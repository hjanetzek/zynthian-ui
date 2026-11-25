"""ZynUI: the Qt UI's counterpart of zynthian_gui, as far as the rest of zynthian sees it.

It is set as zynthian_gui_config.zyngui, owns the state manager and runs the start-up and
shutdown sequences. CUIAs come in through the state manager's cuia_queue (MIDI, keyboard
bindings) and OSC (port 1370, /cuia/<name>); a thread reads the queue and hands each CUIA to the
GUI thread, where it is dispatched to a cuia_<name>() method. The websocket API (port 8370:
CUIAs, keys, MIDI in; LED, screen, DPM and chain feedback out) is upstream's, shared with the Tk
UI (zyngui.zynthian_websocket); zynqt.ws_state reports the Qt screens as Tk's.
"""

import functools
import logging
import os
from queue import Empty
from threading import Thread
from time import monotonic, sleep

import pyliblo3 as liblo
from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Property, Signal, Slot
from PySide6.QtGui import QCursor, QGuiApplication, QWindow

import zynautoconnect
from zyncoder.zyncore import lib_zyncore
import zynconf
from zyngine import zynthian_lv2
from zyngine.zynthian_signal_manager import zynsigman
from zyngine.zynthian_state_manager import zynthian_state_manager
from zyngui import zynthian_gui_config, zynthian_admin_settings, zynthian_help, zynthian_power_control, zynthian_wiring
from zyngui.zynthian_websocket import zynthian_websocket_feedback

from zynqt.bridge import SignalBridge
from zynqt.gui_thread import GuiCaller, gui_thread
from zynqt.screen_names import qt_name, tk_name
from zynqt.tk_screens import TkScreens
from zynqt.power import battery_status
from zynqt.keyboard import load_bindings
from zynqt.chain_edit import ChainEdit
from zynqt.screens.menus import AddChain, MainMenu
from zynqt.screens.chain_screens import Bank, Engine, MidiChannel, Preset, has_bank_dirs
from zynqt.models.control_xy import ControlXY
from zynqt.models.launcher import Launcher
from zynqt.keypad_leds import KeypadLeds
from zynqt.hw_input import HwInput, list_step
from zynqt.screens.pattern_editor import PatternEditor
from zynqt.screens.chain_manager import ChainManager
from zynqt.screens.control import ChainControl
from zynqt.screens.snapshots import Options, Snapshots
from zynqt.screens.file_selector import FileSelector
from zynqt.screens.chain_options import ChainOptions
from zynqt.screens.routing import AudioIn, AudioOut, MidiDevicesIn, MidiDevicesOut, MidiIn, MidiOut
from zynqt.screens.processor_options import ProcessorOptions
from zynqt.screens.zs3 import ZS3
from zynqt.screens.admin import Admin
from zynqt.screens.controller_settings import ControllerSettings
from zynqt.screens.midi_recorder import MidiRecorder
from zynqt.screens.midi_chain import KeyRangeProcessor, MidiCC
from zynqt.screens.mixer_nav import MixerNav
from zynqt.ws_state import ScreenStateWatch, current_state
from zynqt.ws_keys import WebsocketKeys

# Screens with their own QML (the others are selector screens, zynqt.screens); tempo and
# alsa_mixer are chain control showing the state manager's tempo or ALSA mixer processor
QML_SCREENS = ("mixer", "launcher", "pattern_editor", "chain_manager", "chain_control", "tempo", "alsa_mixer", "audio_player",
               "midi_key_range", "control_xy")

# Screens which are never in the history: the options list is a modal list over the screen which
# opened it. A screen shown from it (MENU on the pattern editor's options: the main menu) returns
# to that screen; kept in the history, the next options list (any screen's) would end the history
# at the old entry and return there (Admin > Controller Settings after the pattern editor's menu:
# a setting chosen led back to the pattern editor)
NO_HISTORY_SCREENS = ("option",)


def _int(value):
    """An int from a number or a string ("1", "1.0": CUIA strings, untyped OSC); ValueError,
    TypeError or OverflowError ("inf") if it isn't one"""
    return int(float(value))


def zynpot_params(params, log=True):
    """ZYNPOT's encoder and delta as ints (zynthian_gui.cuia_zynpot), from numbers or strings
    (CUIA strings, OSC: "1" or "1.0"), or None (logged) if they are missing or not numbers"""
    try:
        return _int(params[0]), _int(params[1])
    except (TypeError, ValueError, OverflowError, IndexError, KeyError):
        if log:
            logging.error(f"ZYNPOT requires 2 parameters: index, delta, not {params}")
        return None


def zynswitch_params(params, log=True):
    """ZYNSWITCH's switch, action (P, R, S, B, L, ...: upper case) and, for R, the press duration
    in µs (the kit's switches; None: timed here), from numbers or strings as zynpot_params; None
    (logged) if they are missing or not numbers"""
    try:
        i, t = _int(params[0]), str(params[1]).upper()
        dtus = _int(params[2]) if t == "R" and len(params) > 2 else None
    except (TypeError, ValueError, OverflowError, IndexError, KeyError):
        if log:
            logging.error(f"ZYNSWITCH requires 2 parameters: index, action[, µs], not {params}")
        return None
    return i, t, dtus


def cuia_event(event):
    """A cuia_queue entry as (name, params list): a CUIA string ("NAME p1,p2"), or a tuple / list
    (name, params[, source]) from OSC, the websocket, drivers (params a list, a tuple or one
    value); None (logged) for anything else"""
    try:
        if isinstance(event, str):
            parts = event.split(" ", 2)
            return parts[0], parts[1].split(",") if len(parts) > 1 else []
        cuia = event[0]
        params = event[1] if len(event) > 1 else None
    except (TypeError, IndexError, KeyError):
        cuia = None
    if not isinstance(cuia, str) or not cuia:
        logging.error(f"bad CUIA event {event!r}")
        return None
    if params is None or params == "":
        return cuia, []
    if isinstance(params, (list, tuple)):
        return cuia, list(params)
    return cuia, [params]


def ws_cuia_args_ok(cuia, args):
    """ZYNPOT index,delta[,P|R] and ZYNSWITCH index,action[,µs]: what _cuia_task accepts
    (zynpot_params, zynswitch_params)"""
    name = str(cuia).lower()
    if name == "zynpot":
        return zynpot_params(args, log=False) is not None
    if name == "zynswitch":
        return zynswitch_params(args, log=False) is not None
    return True


class ZynUI(QObject, zynthian_websocket_feedback):
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
    helpChanged = Signal()
    topBarChanged = Signal()
    # Help view: scroll by n steps (arrows, encoder)
    helpScroll = Signal(int)
    # SEL pressed while the keyboard is shown: QML answers with keyboardAccept(text)
    keyboardSubmit = Signal()
    # Navigation for the current screen: "up", "down", "left", "right", "select", "select_bold"
    navigate = Signal(str)
    # Internal: a CUIA from the CUIA thread or OSC, to be run in the GUI thread
    _cuiaRequested = Signal(str, list)
    _startFinished = Signal(bool)
    # Internal: the kit's encoders were turned (HwInput's thread), take the deltas in the GUI thread
    _zynpotPending = Signal()
    _backgroundDone = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Calls from other threads (engines, MIDI, OSC, drivers) go to the GUI thread (@gui_thread)
        self._gui = GuiCaller(self)
        # Touch keypad docked beside the screens, or not shown (default); saved as ZYNTHIAN_QT_KEYPAD
        # ("docked" / "off"; any other value, e.g. the former "overlay", is off). Not Tk's
        # ZYNTHIAN_TOUCH_SHOWN: the Tk UI saves that on every exit
        self._keypad_docked = os.environ.get("ZYNTHIAN_QT_KEYPAD", "off").strip() == "docked"
        self.state_manager = zynthian_state_manager()
        self.chain_manager = self.state_manager.chain_manager
        self.cuia_queue = self.state_manager.cuia_queue
        self.bridge = SignalBridge(self)

        # What the engine side expects of zynthian_gui
        self.current_screen = "mixer"
        # The root screen shown last (Tk's "root": the mixer in its mode)
        self._last_root = "mixer"
        # The screen announced with SS_GUI_SHOW_SCREEN (its Tk name)
        self._sent_screen = None
        self.screen_history = []
        self.current_processor = None
        self.wsleds = None
        self.alt_mode = False
        self.tts = None

        self.exit_code = 0
        self.exit_flag = False
        self._shut_down = False
        self._started = False
        self._busy = False
        self._busy_message = ""
        self._busy_progress = None
        self._busy_details = ""
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
        # Stand-ins for the Tk screen objects some controller drivers use (zynqt.tk_screens)
        self.screens = TkScreens(self)
        # Screens with their own QML and Python object (build when shown, hide when left)
        self.qml_screen_objects = {"mixer": MixerNav(self),
                                   "launcher": self.launcher,
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
                    MidiDevicesOut, ZS3, Admin, MidiRecorder, MidiCC, FileSelector, ControllerSettings):
            screen = cls(self, self)
            self.list_screens[screen.name] = screen
        self._info = ""
        self._info_timer = QTimer(self, singleShot=True, interval=2500)
        self._info_timer.timeout.connect(lambda: self._set_info(""))
        self._confirm_text = ""
        self._confirm_action = None
        # The QML side (zynthian_qt_main.QmlFrontend) and its theme, set when it loads
        self.frontend = None
        self.theme_name = None
        self._keyboard_title = ""
        self._keyboard_text = ""
        self._keyboard_action = None
        self._value_editor = None   # (title, value, min, max, step, decimals, action)
        self._help_html = ""
        self._topbar_shown = True
        self._cursor_hidden = False
        self._help_path = ""        # the page shown ("" for the index)
        self._moving_chain = False
        self._moving_processor = None
        self._backgroundDone.connect(lambda done, result: done(result))

        self._cuiaRequested.connect(self._run_cuia)
        self.bridge.recorderStateChanged.connect(self._recorder_state_changed)
        # SS_GUI_SHOW_MESSAGE (drivers, engines): Tk shows it in the screen's title
        self.bridge.showMessage.connect(self.show_info)
        # SS_GUI_SHOW_FILE_SELECTOR (path controllers) and SS_GUI_CONTROL_MODE (SooperLooper)
        self.bridge.showFileSelector.connect(lambda kwargs: self.show_file_selector(**kwargs))
        self.bridge.controlMode.connect(self._control_mode)
        self._startFinished.connect(self._start_finished)
        # The touch keypad's LEDs (zynthian_wsleds_v5)
        self.keypad_leds = KeypadLeds(self, self)
        self._status_timer = QTimer(self, interval=200)
        self._status_timer.timeout.connect(self._poll_status)
        self._status_timer.start()
        # The kit's encoders and switches (docs/qt-hardware-input.md): only with a kit's zyncore
        # build, off with the generic one (DUMMIES: Duet, desktops)
        self.zynpot_pr_state = [0] * max(zynthian_gui_config.num_zynpots, 0)
        # No long press while held (zynthian_gui.zynswitch_disable_autolong: the Organelle's AUX)
        self.zynswitch_autolong_disabled = False
        self._zynpot_steps = {}   # encoder -> the behaviour set in zyncore
        self.hw_input = HwInput(lib_zyncore, zynthian_gui_config.last_zynswitch_index,
                                zynthian_gui_config.num_zynpots, self.cuia_queue.put_nowait,
                                self._has_switch_ui_action, self._zynpotPending.emit,
                                self.state_manager.set_event_flag)
        self._zynpotPending.connect(self._take_zynpots)
        # The websocket API (zyngui.zynthian_websocket): started with start()
        self.websocket_setup()
        self._ws_watch = ScreenStateWatch(self, self.cb_screen_state_full)
        self._ws_keys = WebsocketKeys(self)

    # --------------------------------------------------------------------------
    # Start and exit
    # --------------------------------------------------------------------------

    def start(self):
        self._start_osc()
        self.websocket_init()
        self._cuia_thread = Thread(target=self._cuia_task, name="cuia", daemon=True)
        self._cuia_thread.start()
        if self.hw_input.enabled:
            self.hw_input.start()
        else:
            logging.info("Hardware input: off (no switches or encoders in this zyncore build)")
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
        # The LV2 data (lilv world), unless the snapshot's plugins loaded it already: in the
        # background once zynthian is idle (a snapshot load builds it itself), so the first
        # plugin added doesn't wait for it (zynthian_lv2.get_world)
        zynthian_lv2.preload_world(busy=lambda: bool(sm.busy))
        self._startFinished.emit(bool(loaded))

    @Slot(bool)
    def _start_finished(self, snapshot_loaded):
        self._started = True
        self.startedChanged.emit()
        # The start screen, for the drivers (Tk announces its first screen too)
        self.notify_screen()
        # As zynthian_gui (create_screens, cb_set_active_chain): the custom switches' MIDI events,
        # Zynaptik and Zyntof, for the active chain's channel. Kit builds only: the generic
        # zyncore has no setup_zynswitch_midi
        if self.hw_input.enabled:
            self._wiring_midi_setup()
            self.bridge.activeChainChanged.connect(self._wiring_midi_setup)
        # As zynthian_gui: without a snapshot, start by adding a chain
        if not snapshot_loaded:
            self.cuia_add_chain()

    @gui_thread
    def exit(self, code=0):
        """Called from signal handlers and CUIAs: stop in the GUI thread"""
        if self.exit_flag:
            return
        self.exit_code = code
        self.exit_flag = True
        logging.info(f"STOPPING ZYNTHIAN-UI (Qt), exit code {code} ...")
        QTimer.singleShot(0, self._do_exit)

    @gui_thread
    def switch_theme(self, name, done=None):
        """Show the UI in theme name ("" / None: the default), then call done(), without
        restarting zynthian: the
        QML engine is replaced (QmlFrontend.switch_theme), after the current event (a QML handler
        may have called this). Under qmlpreview (hot reload) the UI restarts instead: the preview
        service is attached to the first engine."""
        if self.frontend is None or os.environ.get("ZYNTHIAN_QT_EXIT_FILE"):
            self.exit(102)
            return
        QTimer.singleShot(0, lambda: self.frontend.switch_theme(name, done))

    def _do_exit(self):
        self.shutdown(save_state=True)
        QGuiApplication.quit()

    def shutdown(self, save_state=True):
        """Stop the backend: hardware input, OSC, the state manager (its engines and JACK
        clients). From _do_exit, and from zynthian_qt_main.py when the UI fails (save_state
        False: the state may be the cause). Only once."""
        if self._shut_down:
            return
        self._shut_down = True
        self.exit_flag = True
        # First: no zyncore callbacks into Python while shutting down
        self.hw_input.stop()
        # As the Tk admin's last_state_action, but on every exit (the kiosk session ends with
        # SIGTERM): the next start restores this state
        if save_state:
            try:
                zynthian_admin_settings.last_state_action(self.state_manager)
            except Exception as e:
                logging.warning(f"last state: {e}")
        self.bridge.stop()
        if self._osc_server:
            self._osc_server.stop()
            self._osc_server = None
        self.websocket_stop()
        zynsigman.stop()
        try:
            self.state_manager.stop()
        except Exception as e:
            logging.exception(f"stopping the state manager: {e}")
        self.cuia_queue.put_nowait("__EXIT__")
        if self._cuia_thread:
            self._cuia_thread.join(2)

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

    @Property(float, notify=busyChanged)
    def busyProgress(self):
        """0..1 while a task with counted steps runs, else -1"""
        p = self._busy_progress
        return p[1] / p[2] if p else -1.0

    @Property(str, notify=busyChanged)
    def busyDetails(self):
        return self._busy_details if self._busy_progress else ""

    @Property("QVariantMap", notify=statusChanged)
    def status(self):
        return self._status

    @Property(bool, notify=altModeChanged)
    def altMode(self):
        return self.alt_mode

    def _poll_status(self):
        sm = self.state_manager
        busy = sm.is_busy()
        # get_busy_message() returns a message once (then None): keep it while busy
        message = (sm.get_busy_message() or self._busy_message) if busy else ""
        progress = getattr(sm, "busy_progress", None) if busy else None
        details = (sm.busy_details or "") if busy else ""
        if progress:
            # A task with counted steps (snapshot loading): its title instead of the messages of
            # the single steps (adding chain, processor, ...), which changed back and forth
            message = progress[0]
        if busy != self._busy or message != self._busy_message or progress != self._busy_progress \
                or details != self._busy_details:
            self._busy = busy
            self._busy_message = message
            self._busy_progress = progress
            self._busy_details = details
            self.busyChanged.emit()
        self._power_save_tick()
        zs = sm.zynseq
        try:
            main_mute = bool(sm.zynmixer_bus.get_mute(0))
        except Exception:
            main_mute = False
        status = {"xrun": bool(sm.status_xrun), "xrunLevel": int(sm.status_xrun or 0),
                  "cpuLoad": int(sm.status_cpu_load or 0),
                  "audioRecorder": bool(sm.audio_recorder.status),
                  "midi": bool(sm.status_midi), "midiRecorder": bool(sm.status_midi_recorder),
                  "midiPlayer": bool(sm.status_midi_player), "midiClock": bool(sm.status_midi_clock),
                  "audioPlayer": bool(sm.status_audio_player),
                  "seqPlay": bool(zs and zs.playing_sequences > 0),
                  "seqRecord": bool(zs and zs.libseq and zs.libseq.isMidiRecord()),
                  "mainMute": main_mute,
                  "undervoltage": bool(sm.status_undervoltage),
                  "updateAvailable": bool(sm.update_available),
                  "overtemp": bool(sm.status_overtemp),
                  "powerSave": bool(sm.power_save_mode),
                  # The Tk mixer's title and tempo (zynthian_gui_mixer set_title / status)
                  "snapshotTitle": self._snapshot_title(),
                  "tempo": float(zs.get_tempo()) if zs else 0.0,
                  "beat": int(getattr(zs, "beat", 0) or 0) if zs else 0,
                  "bpb": int(getattr(zs, "bpb", 4) or 4) if zs else 4}
        # Battery: read every 5 s (sysfs), shown while there is a system battery
        self._battery_ticks = getattr(self, "_battery_ticks", 0) - 1
        if self._battery_ticks <= 0:
            self._battery_ticks = 25
            self._battery = battery_status()
        if self._battery is not None:
            status["battery"], status["batteryAc"] = self._battery
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
            zynconf.save_config({"ZYNTHIAN_QT_KEYPAD": "docked" if self._keypad_docked else "off"})
        except Exception as e:
            logging.warning(f"Can't save the keypad setting: {e}")

    @Property(QObject, constant=True)
    def controlXY(self):
        return self.control_xy

    @Property(QObject, constant=True)
    def keypadLeds(self):
        return self.keypad_leds

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
        self.helpClose()
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
        if name in ("mixer", "launcher"):
            self._last_root = name
        if name != self.current_screen:
            self.current_screen = name
            self.currentScreenChanged.emit()
        self.setup_zynpots()
        self.notify_screen()

    def notify_screen(self):
        """Announce the screen shown under its Tk name (zynqt.screen_names), as
        zynthian_gui.show_screen: SS_GUI_SHOW_SCREEN with screen=name, sent directly from the GUI
        thread once the screen is current, only when the name changed. Controller drivers change
        their buttons and LEDs by it; the pattern editor calls this when it switches to CCs
        (Tk's pated_cc)."""
        name = self.get_current_screen()
        if name != self._sent_screen:
            self._sent_screen = name
            zynsigman.send(zynsigman.S_GUI, zynsigman.SS_GUI_SHOW_SCREEN, screen=name)

    def qt_screen_name(self, name):
        """The Qt screen for name, a Qt or Tk screen name (zynqt.screen_names); None: the
        current screen (zynthian_gui.show_screen)"""
        if name is None:
            return self.current_screen
        special = None
        if name == "control":
            sm = self.state_manager
            proc = self.current_processor
            for screen, sproc in (("tempo", sm.tempo_processor), ("alsa_mixer", sm.alsa_mixer_processor),
                                  ("audio_player", sm.audio_player)):
                if proc is not None and proc is sproc:
                    special = screen
        return qt_name(name, self._last_root, special)

    @gui_thread
    def show_screen(self, name, history=True, params=None):
        """Show screen name (a Qt or Tk name); from any thread"""
        name = self.qt_screen_name(name)
        if name not in QML_SCREENS and name not in self.list_screens:
            logging.warning(f"Qt UI has no screen '{name}' (yet)")
            self.show_info(f"'{name}' is not in the Qt UI yet.")
            return
        if history and name != self.current_screen and self.current_screen not in NO_HISTORY_SCREENS:
            self.screen_history.append(self.current_screen)
            del self.screen_history[:-20]
        # As zynthian_gui.prune_screen_history: a screen shown again ends the history where it
        # was (BACK from it doesn't come back to itself: chain control after a preset was chosen)
        if name in self.screen_history:
            del self.screen_history[self.screen_history.index(name):]
        self._set_current_screen(name, params)

    @gui_thread
    def replace_screen(self, name):
        """Show name instead of the current screen (BACK skips the current one)"""
        self.show_screen(name, history=False)

    @gui_thread
    def show_screen_reset(self, name):
        self.screen_history = []
        self.show_screen(name, history=False)

    @gui_thread
    def purge_history(self, name):
        name = self.qt_screen_name(name)
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

    @gui_thread
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

    @gui_thread
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
        if self._help_html:
            self.helpClose()
            return
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
        screen = self._screen_obj()
        if screen and screen.back():
            return
        self.close_screen()

    @gui_thread
    def close_screen(self):
        """As zynthian_gui.close_screen: the previous screen, the mixer (root) without one"""
        if self.screen_history:
            self._set_current_screen(self.screen_history.pop())
        elif self.current_screen not in ("mixer", "launcher"):
            self._set_current_screen("mixer")

    def _snapshot_title(self):
        """The loaded snapshot's name and the ZS3's, as zynthian_gui_mixer.set_title"""
        sm = self.state_manager
        if not sm.last_snapshot_fpath:
            return ""
        title = os.path.splitext(sm.last_snapshot_fpath)[0].rsplit("/", 1)[-1].replace("last_state", "Last State")
        zs3 = sm.get_zs3_title()
        if zs3 and zs3 != "Last state":
            title += f": {zs3}"
        return title

    def _screen_obj(self, name=None):
        """The object behind screen name (default: the current one): a selector screen or the
        Python side of a QML screen"""
        name = name or self.current_screen
        return self.list_screens.get(name) or self.qml_screen_objects.get(name)

    def _overlay_shown(self):
        """A dialog over the screens takes the keys (Tk: they are screens of their own)"""
        return bool(self._help_html or self._value_editor or self._keyboard_action
                    or self._confirm_action or self._moving_chain or self._moving_processor is not None)

    def _navigate(self, what):
        """Arrows and SELECT: the keyboard, the confirm dialog, the selector screen shown, or the
        QML screen"""
        if self._help_html:
            if what in ("up", "down"):
                self.helpScroll.emit(-1 if what == "up" else 1)
            elif what in ("select", "select_bold"):
                self.helpClose()
            return
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

    @gui_thread
    def show_info(self, text, ms=2500):
        """The info box with text for ms; from any thread (the timer that clears it runs only
        when started in the GUI thread)"""
        self._set_info(text)
        self._info_timer.start(ms)

    @Property(str, notify=confirmChanged)
    def confirmText(self):
        return self._confirm_text

    @gui_thread
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

    @gui_thread
    def show_file_selector(self, cb_func, fexts=None, dirnames=None, path=None, preload=False):
        """A file for a path controller (zynthian_gui.cb_show_file_selector): cb_func(path) for
        the chosen file; preload: the selected file is applied while browsing and the value
        restored on leaving without a choice (zynqt.screens.file_selector)"""
        screen = self.list_screens["file_selector"]
        if self.current_screen == "file_selector" and screen.cb_func == cb_func:
            return  # asked again while it is shown (the knob turned on): keep the preview's start
        self._close_overlays()
        screen.config(cb_func, fexts=fexts, dirnames=dirnames, path=path, preload=preload)
        self.show_screen("file_selector")

    def _control_mode(self, mode):
        """SS_GUI_CONTROL_MODE (SooperLooper after selecting a loop): chain control leaves its
        select mode"""
        if mode in ("control", "select") and self.current_screen == "chain_control":
            self.chain_control_screen.set_mode(mode)

    @gui_thread
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

    @gui_thread
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

    @gui_thread
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

    # Help view (zynthian_gui_help): the zynthian-help page of the screen shown, links followed

    # The help pages' style sheet is for a browser; Qt's rich text gets the basics
    HELP_STYLE = ("<style>a { color: #5ab4f0; } h1 { font-size: x-large; } h2, h3 { color: #c0c0c0; }"
                  " .note-block { color: #f0d080; }</style>")

    @Property(bool, notify=helpChanged)
    def helpShown(self):
        return bool(self._help_html)

    @Property(str, notify=helpChanged)
    def helpHtml(self):
        return self._help_html

    @Property(str, notify=helpChanged)
    def helpBaseUrl(self):
        return "file://" + os.path.dirname(self._help_path or zynthian_help.help_dir + "/") + "/"

    def _help_topic(self):
        """The help file name for the screen shown (as the Tk screens' get_help_fpath)"""
        name = self.current_screen
        if name in ("chain_control", "tempo", "alsa_mixer", "audio_player", "midi_key_range"):
            proc = self.current_processor
            if name == "chain_control" and proc is not None and getattr(proc, "name", None):
                return [f"{proc.name.lower()}.html", "chain_control.html"]
            return [f"{name}.html", "chain_control.html"]
        screen = self.list_screens.get(name)
        if screen is not None:
            return [f"{name}.html", "selector_grid.html" if screen.kind == "grid" else "selector.html"]
        return [f"{name}.html"]

    @gui_thread
    def show_help(self, fpath=None):
        """Show the help page fpath (a path, a file name or "index:"), else the screen's page"""
        layout = zynthian_gui_config.layout["name"]
        if fpath == "index:":
            self._show_help_index()
            return
        names = [fpath] if fpath else self._help_topic()
        for name in names:
            path = zynthian_help.find_file(name, layout)
            if path:
                self._show_help_page(path)
                return
        logging.warning(f"No help for '{names[0]}'")
        self._show_help_index()

    def _show_help_page(self, path):
        proc = self.current_processor
        proc_info = None
        try:
            info = self.chain_manager.engine_info[proc.eng_code]
            proc_info = f"{info['NAME']}: {info['DESCR']}"
        except Exception:
            pass
        try:
            html = zynthian_help.page_html(path, proc_info, drop_classes=("knob_action",))
        except Exception as e:
            logging.error(f"help page {path}: {e}")
            self.show_info("Can't read the help page.")
            return
        self._set_help(html, path)

    def _show_help_index(self):
        items = zynthian_help.index(zynthian_gui_config.layout["name"])
        if not items:
            self.show_info("No help pages installed.")
            return
        links = "".join(f'<li><a href="{path}">{title}</a></li>' for title, path in items)
        self._set_help(f"<html><body><h1>Help Index</h1><ul>{links}</ul></body></html>", "")

    def _set_help(self, html, path):
        nav = "<p><a href=\"index:\">Index</a></p>"
        if "<body" in html:
            head, _, body = html.partition("<body")
            body_tag, _, rest = body.partition(">")
            html = f"{head}<body{body_tag}>{nav}{rest}"
        else:
            html = nav + html
        self._help_html = self.HELP_STYLE + html
        self._help_path = path
        self.helpChanged.emit()

    @Slot(str)
    def helpLink(self, href):
        if href == "index:":
            self._show_help_index()
        elif href.startswith(("http:", "https:", "mailto:")):
            self.show_info(href)
        else:
            href = href.split("#")[0]
            if href.startswith("file://"):
                href = href[7:]
            if not href:
                return
            path = href if os.path.isabs(href) else os.path.join(os.path.dirname(self._help_path or
                                                                            zynthian_help.help_dir + "/"), href)
            if os.path.exists(path):
                self._show_help_page(path)
            else:
                self.show_help(os.path.basename(path))

    @Slot()
    def helpClose(self):
        if self._help_html:
            self._help_html = ""
            self._help_path = ""
            self.helpChanged.emit()

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

    @gui_thread
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
            new_chain = "chain_id" not in self.chain_edit.status
            if new_chain:
                # As zynthian_gui.modify_chain: a new chain starts a new history, BACK from its
                # first screen (bank, preset, chain control) leads to the mixer, not into the
                # add-chain screens (type, engine, MIDI channel)
                self.screen_history = []
            if processor and processor.eng_code == "CL" and new_chain:
                # A new Clippy chain: its clips are chosen in the launcher (zynthian_gui.modify_chain)
                self.show_screen("launcher", history=False)
            else:
                # A processor added to or replaced in a chain keeps the history (Tk: chain_control
                # with reset=False): BACK from chain control to the screen before it, as chain
                # control shown again ends the history there; from bank/preset to the engine list
                self.chain_control(chain_id, processor, force_bank_preset=True, history=not new_chain)

    @gui_thread
    def chain_control(self, chain_id=None, processor=None, force_bank_preset=False, history=True):
        """Show a chain's processor: bank/preset selection first if it has no preset yet
        (zynthian_gui.chain_control). history: False to show it without the current screen in
        the history (a new chain)"""
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
            if self.list_screens["preset"].is_flat(processor):
                screen = "preset"   # the flat list: all banks with their presets
            elif len(processor.get_bank_list()) > 1:
                screen = "bank"
            else:
                processor.set_bank(0)
                processor.load_preset_list()
                if len(processor.preset_list) > 1:
                    screen = "preset"
                elif not processor.bank_list and has_bank_dirs(processor):
                    # Nothing installed yet (no soundfonts, ...): the bank list says how to add
                    # some; BACK leads to the processor (not out of the new chain)
                    screen = "bank_hint"
        # As zynthian_gui_chain_control.set_chain(reset=True): control mode
        self.chain_control_screen.set_mode("control")
        if screen == "bank_hint":
            self.show_screen("bank", history=history)
            if "chain_control" in self.screen_history:
                del self.screen_history[self.screen_history.index("chain_control"):]
            self.screen_history.append("chain_control")
        else:
            self.show_screen(screen, history=history)

    def get_current_screen(self):
        """The current screen's Tk name (zynqt.screen_names): for drivers and shared code"""
        return tk_name(self.current_screen, self.current_screen == "pattern_editor"
                       and bool(getattr(self.pattern_editor, "cc_mode", False)))

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
        pressed = {}    # switch index -> press time
        repeating = {}  # switch index -> repeat intervals left before the next push action
        pot_repeating = {}  # zynpot index -> [intervals left, delta] while a key turns it
        repeat_delay = 3        # as zynthian_gui: intervals before auto repeat starts
        repeat_interval = 0.15  # seconds
        while not self.exit_flag:
            long_ts = monotonic() - zynthian_gui_config.zynswitch_long_seconds
            for i, ts in list(pressed.items()):
                if ts < long_ts and not self.zynswitch_autolong_disabled:
                    del pressed[i]
                    # Not while its encoder is turned (push-rotate)
                    zpi = self._switch_zynpot(i)
                    if zpi is None or self.zynpot_pr_state[zpi] <= 1:
                        self._cuiaRequested.emit("_zynswitch", [i, "L"])
            try:
                event = self.cuia_queue.get(True, repeat_interval)
            except Empty:
                event = None
            # Held switches with a push action (arrows): repeat it
            for i in list(repeating):
                if repeating[i]:
                    repeating[i] -= 1
                else:
                    self._cuiaRequested.emit("_zynswitch", [i, "P"])
            # Encoders turned by held keys (key bindings ZYNPOT i,d): repeat
            for i, r in list(pot_repeating.items()):
                if r[0]:
                    r[0] -= 1
                else:
                    self._cuiaRequested.emit("_zynpot", [i, r[1]])
            if event is None:
                continue
            if event == "__EXIT__":
                break
            # Whatever goes wrong with one event: logged, the thread goes on (it ends only
            # with __EXIT__)
            try:
                parsed = cuia_event(event)
                if parsed is None:
                    continue    # logged
                cuia, params = parsed
                # As zynthian_gui's CUIA thread: user activity (wakes the screen from power save)
                if cuia.lower() != "power_save":
                    self.state_manager.set_event_flag()
                if cuia.lower() == "zynpot":
                    # ZYNPOT i,d (as zynthian_gui: from key bindings with P / R: repeat while held)
                    pot = zynpot_params(params)
                    if pot is None:
                        continue    # logged; bad parameters must not end this thread
                    i, d = pot
                    t = str(params[2]).upper() if len(params) > 2 else ""
                    if t == "R":
                        pot_repeating.pop(i, None)
                        continue
                    if t == "P":
                        pot_repeating[i] = [repeat_delay, d]
                    self._cuiaRequested.emit("_zynpot", [i, d])
                    continue
                if cuia.lower() == "zynswitch":
                    sw = zynswitch_params(params)
                    if sw is None:
                        continue    # logged; bad parameters must not end this thread
                    i, t, dtus = sw
                    # The push switch of an encoder (kits): push-rotate (zynthian_gui.zynpot_pr_state)
                    zpi = self._switch_zynpot(i)
                    if t == "P":
                        if zpi is not None:
                            self.zynpot_pr_state[zpi] = 1
                            pressed[i] = monotonic()
                        elif self._push_action(i):
                            # A push action (zynthian_gui.zynswitch_push): now, repeated while held
                            self._cuiaRequested.emit("_zynswitch", [i, "P"])
                            repeating[i] = repeat_delay
                        else:
                            pressed[i] = monotonic()
                            if i >= 4:
                                # The screen may take the push (zynthian_gui.zynswitch_push: the
                                # Organelle's AUX switch)
                                self._cuiaRequested.emit("_zynswitch", [i, "P"])
                        continue
                    turned = zpi is not None and self.zynpot_pr_state[zpi] > 1
                    if zpi is not None:
                        self.zynpot_pr_state[zpi] = 0
                    if t == "R":
                        if repeating.pop(i, None) is not None:
                            continue
                        ts = pressed.pop(i, None)
                        if ts is None:
                            continue  # long press already handled
                        # The kit's switches: zyncore's (debounced) duration in µs
                        seconds = dtus / 1000000 if dtus is not None else monotonic() - ts
                        t = self._switch_timing(seconds)
                    else:
                        # S / B / L given (OSC): ends a press started with P
                        pressed.pop(i, None)
                        repeating.pop(i, None)
                    if turned:
                        continue  # its encoder was turned while pushed: no switch action
                    self._cuiaRequested.emit("_zynswitch", [i, t])
                    continue
                self._cuiaRequested.emit(str(cuia), params)
            except Exception as e:
                logging.exception(f"CUIA event {event!r} failed: {e}")

    def cuia_zynpot(self, params=None):
        """ZYNPOT i,d run directly (zynthian_gui.cuia_zynpot): the CUIAs that don't come through
        cuia_queue (custom switch actions, QML, callable_ui_action); the queue's take the
        _zynpot path (key repeat)"""
        pot = zynpot_params(params)
        if pot is not None:
            self.cuia__zynpot(list(pot))

    def cuia__zynpot(self, params):
        """Encoder i turned by d (the kit's encoders, ZYNPOT): the current screen's zynpot(i, d)
        if it has one; chain control turns its controllers (knob i slot i, as Tk), elsewhere the
        select encoder moves the selection. A dialog shown takes the encoders instead (Tk: they
        are screens of their own)"""
        i, d = int(params[0]), int(params[1])
        if self._overlay_shown():
            self._overlay_zynpot(i, d)
            return
        screen = self._screen_obj()
        func = getattr(screen, "zynpot", None)
        if callable(func) and func(i, d):
            return
        if i == zynthian_gui_config.select_ctrl:
            if self.current_screen in self.list_screens and screen is not None:
                screen.move(d)
            else:
                self._navigate("down" if d > 0 else "up")

    def _overlay_zynpot(self, i, d):
        """The encoders while a dialog is shown: the value editor's value (Tk's param editor,
        zynthian_gui_base.zynpot_cb: the layout's ctrl_order[3] by one step, ctrl_order[2] by
        ten), the help scrolled (zynthian_gui_help.zynpot_cb), the select knob moves a chain or
        processor being moved; the confirm dialog and the keyboard take none (as Tk's)"""
        if self._help_html:
            if i == zynthian_gui_config.select_ctrl and d:
                self.helpScroll.emit(1 if d > 0 else -1)    # by most of a page (Tk: by lines)
        elif self._moving_chain or self._moving_processor is not None:
            if i == zynthian_gui_config.select_ctrl:
                self._navigate("down" if d > 0 else "up")
        elif self._value_editor:
            order = zynthian_gui_config.layout.get("ctrl_order", (0, 1, 2, 3))
            if i == order[3]:
                self.valueEditorStep(d)
            elif i == order[2]:
                self.valueEditorStep(10 * d)

    def setup_zynpots(self, screen=None):
        """The kit's encoder behaviour (acceleration) for the screen shown, as the Tk screens set
        it (zynthian_gui_controller.config, the mixer's and pattern editor's setup_zynpots): the
        screen's zynpot_steps() {encoder: step}, list screens the select encoder by the list's
        length; the others are left as they are (as Tk). screen: only if it is the one shown"""
        if not self.hw_input.pots:
            return
        current = self._screen_obj()
        if current is None or (screen is not None and screen is not current):
            return
        func = getattr(current, "zynpot_steps", None)
        if callable(func):
            steps = func()
        elif self.current_screen in self.list_screens:
            steps = {zynthian_gui_config.select_ctrl: list_step(len(current.model.entries))}
        else:
            steps = None
        for i, step in (steps or {}).items():
            if 0 <= i < zynthian_gui_config.num_zynpots and self._zynpot_steps.get(i) != step:
                try:
                    lib_zyncore.setup_behaviour_zynpot(i, step)
                    self._zynpot_steps[i] = step
                except Exception as e:
                    logging.error(f"encoder {i} behaviour: {e}")

    def _switch_zynpot(self, i):
        """The encoder whose push switch i is (zynthian_gui_config.zynpot2switch), or None"""
        try:
            zpi = zynthian_gui_config.zynpot2switch.index(i)
        except (AttributeError, ValueError):
            return None
        return zpi if zpi < len(self.zynpot_pr_state) else None

    def zynpot_push_rotate(self, i):
        """Encoder i turned while pushed (kits): counted, so its release does nothing (as
        zynthian_gui_controller.zynpot_cb); the controller screens nudge fine then"""
        if 0 <= i < len(self.zynpot_pr_state) and self.zynpot_pr_state[i] > 0:
            self.zynpot_pr_state[i] += 1
            return True
        return False

    @Slot()
    def _take_zynpots(self):
        """The kit's encoders (HwInput): the deltas since the last call, to the current screen"""
        for i, d in self.hw_input.take_pot_deltas():
            try:
                self.cuia__zynpot([i, d])
            except Exception as e:
                logging.exception(f"zynpot {i},{d} of screen {self.current_screen} failed: {e}")

    @staticmethod
    def _has_switch_ui_action(i):
        """Custom switch i (from 4) has UI actions (the others are MIDI switches: zyncore's)"""
        try:
            return bool(zynthian_gui_config.custom_switch_ui_actions[i - 4])
        except IndexError:
            return False

    def _wiring_midi_setup(self):
        chain = self.chain_manager.get_active_chain()
        try:
            zynthian_wiring.wiring_midi_setup(chain.midi_chan if chain is not None else None)
        except Exception as e:
            logging.error(f"wiring MIDI set-up: {e}")

    def _push_action(self, i):
        """The custom switch's push action (wiring configuration UI_ACTION_PUSH), or None"""
        if i < 4:
            return None
        try:
            config = zynthian_gui_config.custom_switch_ui_actions[i - 4]
        except IndexError:
            return None
        if not config:
            return None
        return (self.alt_mode and config.get("AP")) or config.get("P")

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
        i, t = int(params[0]), str(params[1]).upper()
        if i < 4:
            self.zynswitch(i, t)
            return
        # The screen's switch(i, t) first, as zynthian_gui.zynswitch_short / bold / long (the
        # pattern editor's ALT clipboard, block and CC keys)
        screen = self._screen_obj()
        func = getattr(screen, "switch", None)
        if t in ("P", "S", "B", "L") and not self._overlay_shown() and callable(func):
            try:
                if func(i, t):
                    return
            except Exception as e:
                logging.exception(f"switch {i},{t} of screen {self.current_screen} failed: {e}")
                return
        if t == "P" and not self._push_action(i):
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

    def zynswitch_disable_autolong(self):
        self.zynswitch_autolong_disabled = True

    def zynswitch_enable_autolong(self):
        self.zynswitch_autolong_disabled = False

    def zynswitch(self, i, t):
        """One of the four standard switches (0-3) pushed (P), or released after a short (S),
        bold (B) or long (L) press. As zynthian_gui.zynswitch_short/bold/long/push: the screen's
        switch(i, t) first (True: handled), then the defaults:

        | switch | short      | bold        | long           |
        | 0      | -          | chain manager | help         |
        | 1      | back       | root (mixer) | power          |
        | 2      | MIDI learn | ZS3 (snapshot from ZS3) | snapshot |
        | 3      | select     | bold select | all sounds off |
        """
        screen = self._screen_obj()
        func = getattr(screen, "switch", None)
        if not self._overlay_shown() and callable(func):
            try:
                if func(i, t):
                    return True
            except Exception as e:
                logging.exception(f"switch {i},{t} of screen {self.current_screen} failed: {e}")
                return True
        if t == "P":
            return False
        if i == 0:
            if t == "B":
                self.show_screen("chain_manager")
            elif t == "L":
                self.cuia_help()
        elif i == 1:
            if t == "S":
                self.back()
            elif t == "B":
                self._close_overlays()
                self.show_screen_reset("mixer")
            elif t == "L":
                self.cuia_power()
        elif i == 2:
            if t == "S":
                self.cuia_toggle_midi_learn()
            elif t == "B":
                if self.current_screen == "zs3":
                    self.cuia_screen_snapshot()
                else:
                    self.cuia_screen_zs3()
            elif t == "L":
                self.cuia_screen_snapshot()
        elif i == 3:
            if t in ("S", "B"):
                self.switch_select(t)
            elif t == "L":
                self.cuia_all_sounds_off()
        return True

    def switch_select(self, t="S"):
        """The select switch (SEL key, switch 3): dialogs, then the screen's switch_select(t) if
        it has one, else its navigate("select" / "select_bold")"""
        screen = self._screen_obj()
        func = getattr(screen, "switch_select", None)
        if not self._overlay_shown() and callable(func):
            if func(t):
                return
        self._navigate("select" if t == "S" else "select_bold")

    def _close_overlays(self):
        """Close the dialogs over the screens (BACK:B, switch 1 bold: to the root)"""
        self.helpClose()
        self.endMoveProcessor()
        self.endMoveChain()
        if self._value_editor:
            self.valueEditorCancel()
        if self._keyboard_action:
            self.keyboardCancel()
        if self._confirm_action:
            self.confirmNo()

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
        screen = self._screen_obj()
        screen_func = getattr(screen, "cuia_" + name, None) if screen is not None and not self._overlay_shown() else None
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
        if len(parts) == 3 and parts[1] == "STATUS":
            # A query (/STATUS/BUSY), answered also while busy
            self.state_manager.osc_status_reply(self._osc_server, src, parts[2])
            return
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

    # Toolkit interface of the websocket API (zyngui.zynthian_websocket)

    def websocket_run_idle(self, fn, *args):
        self._gui.post(functools.partial(fn, *args))

    def websocket_run_later(self, ms, fn, *args):
        call = functools.partial(fn, *args)
        self._gui.run(lambda: QTimer.singleShot(ms, self, call))

    def websocket_key_event(self, action, code):
        self._gui.run(lambda: self._ws_keys.event(action, code))

    def websocket_cuia(self, cuia, args, src):
        """Into the CUIA queue (the CUIA thread, then the GUI thread), as OSC; ZYNPOT / ZYNSWITCH
        with arguments the CUIA thread doesn't accept are dropped here, with the client in the
        log"""
        args = list(args) if isinstance(args, (list, tuple)) else ([] if args is None else [args])
        if not ws_cuia_args_ok(cuia, args):
            logging.warning(f"websocket {src}: bad arguments for CUIA {cuia}: {args}")
            return
        self.cuia_queue.put_nowait((str(cuia), args, src))

    def websocket_wsleds(self):
        return self.keypad_leds

    def screen_state_current(self):
        return current_state(self)

    def get_screen_title(self, view):
        return view.title() if view is not None else ""

    def screen_state_watch(self, on):
        if on:
            self._ws_watch.start()
        else:
            self._ws_watch.stop()

    # CUIA implementations (the subset the Qt UI has so far)

    def cuia_show_screen(self, params):
        """As zynthian_gui: the screen with a new history ("root": the mixer)"""
        if params:
            name = str(params[0])
            self.show_screen_reset(name)   # Tk names too ("root": the last root screen)

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
        if screen is self.chain_control_screen:
            # As zynthian_gui: the state manager's learn state is the screen's learning mode
            # (nothing in select mode)
            if screen.selectMode:
                self.state_manager.set_midi_learn(None)
                return
            screen.toggle_midi_learn()
            self.state_manager.set_midi_learn(screen.midi_learning)
        elif screen is not None:
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
            self.chain_manager.clean_midi_binding(zctrl)
            cc.refresh_bindings()

    def cuia_action_midi_unlearn(self, params=None):
        if self._learn_screen() is self.chain_control_screen:
            self.chain_control_screen.midi_unlearn_action()

    def cuia_midi_unlearn_mixer(self, params=None):
        for chain in self.chain_manager.chains.values():
            if chain.zynmixer_proc:
                self.chain_manager.clean_midi_binding(chain.zynmixer_proc)

    def cuia_midi_unlearn_node(self, params=None):
        """params: processor id, controller symbol (zynthian_gui passes both as one list, which
        clear_midi_binding(proc, symbol) doesn't take)"""
        if params and len(params) > 1:
            proc = self.chain_manager.processors.get(int(params[0]))
            if proc is not None:
                self.chain_manager.clear_midi_binding(proc, str(params[1]))

    def cuia_midi_unlearn_chain(self, params=None):
        self.chain_manager.clean_midi_binding(params[0] if params else self.chain_manager.active_chain.chain_id)

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

    def cuia_pattern_editor_window(self, params=None):
        """PATTERN_EDITOR_WINDOW start length low high [pattern]: the window of a controller's
        step sequencer (DrivenByMoss' ClipEditWindow) on the pattern editor: the steps from start
        for length (beats), the notes low..high (MIDI notes); the pattern shown if none is given.
        Doesn't switch screens (docs/controller-view-sync.md)."""
        try:
            start, length, low, high = (float(params[0]), float(params[1]), int(params[2]), int(params[3]))
            pattern = int(params[4]) if len(params) > 4 and params[4] is not None else None
        except (TypeError, ValueError, IndexError):
            logging.warning(f"PATTERN_EDITOR_WINDOW needs start, length, low, high: {params}")
            return
        self.pattern_editor.show_window(start, length, low, high, pattern)

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
        """As zynthian_gui.cuia_menu: the current screen's own menu (show_menu: its options) if it
        has one, else the main menu"""
        if self._overlay_shown():
            return
        show_menu = getattr(self._screen_obj(), "show_menu", None)
        if callable(show_menu):
            show_menu()
        elif self.current_screen != "main_menu":
            self.showScreen("main_menu")

    def cuia_back(self, params=None):
        """BACK; BACK:B goes to the root (the mixer), as zynthian_gui.cuia_back (screens can take
        it first with cuia_back: the mixer opens the chain manager)"""
        if params and str(params[0]).upper() == "B":
            self._close_overlays()
            self.show_screen_reset("mixer")
        else:
            self.back()

    def cuia_v5_zynpot_switch(self, params=None):
        """A V5 knob pushed (params: knob, S/B/L). The screen's cuia_v5_zynpot_switch comes
        first (_run_cuia); the defaults as zynthian_gui: long: the X-Y controller if both axes
        are set; knob 3 short/bold: switch 3"""
        try:
            i, t = int(params[0]), str(params[1]).upper()
        except (TypeError, ValueError, IndexError):
            logging.error(f"V5_ZYNPOT_SWITCH: wrong parameters {params}")
            return
        if t == "L":
            if self.control_xy.available():
                self.show_screen("control_xy")
        elif i == 3 and t in ("S", "B"):
            self.zynswitch(3, t)

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
        self.switch_select("B" if t in ("B", "L") else "S")

    def cuia_bold_select_action(self, params=None):
        self.switch_select("B")

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
    def selectChain(self, chain_id):
        """A mixer strip touched: make its chain the active one (Tk's fader / strip press)"""
        if chain_id >= 0:
            self.chain_manager.set_active_chain_by_id(chain_id)

    @Slot(int)
    def openChainManagerOptions(self, chain_id):
        """Long press on a mixer strip's legend (Tk): the chain manager at the chain's options"""
        if chain_id >= 0:
            self.chain_manager.set_active_chain_by_id(chain_id)
        self.show_screen("chain_manager")

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
        """As zynthian_gui.cuia_bank_preset: from the bank list back; from the presets to the
        banks (back with a single bank); elsewhere the presets of the current processor if it
        has a preset list, else its banks. Neither: the bank list's hint for an engine that
        reads its banks from directories (no soundfonts installed, ...), else (Tk) the empty
        preset list and its options"""
        sm = self.state_manager
        if self.current_screen == "alsa_mixer":
            return
        if self.current_processor is not sm.audio_player or self.current_screen != "audio_player":
            chain = self.chain_manager.get_active_chain()
            if chain is not None and chain.current_processor is not None:
                self.current_processor = chain.current_processor
        proc = self.current_processor
        if proc is None:
            return
        if self.current_screen == "chain_control" and proc.eng_code == "CL":
            # Clippy: the selected clip's file
            proc.engine.request_file()
        elif self.current_screen == "bank":
            self.back()
        elif self.current_screen == "preset":
            if len(proc.get_bank_list()) > 1:
                self.replace_screen("bank")
            else:
                self.back()
        else:
            bank_list = proc.get_bank_list()
            if proc.preset_list and proc.preset_list[0][0] != "" or self.list_screens["preset"].is_flat(proc):
                self.show_screen("preset")
            elif bank_list and bank_list[0][0] != "":
                self.show_screen("bank")
            elif not bank_list and has_bank_dirs(proc):
                self.show_screen("bank")
            else:
                self.show_screen("preset")
                self.list_screens["preset"].show_preset_options()

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

    def cuia_program_change(self, params=None):
        """PROGRAM_CHANGE n[,chan] (F1-F4 on the V5 keypad), n also "+" / "-": a program change on
        the active chain's channel, as if from a MIDI device (zynthian_gui.cuia_program_change)"""
        if not params:
            return
        if len(params) > 1:
            chan = int(params[1])
        else:
            chain = self.chain_manager.get_active_chain()
            chan = chain.midi_chan if chain is not None and isinstance(chain.midi_chan, int) else 0
            if not 0 <= chan < 16:
                chan = 0
        if not hasattr(self, "_prog_change"):
            self._prog_change = [0] * 16
        if params[0] == "+":
            pgm = self._prog_change[chan] + 1
        elif params[0] == "-":
            pgm = self._prog_change[chan] - 1
        else:
            pgm = int(params[0])
        if 0 <= chan < 16 and 0 <= pgm < 128:
            lib_zyncore.write_zynmidi_program_change(chan, pgm)
            self._prog_change[chan] = pgm

    def cuia_reload_key_binding(self, params=None):
        """Re-read the computer keyboard bindings (webconf saves them)"""
        load_bindings()

    # Speech (ZynVoice): not in the Qt UI yet. Keys show it; TTS_ANNOUNCE / TTS_REGISTER (from
    # code and OSC clients, not keys) do nothing

    def _no_tts(self, params=None):
        self.show_info("Speech (ZynVoice) is not available yet.")

    def _no_tts_quiet(self, params=None):
        logging.debug(f"no speech (ZynVoice) in the Qt UI: ignored {params}")

    cuia_tts_toggle_enable = _no_tts
    cuia_tts_toggle_playback = _no_tts
    cuia_tts_toggle_pause = _no_tts
    cuia_tts_pause = _no_tts
    cuia_tts_resume = _no_tts
    cuia_tts_stop = _no_tts
    cuia_tts_announce = _no_tts_quiet
    cuia_tts_register = _no_tts_quiet

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

    # Backend actions (zynthian_gui's system, ZS3, MIDI and Zynaptik CUIAs)

    def cuia_reload_midi_config(self, params=None):
        """Re-read the MIDI profile (webconf sends it after saving)"""
        self.state_manager.reload_midi_config()

    def cuia_reload_wiring_layout(self, params=None):
        """Re-read the wiring configuration: custom switches, Zynaptik, Zyntof (webconf)"""
        chain = self.chain_manager.get_active_chain()
        zynthian_wiring.reload_wiring_layout(chain.midi_chan if chain is not None else None)

    def cuia_last_state_action(self, params=None):
        """Save the state for the next start, or delete it (admin: restore last state)"""
        zynthian_admin_settings.last_state_action(self.state_manager)

    def cuia_zs3_next(self, params=None):
        """The next ZS3; params[0] true: from the last back to the first"""
        self.state_manager.load_next_zs3(bool(params[0]) if params else False)

    def cuia_zs3_prev(self, params=None):
        self.state_manager.load_prev_zs3(bool(params[0]) if params else False)

    def cuia_clean_all(self, params=None):
        """Remove all chains and sequences: confirmed, or params[0] "CONFIRM" (as zynthian_gui)"""
        def clean_all():
            sm = self.state_manager
            if self.chain_manager.get_chain_count() > 1:
                sm.save_last_state_snapshot()
            sm.clean_all()
            self.show_screen_reset("mixer")
        if params and str(params[0]).upper() == "CONFIRM":
            clean_all()
        else:
            self.confirm("Remove all chains and sequences?", clean_all)

    def cuia_zyn_cc(self, params=None):
        """ZYN_CC chan,cc,value[,R,release value]: a CC as if from a MIDI device (switches)"""
        if params and len(params) > 2:
            chan, cc = int(params[0]), int(params[1])
            if str(params[-1]).upper() == "R":
                if len(params) > 3:
                    lib_zyncore.write_zynmidi_ccontrol_change(chan, cc, int(params[3]))
            else:
                lib_zyncore.write_zynmidi_ccontrol_change(chan, cc, int(params[2]))

    def cuia_enable_midi_learn_cc(self, params=None):
        """Learn a CC for a controller: params processor id, controller symbol (as
        MIDI_UNLEARN_NODE); in chain control also the controller's position (0-3)"""
        zctrl = None
        if params and len(params) > 1:
            proc = self.chain_manager.processors.get(int(params[0]))
            if proc is not None:
                zctrl = proc.controllers_dict.get(str(params[1]))
        elif params and self._learn_screen() is self.chain_control_screen:
            zctrl = self.chain_control_screen.controllers[int(params[0])].zctrl
        if zctrl is None:
            self.show_info("No such controller to learn.")
            return
        self.state_manager.enable_learn_cc(zctrl)

    def cuia_toggle_seq(self, params=None):
        """TOGGLE_SEQ phrase,sequence: start / stop a sequence of the current scene"""
        try:
            zs = self.state_manager.zynseq
            zs.libseq.togglePlayState(zs.scene, int(params[0]), int(params[1]))
        except (AttributeError, TypeError, IndexError, ValueError) as e:
            logging.warning(f"TOGGLE_SEQ {params}: {e}")

    def cuia_zynaptik_cvin_set_volts_octave(self, params=None):
        try:
            lib_zyncore.zynaptik_cvin_set_volts_octave(float(params[0]))
        except Exception as e:
            logging.debug(e)

    def cuia_zynaptik_cvin_set_note0(self, params=None):
        try:
            lib_zyncore.zynaptik_cvin_set_note0(int(params[0]))
        except Exception as e:
            logging.debug(e)

    def cuia_zynaptik_cvout_set_volts_octave(self, params=None):
        try:
            lib_zyncore.zynaptik_cvout_set_volts_octave(float(params[0]))
        except Exception as e:
            logging.debug(e)

    def cuia_zynaptik_cvout_set_note0(self, params=None):
        try:
            lib_zyncore.zynaptik_cvout_set_note0(int(params[0]))
        except Exception as e:
            logging.debug(e)

    def cuia_zynpot_abs(self, params=None):
        """ZYNPOT_ABS i,value (value 0..1): the screen's zynpot_abs(i, value) if it has one, else in
        chain control encoder i's controller (slot i, as Tk) to that part of its range"""
        if not params or len(params) < 2:
            return
        i, val = int(params[0]), max(0.0, min(1.0, float(params[1])))
        screen = self.list_screens.get(self.current_screen) or self.qml_screen_objects.get(self.current_screen)
        func = getattr(screen, "zynpot_abs", None)
        if callable(func):
            func(i, val)
        elif screen is self.chain_control_screen:
            if 0 <= i < len(self.chain_control_screen.controllers):
                self.chain_control_screen.controllers[i].set_abs(val)

    def cuia_api(self, params=None):
        """API sm|cm,method,params...: call a state manager / chain manager method"""
        try:
            api, method, *args = params
            obj = {"sm": self.state_manager, "cm": self.chain_manager}.get(api)
            if obj is not None:
                getattr(obj, method)(*args)
        except Exception as e:
            logging.debug(e)

    # System: power, power save, workflow capture

    def cuia_power(self, params=None):
        """Power off: asks first (Shutdown / Reboot / Cancel, as zynthian_gui_admin.power) unless
        params[0] is CONFIRM"""
        if params and str(params[0]).upper() == "CONFIRM":
            self._power(zynthian_power_control.POWEROFF)
        else:
            self._power_menu(1)

    def cuia_reboot(self, params=None):
        """Reboot: asks first unless params[0] is CONFIRM"""
        if params and str(params[0]).upper() == "CONFIRM":
            self._power(zynthian_power_control.REBOOT)
        else:
            self._power_menu(2)

    def _power_menu(self, selected):
        pc = zynthian_power_control
        self.show_options("Power", [
            ("Cancel", lambda: None, None, "cancel.png"),
            ("Shutdown", lambda: self._power(pc.POWEROFF), "Save the state and power off.", "poweroff.png"),
            ("Reboot", lambda: self._power(pc.REBOOT), "Save the state and reboot.", "reboot.png"),
        ], selected)

    def _power(self, action):
        """Save the state, then power off / reboot the way the system does it"""
        pc = zynthian_power_control
        method = pc.power_method()
        verb = "Shutting down" if action == pc.POWEROFF else "Rebooting"
        logging.info(f"{action.upper()} ({method})")
        if method == "desktop":
            self.show_info("On the desktop, power off and reboot are left to the desktop.")
        elif method == "exit_code":
            # zynthian.sh: exit code 0 powers off, 100 reboots; _do_exit saves the state
            self.show_info(f"{verb}...")
            self.exit(pc.EXIT_CODES[action])
        else:
            sm = self.state_manager
            sm.start_busy("power", f"{verb}...")

            def task():
                zynthian_admin_settings.last_state_action(sm)
                return pc.logind_power(action)

            def done(error):
                if error:
                    sm.end_busy("power")
                    logging.error(f"{action}: {error}")
                    self.show_info(f"Can't {action}: {error}", 5000)
                # else the system stops the session (and zynthian, SIGTERM) soon
            self.run_background(task, done)

    def cuia_power_save(self, params=None):
        """Blank the screen (power save mode, as zynthian_gui); the next input wakes it, as does
        POWER_SAVE 0"""
        sm = self.state_manager
        if params and str(params[0]) == "0":
            sm.set_event_flag()
            return
        sm.reset_event_flag()
        sm.last_event_ts = monotonic() - zynthian_gui_config.power_save_secs
        if zynthian_gui_config.power_save_secs <= 0 and not sm.power_save_mode:
            # Automatic power save off (power_save_check does nothing): on request only
            sm.set_power_save_mode(True)
        self._poll_status()

    def _power_save_tick(self):
        """As zynthian_gui's control thread: power save after the configured time without input or
        sound, off again on input"""
        sm = self.state_manager
        try:
            sm.power_save_check()
            if sm.power_save_mode and zynthian_gui_config.power_save_secs <= 0 and sm.last_event_flag:
                sm.reset_event_flag()
                sm.set_power_save_mode(False)
        except Exception as e:
            logging.debug(f"power save check: {e}")

    def user_activity(self, pointer):
        """Input on the window (UserActivityFilter): wakes the screen; True if the event is to be
        dropped (a touch that only wakes it, as zynthian_gui.cb_touch)"""
        sm = self.state_manager
        sm.set_event_flag()
        if sm.power_save_mode:
            self._power_save_tick()
            self._poll_status()
            return pointer
        return False

    def _no_capture(self, params=None):
        """The Tk UI's workflow capture records the X11 screen (ffmpeg x11grab) with its own input
        log: not in the Qt UI"""
        self.show_info("Workflow capture is not available in the Qt UI.")

    cuia_workflow_capture_start = _no_capture
    cuia_workflow_capture_stop = _no_capture
    cuia_workflow_capture_text = _no_capture

    # Display (zynthian_gui's layout CUIAs)

    @Property(bool, notify=topBarChanged)
    def topBarShown(self):
        return self._topbar_shown

    def _show_topbar(self, show):
        if show != self._topbar_shown:
            self._topbar_shown = show
            self.topBarChanged.emit()

    def cuia_show_topbar(self, params=None):
        self._show_topbar(True)

    def cuia_hide_topbar(self, params=None):
        self._show_topbar(False)

    def _show_cursor(self, show):
        """The mouse pointer over the window (hidden for touch-only devices)"""
        if show and self._cursor_hidden:
            QGuiApplication.restoreOverrideCursor()
        elif not show and not self._cursor_hidden:
            QGuiApplication.setOverrideCursor(QCursor(Qt.BlankCursor))
        self._cursor_hidden = not show

    def cuia_show_cursor(self, params=None):
        self._show_cursor(True)

    def cuia_hide_cursor(self, params=None):
        self._show_cursor(False)

    # The chain control screen shows and hides its processor list (ChainControl.cuia_*_sidebar);
    # the other screens have no sidebar, as in Tk nothing happens there

    def cuia_show_sidebar(self, params=None):
        pass

    def cuia_hide_sidebar(self, params=None):
        pass

    def cuia_toggle_sidebar(self, params=None):
        pass

    def cuia_toggle_screen(self, params=None):
        """TOGGLE_SCREEN name: show the screen, or close it if shown (zynthian_gui.toggle_screen)"""
        if not params:
            return
        if self.current_screen != str(params[0]):
            self.show_screen(str(params[0]))
        else:
            self.back()

    def cuia_refresh_screen(self, params=None):
        """Rebuild the screen shown (params: only if it is one of these)"""
        if params and self.current_screen not in [str(p) for p in params]:
            return
        screen = self.list_screens.get(self.current_screen) or self.qml_screen_objects.get(self.current_screen)
        if screen is not None:
            screen.build()

    def cuia_screen_calibrate(self, params=None):
        """Tk's touchscreen calibration (X11 transformation matrix): under Wayland the compositor
        maps the touchscreen (output rotation, udev calibration rules)"""
        self.show_info("Touchscreen calibration is done by the system (compositor) in the Qt UI.")

    def cuia_screen_clean(self, params=None):
        """10 s with the touches swallowed by the busy overlay, to clean the screen (as Tk)"""
        sm = self.state_manager

        def task():
            for i in range(10, 0, -1):
                sm.start_busy("clean_screen", f"Clean screen: closing in {i} s")
                sleep(1)
        # done runs also if the task fails
        self.run_background(task, lambda result: sm.end_busy("clean_screen"))

    def cuia_show_navigation_grid(self, params=None):
        """SHOW_NAVIGATION_GRID title,buttons (zynthian_gui: the grid selector with a list of
        {"title", "icon", "action"}): as options; only from code, OSC can't pass the buttons"""
        if not params or len(params) < 2 or not isinstance(params[1], (list, tuple)):
            self.show_info("SHOW_NAVIGATION_GRID needs a list of buttons.")
            return
        options = []
        for button in params[1]:
            try:
                options.append((button["title"], button["action"], None, button.get("icon")))
            except (TypeError, KeyError):
                logging.warning(f"SHOW_NAVIGATION_GRID: bad button {button}")
        self.show_options(str(params[0]), options)

    # Navigation and screens

    cuia_arrow_next = cuia_arrow_right
    cuia_arrow_prev = cuia_arrow_left
    cuia_layer_options = cuia_chain_options

    def cuia_preset(self, params=None):
        """The current processor's presets (zynthian_gui: an alias of BANK_PRESET)"""
        if self.current_processor is None:
            chain = self.chain_manager.get_active_chain()
            if chain is not None and chain.current_processor is not None:
                self.set_current_processor(chain.current_processor)
        self.cuia_bank_preset(params)

    def cuia_preset_fav(self, params=None):
        """The current processor's favourite presets (zynthian_gui.show_favorites: its bank /
        preset list, then the favourites, also when there are none yet)"""
        proc = self.current_processor
        if proc is None:
            chain = self.chain_manager.get_active_chain()
            proc = chain.current_processor if chain is not None else None
            if proc is None:
                return
            self.set_current_processor(proc)
        self.cuia_bank_preset()
        if self.current_screen in ("bank", "preset"):
            proc = self.current_processor
            proc.set_show_fav_presets(True)
            if self.current_screen == "preset":
                self.list_screens["preset"].fill()
            else:
                self.show_screen("preset")

    def cuia_mixer(self, params=None):
        """MIXER chain,param,value: set a mixer controller (zynthian_gui.cuia_mixer). chain: the
        position in the mixer (0-based), -1 the main chain, None the active chain; param: level,
        balance, mute, solo, mono, ..."""
        try:
            index = params[0]
            if index is None or index == "" or str(index).lower() == "none":
                chain = self.chain_manager.active_chain
            elif int(index) == -1:
                chain = self.chain_manager.chains[0]
            else:
                chain = self.chain_manager.chains[list(self.chain_manager.chains)[int(index)]]
            value = params[2]
            if isinstance(value, str):
                value = float(value)
            chain.zynmixer_proc.controllers_dict[str(params[1])].set_value(value)
        except Exception as e:
            logging.warning(f"MIXER: can't set {params} => {e}")

    def cuia_copy(self, params=None):
        """Screens with something to copy handle it (pattern editor); nothing elsewhere"""

    def cuia_paste(self, params=None):
        """Screens with something to paste handle it (pattern editor); nothing elsewhere"""

    def cuia_help(self, params=None):
        """Show the help page of the screen shown (params[0]: a page, or "index:")"""
        self.show_help(str(params[0]) if params else None)


class UserActivityFilter(QObject):
    """On the window: touches, clicks, wheel and keys count as user activity (power save); while
    the screen is blank, a touch only wakes it"""

    POINTER = (QEvent.MouseButtonPress, QEvent.TouchBegin, QEvent.Wheel)

    def __init__(self, ui, parent=None):
        super().__init__(parent)
        self.ui = ui

    def eventFilter(self, obj, event):
        kind = event.type()
        if kind in self.POINTER or kind == QEvent.KeyPress:
            if isinstance(obj, QWindow):
                return self.ui.user_activity(kind in self.POINTER)
        return False
