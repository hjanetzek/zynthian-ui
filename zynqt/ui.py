"""ZynUI: the Qt UI's counterpart of zynthian_gui, as far as the rest of zynthian sees it.

It is set as zynthian_gui_config.zyngui, owns the state manager and runs the start-up and
shutdown sequences. CUIAs come in through the state manager's cuia_queue (MIDI, keyboard
bindings) and OSC (port 1370, /cuia/<name>); a thread reads the queue and hands each CUIA to the
GUI thread, where it is dispatched to a cuia_<name>() method.
"""

import logging
from queue import Empty
from threading import Thread
from time import monotonic

import pyliblo3 as liblo
from PySide6.QtCore import QObject, QTimer, Property, Signal, Slot
from PySide6.QtGui import QGuiApplication

import zynautoconnect
import zynconf
from zyngine.zynthian_signal_manager import zynsigman
from zyngine.zynthian_state_manager import zynthian_state_manager
from zyngui import zynthian_gui_config

from zynqt.bridge import SignalBridge
from zynqt.chain_edit import ChainEdit
from zynqt.screens.menus import AddChain, MainMenu
from zynqt.screens.chain_screens import Bank, Engine, MidiChannel, Preset
from zynqt.screens.control import ChainControl

# Screens with their own QML (the others are selector screens, zynqt.screens)
QML_SCREENS = ("mixer", "chain_control")


class ZynUI(QObject):
    currentScreenChanged = Signal()
    statusChanged = Signal()
    busyChanged = Signal()
    startedChanged = Signal()
    altModeChanged = Signal()
    infoChanged = Signal()
    confirmChanged = Signal()
    # Navigation for the current screen: "up", "down", "left", "right", "select", "select_bold"
    navigate = Signal(str)
    # Internal: a CUIA from the CUIA thread or OSC, to be run in the GUI thread
    _cuiaRequested = Signal(str, list)
    _startFinished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state_manager = zynthian_state_manager()
        self.chain_manager = self.state_manager.chain_manager
        self.cuia_queue = self.state_manager.cuia_queue
        self.bridge = SignalBridge(self)

        # What the engine side expects of zynthian_gui
        self.screens = {}  # Tk screen objects: none here (used by some controller drivers)
        self.current_screen = "mixer"
        self.screen_history = []
        self.current_processor = None
        self.wsleds = None
        self.alt_mode = False
        self.tts = None

        self.exit_code = 0
        self.exit_flag = False
        self._started = False
        self._busy = False
        self._busy_message = ""
        self._status = {}
        self._cuia_thread = None
        self._osc_server = None

        self.chain_edit = ChainEdit(self.state_manager)
        self.list_screens = {}
        self.chain_control_screen = ChainControl(self, self)
        # Screens with their own QML and Python object (build when shown, hide when left)
        self.qml_screen_objects = {"chain_control": self.chain_control_screen}
        for cls in (MainMenu, AddChain, Engine, MidiChannel, Bank, Preset):
            screen = cls(self, self)
            self.list_screens[screen.name] = screen
        self._info = ""
        self._info_timer = QTimer(self, singleShot=True, interval=2500)
        self._info_timer.timeout.connect(lambda: self._set_info(""))
        self._confirm_text = ""
        self._confirm_action = None

        self._cuiaRequested.connect(self._run_cuia)
        self._startFinished.connect(self._start_finished)
        self._status_timer = QTimer(self, interval=200)
        self._status_timer.timeout.connect(self._poll_status)
        self._status_timer.start()

    # --------------------------------------------------------------------------
    # Start and exit
    # --------------------------------------------------------------------------

    def start(self):
        self._start_osc()
        self._cuia_thread = Thread(target=self._cuia_task, name="cuia", daemon=True)
        self._cuia_thread.start()
        Thread(target=self._start_task, name="start", daemon=True).start()

    def _start_task(self):
        """As zynthian_gui.start_task: last state or default snapshot, else MIDI set-up"""
        sm = self.state_manager
        sm.start_busy("ui startup")
        loaded = False
        try:
            if zynthian_gui_config.restore_last_state:
                loaded = sm.load_last_state_snapshot()
            if not loaded:
                loaded = sm.load_default_snapshot()
            if not loaded:
                sm.init_midi()
                sm.init_midi_services()
            zynautoconnect.request_audio_connect()
            zynautoconnect.request_midi_connect()
        except Exception as e:
            logging.exception(f"start-up failed: {e}")
        finally:
            sm.end_busy("ui startup")
        self._startFinished.emit(bool(loaded))

    @Slot(bool)
    def _start_finished(self, snapshot_loaded):
        self._started = True
        self.startedChanged.emit()
        # As zynthian_gui: without a snapshot, start by adding a chain
        if not snapshot_loaded:
            self.cuia_add_chain()

    def exit(self, code=0):
        """Called from signal handlers and CUIAs: stop in the GUI thread"""
        if self.exit_flag:
            return
        self.exit_code = code
        self.exit_flag = True
        logging.info(f"STOPPING ZYNTHIAN-UI (Qt), exit code {code} ...")
        QTimer.singleShot(0, self._do_exit)

    def _do_exit(self):
        self.bridge.stop()
        if self._osc_server:
            self._osc_server.stop()
            self._osc_server = None
        zynsigman.stop()
        try:
            self.state_manager.stop()
        except Exception as e:
            logging.exception(f"stopping the state manager: {e}")
        self.cuia_queue.put_nowait("__EXIT__")
        if self._cuia_thread:
            self._cuia_thread.join(2)
        QGuiApplication.quit()

    # --------------------------------------------------------------------------
    # Properties for QML
    # --------------------------------------------------------------------------

    @Property(str, notify=currentScreenChanged)
    def currentScreen(self):
        return self.current_screen

    @Property(bool, notify=startedChanged)
    def started(self):
        return self._started

    @Property(bool, notify=busyChanged)
    def busy(self):
        return self._busy

    @Property(str, notify=busyChanged)
    def busyMessage(self):
        return self._busy_message

    @Property("QVariantMap", notify=statusChanged)
    def status(self):
        return self._status

    @Property(bool, notify=altModeChanged)
    def altMode(self):
        return self.alt_mode

    def _poll_status(self):
        sm = self.state_manager
        busy = sm.is_busy()
        message = (sm.get_busy_message() or "") if busy else ""
        if busy != self._busy or message != self._busy_message:
            self._busy = busy
            self._busy_message = message
            self.busyChanged.emit()
        status = {"xrun": bool(sm.status_xrun), "cpuLoad": int(sm.status_cpu_load or 0),
                  "midi": bool(sm.status_midi), "midiRecorder": bool(sm.status_midi_recorder),
                  "audioPlayer": bool(sm.status_audio_player),
                  "overtemp": bool(sm.status_overtemp)}
        if status != self._status:
            self._status = status
            self.statusChanged.emit()

    # --------------------------------------------------------------------------
    # Screens
    # --------------------------------------------------------------------------

    @Property(QObject, notify=currentScreenChanged)
    def currentList(self):
        """The selector screen shown (None for screens with their own QML)"""
        return self.list_screens.get(self.current_screen)

    @Property(QObject, constant=True)
    def chainControl(self):
        return self.chain_control_screen

    @Slot(str)
    def showScreen(self, name):
        self.show_screen(name)

    def _set_current_screen(self, name):
        """Switch to name: hide the old screen object, build the new one"""
        old = self.qml_screen_objects.get(self.current_screen)
        if old and name != self.current_screen:
            old.hide()
        screen = self.list_screens.get(name) or self.qml_screen_objects.get(name)
        if screen:
            screen.build()
        if name != self.current_screen:
            self.current_screen = name
            self.currentScreenChanged.emit()

    def show_screen(self, name, history=True):
        if name not in QML_SCREENS and name not in self.list_screens:
            logging.warning(f"Qt UI has no screen '{name}' (yet)")
            self.show_info(f"'{name}' is not in the Qt UI yet.")
            return
        if history and name != self.current_screen:
            self.screen_history.append(self.current_screen)
            del self.screen_history[:-20]
        self._set_current_screen(name)

    def replace_screen(self, name):
        """Show name instead of the current screen (BACK skips the current one)"""
        self.show_screen(name, history=False)

    def show_screen_reset(self, name):
        self.screen_history = []
        self.show_screen(name, history=False)

    def purge_history(self, name):
        self.screen_history = [n for n in self.screen_history if n != name]

    @Slot()
    def back(self):
        if self._confirm_action:
            self.confirmNo()
            return
        screen = self.list_screens.get(self.current_screen) or self.qml_screen_objects.get(self.current_screen)
        if screen and screen.back():
            return
        if self.screen_history:
            self._set_current_screen(self.screen_history.pop())

    def _navigate(self, what):
        """Arrows and SELECT: the confirm dialog, the selector screen shown, or the QML screen"""
        if self._confirm_action:
            if what == "select":
                self.confirmYes()
            return
        screen = self.list_screens.get(self.current_screen) or self.qml_screen_objects.get(self.current_screen)
        if screen:
            screen.navigate(what)
        else:
            self.navigate.emit(what)

    # Info messages and confirmation

    @Property(str, notify=infoChanged)
    def info(self):
        return self._info

    def _set_info(self, text):
        if text != self._info:
            self._info = text
            self.infoChanged.emit()

    def show_info(self, text, ms=2500):
        self._set_info(text)
        self._info_timer.start(ms)

    @Property(str, notify=confirmChanged)
    def confirmText(self):
        return self._confirm_text

    def confirm(self, text, action):
        self._confirm_text = text
        self._confirm_action = action
        self.confirmChanged.emit()

    @Slot()
    def confirmYes(self):
        action = self._confirm_action
        self.confirmNo()
        if action:
            action()

    @Slot()
    def confirmNo(self):
        self._confirm_text = ""
        self._confirm_action = None
        self.confirmChanged.emit()

    # Chains

    def set_current_processor(self, processor):
        self.current_processor = processor
        if processor and processor.chain:
            processor.chain.set_current_processor(processor)

    def modify_chain(self, status=None):
        """Next stage of adding a chain or processor (zynthian_gui.modify_chain)"""
        if status is not None:
            self.chain_edit.start(status)
        step, result = self.chain_edit.next_step()
        if step in ("engine", "midi_chan"):
            self.show_screen(step)
        elif step == "failed":
            self.show_info(result)
        else:
            chain_id, processor = result
            self.screen_history = []
            self.chain_control(chain_id, processor, force_bank_preset=True)

    def chain_control(self, chain_id=None, processor=None, force_bank_preset=False):
        """Show a chain's processor: bank/preset selection first if it has no preset yet
        (zynthian_gui.chain_control)"""
        cm = self.chain_manager
        if chain_id is None:
            chain_id = cm.active_chain.chain_id
        else:
            cm.set_active_chain_by_id(chain_id)
        chain = cm.get_chain(chain_id)
        if processor is None and chain:
            processor = chain.current_processor
        self.set_current_processor(processor)
        screen = "chain_control"
        if processor and force_bank_preset and not processor.get_preset_name():
            if len(processor.get_bank_list()) > 1:
                screen = "bank"
            else:
                processor.set_bank(0)
                processor.load_preset_list()
                if len(processor.preset_list) > 1:
                    screen = "preset"
        if processor and processor.eng_code == "CL":
            screen = "mixer"   # launcher: not in the Qt UI yet
        self.show_screen(screen)

    def get_current_screen(self):
        return self.current_screen

    def get_alt_mode(self):
        return self.alt_mode

    def get_current_processor(self):
        return self.current_processor

    # --------------------------------------------------------------------------
    # CUIA
    # --------------------------------------------------------------------------

    @Slot(str, list)
    def cuia(self, name, params=None):
        """Run a CUIA from QML (keypad, keys)"""
        self._run_cuia(name, params or [])

    def callable_ui_action(self, cuia, params=None):
        """The name zynthian_gui uses: called by some engine-side code"""
        self._cuiaRequested.emit(str(cuia), list(params or []))

    @Slot(int, bool)
    def pushSwitch(self, i, pressed):
        """A key of the touch keypad (custom switch i), as zynthian_gui_touchkeypad_v5 sends it"""
        self.cuia_queue.put_nowait(f"zynswitch {i + 4},{'P' if pressed else 'R'}")

    def _cuia_task(self):
        """Reads cuia_queue (as zynthian_gui.task_cuia_thread) and hands the CUIAs to the GUI
        thread. Switch events (zynswitch i,P / i,R) are timed here: short, bold or long, long
        also while still held."""
        pressed = {}  # switch index -> press time
        while not self.exit_flag:
            long_ts = monotonic() - zynthian_gui_config.zynswitch_long_seconds
            for i, ts in list(pressed.items()):
                if ts < long_ts:
                    del pressed[i]
                    self._cuiaRequested.emit("_zynswitch", [i, "L"])
            try:
                event = self.cuia_queue.get(True, 0.1)
            except Empty:
                continue
            params = []
            if isinstance(event, str):
                if event == "__EXIT__":
                    break
                parts = event.split(" ", 2)
                cuia = parts[0]
                if len(parts) > 1:
                    params = parts[1].split(",")
            else:
                cuia = event[0]
                if len(event) > 1 and event[1]:
                    params = list(event[1])
            if cuia.lower() == "zynswitch" and len(params) >= 2:
                i, t = int(params[0]), str(params[1]).upper()
                if t == "P":
                    pressed[i] = monotonic()
                    continue
                if t == "R":
                    ts = pressed.pop(i, None)
                    if ts is None:
                        continue  # long press already handled
                    t = self._switch_timing(monotonic() - ts)
                self._cuiaRequested.emit("_zynswitch", [i, t])
                continue
            self._cuiaRequested.emit(str(cuia), params)

    @staticmethod
    def _switch_timing(seconds):
        if seconds > zynthian_gui_config.zynswitch_long_seconds:
            return "L"
        if seconds > zynthian_gui_config.zynswitch_bold_seconds:
            return "B"
        return "S"

    def cuia__zynswitch(self, params):
        """Switch i pressed for t (S/B/L): the standard four switches, else the custom switch
        actions of the wiring configuration (as zynthian_gui.custom_switch_ui_action)"""
        i, t = int(params[0]), params[1]
        if i < 4:
            {0: lambda: self.cuia_menu(), 1: lambda: self.cuia_back(),
             3: lambda: self._navigate("select" if t == "S" else "select_bold")}.get(i, lambda: None)()
            return
        try:
            config = zynthian_gui_config.custom_switch_ui_actions[i - 4]
        except IndexError:
            return
        if not config:
            return
        cuia = None
        if t == "S" and self._is_current_screen_switch(config):
            cuia = config.get("B")
        if not cuia and self.alt_mode:
            cuia = config.get("A" + t)
        if not cuia:
            cuia = config.get(t)
        if cuia:
            parts = cuia.split(" ", 1)
            params = self.state_manager.parse_cuia_params(parts[1]) if len(parts) > 1 else []
            self._run_cuia(parts[0], list(params or []))

    def _is_current_screen_switch(self, config):
        """Short press on the key of the shown screen: its bold action (as zynthian_gui)"""
        short = (config.get("S") or "").lower()
        if not short:
            return False
        return short.endswith(self.current_screen) or (short == "menu" and self.current_screen == "main_menu")

    @Slot(str, list)
    def _run_cuia(self, cuia, params):
        name = cuia.lower()
        func = getattr(self, "cuia_" + name, None)
        if not callable(func):
            logging.info(f"CUIA '{name}' not available in the Qt UI (yet) => {params}")
            return
        try:
            func(params)
        except Exception as e:
            logging.exception(f"CUIA '{name}' failed with {params}: {e}")

    def _start_osc(self):
        try:
            self._osc_server = liblo.ServerThread(zynconf.ServerPort["cuia_osc"], liblo.UDP)
            self._osc_server.add_method(None, None, self._osc_cb)
            self._osc_server.start()
            logging.info(f"ZYNTHIAN-UI (Qt) OSC server on port {self._osc_server.port}")
        except Exception as e:
            logging.error(f"OSC server can't be started: {e}")

    def _osc_cb(self, path, args, types, src):
        """OSC thread: /cuia/<name> args -> cuia_queue, as zynthian_gui.osc_cb_all"""
        parts = path.upper().split("/", 2)
        if len(parts) < 3 or parts[1] != "CUIA":
            logging.debug(f"OSC '{path}' not handled by the Qt UI (yet)")
            return
        if parts[2] != "POWER_SAVE":
            self.state_manager.set_event_flag()
        if self.state_manager.is_busy():
            logging.debug(f"busy, ignoring OSC CUIA {parts[2]}")
            return
        self.cuia_queue.put_nowait((parts[2], args, src))
        zynautoconnect.request_audio_connect()
        zynautoconnect.request_midi_connect()

    # CUIA implementations (the subset the Qt UI has so far)

    def cuia_show_screen(self, params):
        if params:
            self.showScreen(str(params[0]))

    def cuia_screen_mixer(self, params=None):
        self.showScreen("mixer")

    def cuia_main_menu(self, params=None):
        self.showScreen("main_menu")

    def cuia_chain_control(self, params=None):
        self.chain_control()

    def cuia_menu(self, params=None):
        if self.current_screen == "main_menu":
            self.back()
        else:
            self.showScreen("main_menu")

    def cuia_back(self, params=None):
        self.back()

    def cuia_select(self, params=None):
        self._navigate("select")

    def cuia_arrow_up(self, params=None):
        self._navigate("up")

    def cuia_arrow_down(self, params=None):
        self._navigate("down")

    def cuia_arrow_left(self, params=None):
        self._navigate("left")

    def cuia_arrow_right(self, params=None):
        self._navigate("right")

    def cuia_add_chain(self, params=None):
        cm = self.chain_manager
        pos = min(cm.get_active_chain_index() + 1, len(cm.chains) - 1)
        self.list_screens["add_chain"].pos = pos
        self.show_screen("add_chain")

    def cuia_bank_preset(self, params=None):
        if self.current_processor:
            self.show_screen("preset" if self.current_screen == "bank" else "bank")

    def cuia_toggle_alt_mode(self, params=None):
        self.alt_mode = not self.alt_mode
        self.altModeChanged.emit()

    def cuia_exit_ui(self, params=None):
        self.exit(101)

    def cuia_restart_ui(self, params=None):
        self.exit(102)

    def cuia_all_notes_off(self, params=None):
        self.state_manager.all_notes_off()

    def cuia_all_sounds_off(self, params=None):
        self.state_manager.all_sounds_off()
