"""ZynUI: the Qt UI's counterpart of zynthian_gui, as far as the rest of zynthian sees it.

It is set as zynthian_gui_config.zyngui, owns the state manager and runs the start-up and
shutdown sequences. CUIAs come in through the state manager's cuia_queue (MIDI, keyboard
bindings) and OSC (port 1370, /cuia/<name>); a thread reads the queue and hands each CUIA to the
GUI thread, where it is dispatched to a cuia_<name>() method.
"""

import logging
import os
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
from zynqt.models.control_xy import ControlXY
from zynqt.models.launcher import Launcher
from zynqt.screens.pattern_editor import PatternEditor
from zynqt.screens.chain_manager import ChainManager
from zynqt.screens.control import ChainControl
from zynqt.screens.snapshots import Options, Snapshots
from zynqt.screens.chain_options import ChainOptions
from zynqt.screens.routing import AudioIn, AudioOut, MidiDevicesIn, MidiDevicesOut, MidiIn, MidiOut
from zynqt.screens.processor_options import ProcessorOptions
from zynqt.screens.zs3 import ZS3
from zynqt.screens.admin import Admin
from zynqt.screens.midi_recorder import MidiRecorder
from zynqt.screens.midi_chain import KeyRangeProcessor, MidiCC

# Screens with their own QML (the others are selector screens, zynqt.screens); tempo and
# alsa_mixer are chain control showing the state manager's tempo or ALSA mixer processor
QML_SCREENS = ("mixer", "launcher", "pattern_editor", "chain_manager", "chain_control", "tempo", "alsa_mixer", "audio_player",
               "midi_key_range", "control_xy")


class ZynUI(QObject):
    currentScreenChanged = Signal()
    statusChanged = Signal()
    busyChanged = Signal()
    startedChanged = Signal()
    altModeChanged = Signal()
    keypadDockedChanged = Signal()
    infoChanged = Signal()
    confirmChanged = Signal()
    keyboardChanged = Signal()
    movingChainChanged = Signal()
    movingProcessorChanged = Signal()
    mixerSettingsChanged = Signal()
    valueEditorChanged = Signal()
    # SEL pressed while the keyboard is shown: QML answers with keyboardAccept(text)
    keyboardSubmit = Signal()
    # Navigation for the current screen: "up", "down", "left", "right", "select", "select_bold"
    navigate = Signal(str)
    # Internal: a CUIA from the CUIA thread or OSC, to be run in the GUI thread
    _cuiaRequested = Signal(str, list)
    _startFinished = Signal(bool)
    _backgroundDone = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Touch keypad as an overlay brought up from the top edge (default), or docked beside the
        # screens; saved as ZYNTHIAN_QT_KEYPAD ("overlay" / "docked"). Not Tk's ZYNTHIAN_TOUCH_SHOWN:
        # the Tk UI saves that on every exit
        self._keypad_docked = os.environ.get("ZYNTHIAN_QT_KEYPAD", "overlay") == "docked"
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
        self.chain_manager_screen = ChainManager(self, self)
        self.launcher = Launcher(self, self)
        self.pattern_editor = PatternEditor(self, self)
        self.control_xy = ControlXY(self, self)
        # Screens with their own QML and Python object (build when shown, hide when left)
        self.qml_screen_objects = {"launcher": self.launcher,
                                   "pattern_editor": self.pattern_editor,
                                   "chain_manager": self.chain_manager_screen,
                                   "chain_control": self.chain_control_screen,
                                   "tempo": self.chain_control_screen,
                                   "alsa_mixer": self.chain_control_screen,
                                   "audio_player": self.chain_control_screen,
                                   "midi_key_range": self.chain_control_screen,
                                   "control_xy": self.control_xy}
        for cls in (MainMenu, AddChain, Engine, MidiChannel, Bank, Preset, Options, Snapshots,
                    ChainOptions, AudioIn, AudioOut, MidiIn, MidiOut, ProcessorOptions, MidiDevicesIn,
                    MidiDevicesOut, ZS3, Admin, MidiRecorder, MidiCC):
            screen = cls(self, self)
            self.list_screens[screen.name] = screen
        self._info = ""
        self._info_timer = QTimer(self, singleShot=True, interval=2500)
        self._info_timer.timeout.connect(lambda: self._set_info(""))
        self._confirm_text = ""
        self._confirm_action = None
        self._keyboard_title = ""
        self._keyboard_text = ""
        self._keyboard_action = None
        self._value_editor = None   # (title, value, min, max, step, decimals, action)
        self._moving_chain = False
        self._moving_processor = None
        self._backgroundDone.connect(lambda done, result: done(result))

        self._cuiaRequested.connect(self._run_cuia)
        self.bridge.recorderStateChanged.connect(self._recorder_state_changed)
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
        # As the Tk admin's last_state_action, but on every exit (the kiosk session ends with
        # SIGTERM): the next start restores this state
        try:
            if zynthian_gui_config.restore_last_state:
                self.state_manager.save_last_state_snapshot()
            else:
                self.state_manager.delete_last_state_snapshot()
        except Exception as e:
            logging.warning(f"last state: {e}")
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
                  "audioRecorder": bool(sm.audio_recorder.status),
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

    @Property("QVariantList", constant=True)
    def listScreenObjects(self):
        """All selector screens: QML keeps one view per screen, so switching doesn't recreate them"""
        return list(self.list_screens.values())

    @Property(QObject, constant=True)
    def patternEditor(self):
        return self.pattern_editor

    @Property(bool, notify=keypadDockedChanged)
    def keypadDocked(self):
        return self._keypad_docked

    @Slot()
    def toggleKeypadDocked(self):
        self._keypad_docked = not self._keypad_docked
        self.keypadDockedChanged.emit()
        try:
            zynconf.save_config({"ZYNTHIAN_QT_KEYPAD": "docked" if self._keypad_docked else "overlay"})
        except Exception as e:
            logging.warning(f"Can't save the keypad setting: {e}")

    @Property(QObject, constant=True)
    def controlXY(self):
        return self.control_xy

    @Property(QObject, constant=True)
    def launcherModel(self):
        return self.launcher

    @Property(QObject, constant=True)
    def chainManager(self):
        return self.chain_manager_screen

    @Property(QObject, constant=True)
    def chainControl(self):
        return self.chain_control_screen

    @Slot(str)
    def showScreen(self, name):
        self.show_screen(name)

    def _set_current_screen(self, name, params=None):
        """Switch to name: hide the old screen object, build the new one"""
        self.switch_t0 = monotonic()   # for ZYNTHIAN_QT_TIMING (zynthian_qt_main)
        if name != self.current_screen:
            # Move modes belong to the screen they were started in (mixer, chain control, chain
            # manager)
            self.endMoveChain()
            self.endMoveProcessor()
        old = self.qml_screen_objects.get(self.current_screen) or self.list_screens.get(self.current_screen)
        if old and name != self.current_screen and callable(getattr(old, "hide", None)):
            old.hide()
        if name in ("tempo", "alsa_mixer", "audio_player"):
            # As zynthian_gui.show_screen: the control screen with a processor without chain;
            # it becomes the current processor (its bank/preset lists: the player's files)
            proc = {"tempo": self.state_manager.tempo_processor,
                    "alsa_mixer": self.state_manager.alsa_mixer_processor,
                    "audio_player": self.state_manager.audio_player}[name]
            if proc is None:
                self.show_info(f"No {name} processor.")
                return
            if name != "audio_player":
                proc.refresh_controllers(params)
            self.chain_control_screen.special_processor = proc
            self.current_processor = proc
        elif name == "midi_key_range":
            # Note range and transpose of the active chain, as controllers
            chain = self.chain_manager.get_active_chain()
            if chain is None or chain.zmop_index is None or chain.zmop_index < 0:
                self.show_info("This chain has no MIDI.")
                return
            self.chain_control_screen.special_processor = KeyRangeProcessor(chain)
        elif name == "chain_control":
            self.chain_control_screen.special_processor = None
        elif name == "control_xy" and not self.control_xy.available():
            self.show_info("Choose the X and Y axis controllers first (long press on a controller).")
            return
        screen = self.list_screens.get(name) or self.qml_screen_objects.get(name)
        if screen:
            screen.build()
        self.switch_build_ms = 1000 * (monotonic() - self.switch_t0)
        if name != self.current_screen:
            self.current_screen = name
            self.currentScreenChanged.emit()

    def show_screen(self, name, history=True, params=None):
        if name not in QML_SCREENS and name not in self.list_screens:
            logging.warning(f"Qt UI has no screen '{name}' (yet)")
            self.show_info(f"'{name}' is not in the Qt UI yet.")
            return
        if history and name != self.current_screen:
            self.screen_history.append(self.current_screen)
            del self.screen_history[:-20]
        self._set_current_screen(name, params)

    def replace_screen(self, name):
        """Show name instead of the current screen (BACK skips the current one)"""
        self.show_screen(name, history=False)

    def show_screen_reset(self, name):
        self.screen_history = []
        self.show_screen(name, history=False)

    def purge_history(self, name):
        self.screen_history = [n for n in self.screen_history if n != name]

    # Moving the active chain in the mixer (zynthian_gui_chain_manager's move mode)

    # Mixer layout settings (admin)

    @Property(int, notify=mixerSettingsChanged)
    def visibleChains(self):
        return zynthian_gui_config.visible_mixer_strips

    def mixer_settings_changed(self):
        """Visible chains or the toggle control changed: the mixer models reload too"""
        self.mixerSettingsChanged.emit()

    @Property(bool, notify=movingChainChanged)
    def movingChain(self):
        return self._moving_chain

    def start_move_chain(self, stay=False):
        """Move the active chain: in the mixer, or in the screen shown (stay: chain manager)"""
        if not stay:
            self.show_screen("mixer")
        self._moving_chain = True
        self.movingChainChanged.emit()

    @Slot(int)
    def moveChain(self, step):
        if self._moving_chain and self.chain_manager.nudge_chain(step) is None:
            self.show_info("This chain can't be moved.")

    @Slot()
    def endMoveChain(self):
        if self._moving_chain:
            self._moving_chain = False
            self.movingChainChanged.emit()

    # Moving a processor within its chain (zynthian_gui_chain_manager's processor move mode)

    @Property(bool, notify=movingProcessorChanged)
    def movingProcessor(self):
        return self._moving_processor is not None

    def start_move_processor(self, processor, stay=False):
        """Move processor: in chain control, or in the screen shown (stay: chain manager)"""
        if not stay:
            self.chain_control(processor.chain.chain_id, processor)
        self._moving_processor = processor
        self.movingProcessorChanged.emit()

    @Slot(str)
    def moveProcessor(self, direction):
        from zyngine.zynthian_chain_manager import NUDGE_UP, NUDGE_DOWN, NUDGE_LEFT, NUDGE_RIGHT
        p = self._moving_processor
        if p is None or p.chain is None:
            return
        d = {"up": NUDGE_UP, "down": NUDGE_DOWN, "left": NUDGE_LEFT, "right": NUDGE_RIGHT}[direction]
        if self.chain_manager.nudge_processor(p.chain.chain_id, p, d):
            if self.current_screen == "chain_manager":
                self.chain_manager_screen.moved()
            else:
                self.chain_control_screen.build()
        else:
            self.show_info("Can't move it further.")

    @Slot()
    def endMoveProcessor(self):
        if self._moving_processor is not None:
            self._moving_processor = None
            self.movingProcessorChanged.emit()

    @Slot()
    def back(self):
        if self._moving_processor is not None:
            self.endMoveProcessor()
            return
        if self._moving_chain:
            self.endMoveChain()
            return
        if self._value_editor:
            self.valueEditorCancel()
            return
        if self._keyboard_action:
            self.keyboardCancel()
            return
        if self._confirm_action:
            self.confirmNo()
            return
        screen = self.list_screens.get(self.current_screen) or self.qml_screen_objects.get(self.current_screen)
        if screen and screen.back():
            return
        if self.screen_history:
            self._set_current_screen(self.screen_history.pop())

    def _navigate(self, what):
        """Arrows and SELECT: the keyboard, the confirm dialog, the selector screen shown, or the
        QML screen"""
        if self._moving_processor is not None:
            if what in ("up", "down", "left", "right"):
                self.moveProcessor(what)
            elif what in ("select", "select_bold"):
                self.endMoveProcessor()
            return
        if self._moving_chain:
            if what in ("left", "up"):
                self.moveChain(-1)
            elif what in ("right", "down"):
                self.moveChain(1)
            elif what in ("select", "select_bold"):
                self.endMoveChain()
            return
        if self._value_editor:
            if what in ("up", "right"):
                self.valueEditorStep(1)
            elif what in ("down", "left"):
                self.valueEditorStep(-1)
            elif what == "select":
                self.valueEditorAccept()
            return
        if self._keyboard_action:
            if what == "select":
                self.keyboardSubmit.emit()
            return
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

    def show_options(self, title, options, selected=0):
        """options: list of (label, action, info, icon); selected: the entry selected first"""
        self.list_screens["option"].config(title, options, selected)
        self.show_screen("option")

    # On-screen keyboard (zynthian_gui_keyboard)

    @Property(bool, notify=keyboardChanged)
    def keyboardShown(self):
        return self._keyboard_action is not None

    @Property(str, notify=keyboardChanged)
    def keyboardTitle(self):
        return self._keyboard_title

    @Property(str, notify=keyboardChanged)
    def keyboardText(self):
        return self._keyboard_text

    def show_keyboard(self, action, text="", title=""):
        """Ask for a text; action(text) runs when it is accepted"""
        self._keyboard_title = title
        self._keyboard_text = text
        self._keyboard_action = action
        self.keyboardChanged.emit()

    @Slot(str)
    def keyboardAccept(self, text):
        action = self._keyboard_action
        self.keyboardCancel()
        if action:
            action(text.strip())

    @Slot()
    def keyboardCancel(self):
        self._keyboard_action = None
        self.keyboardChanged.emit()

    # Value editor (Tk's param editor, for numeric values): action(value) when accepted

    def edit_value(self, title, value, vmin, vmax, action, step=1, decimals=0):
        self._value_editor = [title, value, vmin, vmax, step, decimals, action]
        self.valueEditorChanged.emit()

    @Property(bool, notify=valueEditorChanged)
    def valueEditorShown(self):
        return self._value_editor is not None

    @Property(str, notify=valueEditorChanged)
    def valueEditorTitle(self):
        return self._value_editor[0] if self._value_editor else ""

    @Property(str, notify=valueEditorChanged)
    def valueEditorText(self):
        if not self._value_editor:
            return ""
        value, decimals = self._value_editor[1], self._value_editor[5]
        return f"{value:.{decimals}f}"

    @Slot(int)
    def valueEditorStep(self, steps):
        ed = self._value_editor
        if ed:
            ed[1] = round(max(ed[2], min(ed[3], ed[1] + steps * ed[4])), ed[5] if ed[5] else None)
            if not ed[5]:
                ed[1] = int(ed[1])
            self.valueEditorChanged.emit()

    @Slot()
    def valueEditorAccept(self):
        ed = self._value_editor
        self.valueEditorCancel()
        if ed:
            ed[6](ed[1])

    @Slot()
    def valueEditorCancel(self):
        self._value_editor = None
        self.valueEditorChanged.emit()

    # Background work (loading and saving snapshots): keeps the GUI thread drawing the busy
    # overlay; done(result) runs in the GUI thread

    def run_background(self, task, done=None):
        def run():
            result = None
            try:
                result = task()
            except Exception as e:
                logging.exception(f"background task failed: {e}")
            if done:
                self._backgroundDone.emit(done, result)
        Thread(target=run, name="ui task", daemon=True).start()

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
        if step == "midi_chan":
            self.list_screens["midi_chan"].mode = "ADD"
            self.show_screen(step)
        elif step == "engine":
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
            screen = "launcher"
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
        # As zynthian_gui.callable_ui_action: the current screen first (transport keys in the
        # pattern editor, MIDI recorder, audio file widgets, ...); it returns True if it handled it
        screen = self.list_screens.get(self.current_screen) or self.qml_screen_objects.get(self.current_screen)
        screen_func = getattr(screen, "cuia_" + name, None) if screen is not None else None
        if callable(screen_func):
            try:
                if screen_func(params):
                    return
            except Exception as e:
                logging.exception(f"CUIA '{name}' of screen {self.current_screen} failed with {params}: {e}")
                return
        func = getattr(self, "cuia_" + name, None)
        if not callable(func):
            logging.info(f"CUIA '{name}' not available in the Qt UI (yet) => {params}")
            # Keys mapped to it should visibly do something
            self.show_info(f"{name.upper()}: not in the Qt UI yet.")
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

    def cuia_screen_admin(self, params=None):
        self.show_screen("admin")

    def cuia_screen_zs3(self, params=None):
        # As zynthian_gui: program changes save ZS3s while the screen is shown
        self.show_screen("zs3")
        self.list_screens["zs3"].enable_midi_learn()

    def cuia_zs3_save(self, params=None):
        if params:
            if isinstance(params[0], int):
                self.state_manager.save_zs3_by_index(params[0])
            else:
                self.state_manager.save_zs3(params[0])

    # MIDI learn (zynthian_gui's MIDI learn CUIAs): the chain control screen (and the screens
    # it shows: ALSA mixer, note range) learns controllers / notes, the ZS3 screen program changes

    def _learn_screen(self):
        if self.current_screen in ("chain_control", "alsa_mixer", "midi_key_range", "tempo", "audio_player"):
            return self.chain_control_screen
        if self.current_screen == "zs3":
            return self.list_screens["zs3"]
        return None

    def cuia_toggle_midi_learn(self, params=None):
        screen = self._learn_screen()
        if screen is not None:
            screen.toggle_midi_learn()
        elif self.state_manager.midi_learn_state:
            self.state_manager.set_midi_learn(False)
        else:
            self.state_manager.set_midi_learn(True)

    def cuia_enable_midi_learn(self, params=None):
        screen = self._learn_screen()
        if screen is self.chain_control_screen:
            if not (screen.midi_learning or screen.note_learn):
                screen.toggle_midi_learn()
        elif screen is not None:
            screen.enable_midi_learn()
        else:
            self.state_manager.set_midi_learn(True)

    def cuia_disable_midi_learn(self, params=None):
        screen = self._learn_screen()
        if screen is self.chain_control_screen:
            screen.exit_midi_learn()
        elif screen is not None:
            screen.disable_midi_learn()
        self.state_manager.set_midi_learn(False)

    def cuia_midi_learn_control(self, params=None):
        if self._learn_screen() is self.chain_control_screen and params:
            self.chain_control_screen.midi_learn(int(params[0]))

    def cuia_midi_learn_control_options(self, params=None):
        if self._learn_screen() is self.chain_control_screen and params:
            self.chain_control_screen.controllers[int(params[0])].options()

    def cuia_midi_unlearn_control(self, params=None):
        cc = self.chain_control_screen
        if self._learn_screen() is not cc:
            return
        zctrl = cc.controllers[int(params[0])].zctrl if params else self.state_manager.get_midi_learn_zctrl()
        if zctrl is not None:
            cc.exit_midi_learn()
            self.chain_manager.clean_midi_learn(zctrl)
            cc.refresh_bindings()

    def cuia_action_midi_unlearn(self, params=None):
        if self._learn_screen() is self.chain_control_screen:
            self.chain_control_screen.midi_unlearn_action()

    def cuia_midi_unlearn_mixer(self, params=None):
        for chain in self.chain_manager.chains.values():
            if chain.zynmixer_proc:
                self.chain_manager.clean_midi_learn(chain.zynmixer_proc)

    def cuia_midi_unlearn_node(self, params=None):
        """params: processor id, controller symbol (zynthian_gui passes both as one list, which
        remove_midi_learn(proc, symbol) doesn't take)"""
        if params and len(params) > 1:
            proc = self.chain_manager.processors.get(int(params[0]))
            if proc is not None:
                self.chain_manager.remove_midi_learn(proc, str(params[1]))

    def cuia_midi_unlearn_chain(self, params=None):
        self.chain_manager.clean_midi_learn(params[0] if params else self.chain_manager.active_chain.chain_id)

    def cuia_enable_midi_learn_pc(self, params=None):
        self.state_manager.enable_learn_pc(params[0] if params else "")

    def cuia_disable_midi_learn_pc(self, params=None):
        self.state_manager.disable_learn_pc()

    def cuia_disable_midi_learn_cc(self, params=None):
        self.state_manager.disable_learn_cc()

    def cuia_z2_zynpot_touch(self, params=None):
        if self._learn_screen() is self.chain_control_screen and params:
            self.chain_control_screen.controllers[int(params[0])].touched()

    def cuia_zs3_load(self, params=None):
        if params:
            if isinstance(params[0], int):
                self.state_manager.load_zs3_by_index(params[0])
            else:
                self.state_manager.load_zs3(params[0])

    def cuia_screen_snapshot(self, params=None):
        self.show_screen("snapshot")

    # Tempo, as zynthian_gui

    def cuia_tempo(self, params=None):
        self.state_manager.zynseq.tap_tempo()
        if self.current_screen != "tempo":
            self.show_screen("tempo")

    def cuia_tap_tempo(self, params=None):
        self.state_manager.zynseq.tap_tempo()

    def cuia_set_tempo(self, params=None):
        if params:
            self.state_manager.zynseq.set_tempo(params[0])

    def cuia_tempo_up(self, params=None):
        zs = self.state_manager.zynseq
        zs.set_tempo(zs.get_tempo() + (params[0] if params else 1))

    def cuia_tempo_down(self, params=None):
        zs = self.state_manager.zynseq
        zs.set_tempo(zs.get_tempo() - (params[0] if params else 1))

    def cuia_screen_audio_player(self, params=None):
        self.show_screen("audio_player")

    cuia_audio_file_list = cuia_screen_audio_player

    def cuia_screen_midi_recorder(self, params=None):
        self.show_screen("midi_recorder")

    def cuia_screen_alsa_mixer(self, params=None):
        self.show_screen("alsa_mixer", params=params)

    def cuia_screen_audio_mixer(self, params=None):
        self.show_screen_reset("mixer")

    def cuia_screen_mixer(self, params=None):
        self.showScreen("mixer")

    def cuia_screen_launcher(self, params=None):
        """PAD: the launcher; in the launcher, edit the selected pad (zynthian_gui)"""
        if self.current_screen == "launcher":
            self.launcher.edit_pad()
        else:
            self.show_screen_reset("launcher")

    def cuia_screen_zynpad(self, params=None):
        self.showScreen("launcher")

    def cuia_screen_pattern_editor(self, params=None):
        """The selected pad's pattern; outside the launcher the active chain's, or the first MIDI
        chain's (zynthian_gui.cuia_screen_pattern_editor)"""
        if self.current_screen == "launcher":
            self.launcher.edit_pad()
            return
        cm = self.chain_manager
        chain = cm.get_active_chain()
        if chain is None or chain.midi_chan is None or chain.midi_chan > 15:
            for chain_id in cm.get_chain_ids_filtered(["synth", "midi"]):
                midi_chan = cm.chains[chain_id].midi_chan
                if midi_chan is not None and midi_chan <= 15:
                    cm.set_active_chain_by_id(chain_id)
                    chain = cm.chains[chain_id]
                    break
            else:
                self.show_info("No MIDI chain for the pattern editor.")
                return
        self.show_screen("pattern_editor")

    def cuia_screen_chain_manager(self, params=None):
        self.showScreen("chain_manager")

    def cuia_main_menu(self, params=None):
        self.showScreen("main_menu")

    def _chain_id_param(self, params):
        """Chain from a CUIA parameter: its position (1-based, 0 the main chain), as zynthian_gui;
        None without a parameter"""
        try:
            index = int(params[0])
            return 0 if index == 0 else self.chain_manager.get_chain_id_by_index(index - 1)
        except (TypeError, ValueError, IndexError):
            return None

    def cuia_chain_control(self, params=None):
        self.chain_control(self._chain_id_param(params))

    cuia_screen_control = cuia_chain_control

    def cuia_menu(self, params=None):
        """The current screen's own menu if it has one (pattern editor), else the main menu"""
        screen = self.qml_screen_objects.get(self.current_screen)
        show_menu = getattr(screen, "show_menu", None)
        if callable(show_menu):
            show_menu()
        elif self.current_screen == "main_menu":
            self.back()
        else:
            self.showScreen("main_menu")

    def cuia_back(self, params=None):
        self.back()

    def cuia_select(self, params=None):
        """Select entry params[0] of the shown list (as zynthian_gui: an index, no action)"""
        screen = self.list_screens.get(self.current_screen)
        if screen and params:
            try:
                screen.setIndex(int(params[0]))
            except (TypeError, ValueError):
                pass

    def cuia_select_action(self, params=None):
        """The SEL key: params[0] "S" (short, default) or "B" (bold)"""
        t = str(params[0]).upper() if params else "S"
        self._navigate("select_bold" if t in ("B", "L") else "select")

    def cuia_bold_select_action(self, params=None):
        self._navigate("select_bold")

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

    @Slot(int)
    def openChain(self, chain_id):
        """Mixer strip tapped: the chain's controllers"""
        self.chain_control(chain_id)

    @Slot(int)
    def openChainOptions(self, chain_id):
        if chain_id >= 0:
            self.chain_manager.set_active_chain_by_id(chain_id)
        self.show_screen("chain_options")

    def set_midi_channel(self):
        """Change the active chain's MIDI channel"""
        self.list_screens["midi_chan"].mode = "SET"
        self.show_screen("midi_chan")

    @Slot(str)
    def openChainScreen(self, name):
        """Chain control's sidebar: chain_options, midi_in, midi_out, audio_out"""
        self.show_screen(name)

    def cuia_chain_options(self, params=None):
        chain_id = self._chain_id_param(params)
        if chain_id is not None:
            self.chain_manager.set_active_chain_by_id(chain_id)
        self.show_screen("chain_options")

    def cuia_bank_preset(self, params=None):
        if self.current_processor:
            self.show_screen("preset" if self.current_screen == "bank" else "bank")

    def _recorder_state_changed(self):
        if self.current_screen in ("main_menu", "midi_recorder"):
            self.list_screens[self.current_screen].fill()

    # Transport and recorders, as zynthian_gui (ALT: MIDI instead of audio)

    def cuia_start_audio_record(self, params=None):
        self.state_manager.audio_recorder.start_recording()

    def cuia_stop_audio_record(self, params=None):
        self.state_manager.audio_recorder.stop_recording()

    def cuia_toggle_audio_record(self, params=None):
        self.state_manager.audio_recorder.toggle_recording()

    def cuia_start_audio_play(self, params=None):
        self.state_manager.start_audio_player()

    def cuia_stop_audio_play(self, params=None):
        self.state_manager.stop_audio_player(reset_pos=True)

    def cuia_toggle_audio_play(self, params=None):
        self.state_manager.toggle_audio_player()

    def cuia_start_midi_record(self, params=None):
        self.state_manager.start_midi_record()

    def cuia_stop_midi_record(self, params=None):
        self.state_manager.stop_midi_record()

    def cuia_toggle_midi_record(self, params=None):
        self.state_manager.toggle_midi_record()

    def cuia_start_midi_play(self, params=None):
        self.state_manager.start_midi_playback()

    def cuia_stop_midi_play(self, params=None):
        self.state_manager.stop_midi_playback()

    def cuia_toggle_midi_play(self, params=None):
        self.state_manager.toggle_midi_playback()

    def cuia_toggle_record(self, params=None):
        if self.alt_mode:
            self.cuia_toggle_midi_record()
        else:
            self.cuia_toggle_audio_record()

    def cuia_stop(self, params=None):
        if self.alt_mode:
            self.cuia_stop_midi_play()
        else:
            self.cuia_stop_audio_play()

    def cuia_toggle_play(self, params=None):
        if self.alt_mode:
            self.cuia_toggle_midi_play()
        else:
            self.cuia_toggle_audio_play()

    def cuia_nop(self, params=None):
        pass

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
