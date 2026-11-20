"""The Qt UI's websocket API (zyngui.zynthian_websocket shared with the Tk UI; zynqt.ws_state,
zynqt.ws_keys, ZynUI's toolkit interface):

- "screen_state" reports the Qt screens with the Tk UI's keys, items and titles; changes send only
  what differs, as Tk's partial updates; signals are connected only while someone is subscribed;
- the feedback's UI calls run in the GUI thread, also when they come from the server's threads;
- CUIAs from a client go through the CUIA queue and the CUIA thread to the GUI thread (ZynUI's
  normal path), keys become QKeyEvents with the native keycodes of the key bindings;
- "wsled_state" from the touch keypad's LEDs.
"""

import base64
import json
import os
import socket
import struct
import threading
from queue import SimpleQueue
from types import SimpleNamespace

import pytest

QtCore = pytest.importorskip("PySide6.QtCore")
ui_mod = pytest.importorskip("zynqt.ui")

from tests.bootstrap import STUBBED_MODULES  # noqa: E402
from tests.unit.test_qt_gui_thread import app, in_thread, wait_for  # noqa: E402,F401
from zyngine.zynthian_signal_manager import zynsigman  # noqa: E402
from zyngui.zynthian_websocket import zynthian_websocket_feedback  # noqa: E402
from zynqt import ws_keys, ws_state  # noqa: E402
from zynqt.gui_thread import GuiCaller  # noqa: E402
from zynqt.keypad_leds import KeypadLeds  # noqa: E402
from zynqt.screen_names import tk_name  # noqa: E402
from zynqt.screens.base import EntryModel, SelectorScreen, entry, placeholder, separator  # noqa: E402

ZynUI = ui_mod.ZynUI
Signal = QtCore.Signal


class FakeServer:
    def __init__(self):
        self.sent = []

    def send_message(self, client, payload):
        self.sent.append((client["id"], json.loads(payload)))


class ListScreen(SelectorScreen):
    def fill(self):
        pass


def list_screen(ui, name, entries, kind="list", columns=4, title=""):
    cls = type(f"Screen_{name}", (ListScreen,), {"name": name, "kind": kind, "columns": columns})
    s = cls(ui)
    s.set_title(title)
    s.set_entries(entries)
    return s


class FakeChainControl(QtCore.QObject):
    processorsChanged = Signal()
    pageChanged = Signal()
    modeChanged = Signal()
    selectPathChanged = Signal()

    def __init__(self):
        super().__init__()
        self.pages = EntryModel(self)
        self.page = 1
        self.selectMode = False
        self.isChain = True
        self.chainNodes = [{"title": "Chain Options"}, {"title": "MIDI Input\nCH#01"}, {"title": "Dexed"}]
        self.chainNode = 2
        self.selectPath = "1#Dexed > Bank/Preset"


class FakeChainManagerScreen(QtCore.QObject):
    graphChanged = Signal()
    selectionChanged = Signal()

    def __init__(self):
        super().__init__()
        self.graph = [{"rows": [[{"title": "1#Dexed"}]]}, {"rows": [[{"title": "Main"}]]}]
        self.selection = [1, 0, 0]


class FakePatternEditor(QtCore.QObject):
    patternChanged = Signal()
    modeChanged = Signal()
    ccChanged = Signal()

    def __init__(self):
        super().__init__()
        self.modeTitle = ""
        self.tkTitle = "B1 Dexed: Notes"
        self.cc_mode = False


class FakeUI(QtCore.QObject, zynthian_websocket_feedback):
    """ZynUI's screen state and websocket parts on a light QObject (ZynUI starts zynthian)"""
    currentScreenChanged = Signal()
    confirmChanged = Signal()
    keyboardChanged = Signal()
    helpChanged = Signal()
    busyChanged = Signal()
    statusChanged = Signal()

    websocket_run_idle = ZynUI.websocket_run_idle
    websocket_run_later = ZynUI.websocket_run_later
    screen_state_current = ZynUI.screen_state_current
    get_screen_title = ZynUI.get_screen_title
    screen_state_watch = ZynUI.screen_state_watch

    def __init__(self):
        super().__init__()
        self._gui = GuiCaller(self)
        self.websocket_setup()
        self.websocket_server = FakeServer()
        self.exit_flag = False
        self.wsleds = None
        self.state_manager = SimpleNamespace()
        self.chain_manager = SimpleNamespace(chains={}, active_chain=None)
        self.cuia_queue = SimpleQueue()
        self.busy = False
        self.confirmText = ""
        self.keyboardShown = False
        self.helpShown = False
        self.current_screen = "admin"
        self.list_screens = {}
        self.chain_control_screen = FakeChainControl()
        self.chain_manager_screen = FakeChainManagerScreen()
        self.pattern_editor = FakePatternEditor()
        self.snapshot_title = "001-Parity Test"
        self._ws_watch = ws_state.ScreenStateWatch(self, self.cb_screen_state_full)

    def get_current_screen(self):
        return tk_name(self.current_screen, self.pattern_editor.cc_mode)

    def _snapshot_title(self):
        return self.snapshot_title

    def show(self, name):
        self.current_screen = name
        self.currentScreenChanged.emit()


def drain(queue):
    items = []
    while not queue.empty():
        items.append(queue.get())
    return items


def screen_states(ui):
    return [json.loads(payload)["screen_state"] for stream, payload in drain(ui.websocket_queue)
            if stream == "screen_state"]


def settle(app, ui, timeout=1.0):
    """Process events until the scheduled screen state update ran"""
    wait_for(app, lambda: not ui.screen_state_pending and not ui.websocket_queue.empty(), timeout)
    wait_for(app, lambda: False, 0.05)


@pytest.fixture
def ui(app):
    u = FakeUI()
    u.list_screens["admin"] = list_screen(u, "admin", [separator("MIDI"), entry("Program Change => ZS3"),
                                                       entry("Test MIDI")], title="Admin")
    u.list_screens["main_menu"] = list_screen(u, "main_menu", [entry("Add\nChain"), entry("Admin"), placeholder()],
                                              kind="grid", columns=3, title="Main Menu")
    yield u
    u.websocket_subscriptions.clear()
    u.screen_state_sync()
    u.chain_state_sync()


@pytest.fixture
def subscribed(app, ui):
    client = {"id": 1}
    ui.websocket_clients[1] = client
    ui.websocket_subscriptions[1] = set()
    ui.websocket_command(client, "/subscribe screen_state")
    settle(app, ui)
    return ui


# --- the Qt screens as Tk's views ---------------------------------------------------------------------------

def test_selector_items_mark_sections_and_join_grid_lines():
    entries = [separator("MIDI"), entry("Test MIDI"), separator("> AUDIO"), entry("Add\nChain"), placeholder()]
    assert ws_state.selector_items(entries) == ["> MIDI", "Test MIDI", "> AUDIO", "Add\nChain", ""]
    assert ws_state.selector_items(entries, grid=True) == ["MIDI", "Test MIDI", "> AUDIO", "Add Chain", ""]


def test_list_grid_and_engine_states(ui):
    assert ws_state.current_state(ui)[0] == "admin"
    view = ws_state.current_state(ui)[1]
    assert view.state_key == "zyngui_selector"
    assert view.get_state() == {"items": ["> MIDI", "Program Change => ZS3", "Test MIDI"], "selected": 1}
    assert view.get_state("select") == {"selected": 1}
    assert view.title() == "Admin"
    ui.current_screen = "main_menu"
    name, view = ws_state.current_state(ui)
    assert (name, view.state_key) == ("main_menu", "zyngui_selector_grid")
    assert view.get_state() == {"items": ["Add Chain", "Admin", ""], "selected": 0, "columns": 3}
    engine = list_screen(ui, "engine", [entry("Dexed"), entry("Helm")], title="MIDI Instrument/Synth")
    engine.set_categories(["Synth", "Sampler"], 1)
    ui.list_screens["engine"] = engine
    ui.current_screen = "engine"
    name, view = ws_state.current_state(ui)
    assert view.state_key == "zyngui_engine"
    assert view.get_state() == {"items": ["Dexed", "Helm"], "selected": 0,
                                "categories": {"items": ["Synth", "Sampler"], "selected": 1}}


def test_chain_control_states(ui):
    cc = ui.chain_control_screen
    cc.pages.set_entries([separator("Dexed"), entry("General 1"), entry("General 2")])
    ui.current_screen = "chain_control"
    name, view = ws_state.current_state(ui)
    assert name == "chain_control" and view.state_key == "zyngui_chain_control"
    assert view.get_state() == {"zyngui_selector": {"items": ["> Dexed", "General 1", "General 2"], "selected": 1}}
    assert view.title() == "1#Dexed > Bank/Preset"
    # Select mode: the chain blocks, as Tk's chain_control shows them
    cc.selectMode = True
    assert view.get_state()["chain_blocks"] == {"items": ["Chain Options", "MIDI Input CH#01", "Dexed"], "selected": 2}
    # Special processors: Tk's plain control screen
    ui.current_screen = "tempo"
    name, view = ws_state.current_state(ui)
    assert name == "tempo" and view.state_key == "zyngui_selector"
    assert view.get_state()["items"] == ["> Dexed", "General 1", "General 2"]
    cc.pages.set_entries([])
    assert view.get_state() == {"items": ["NO PROCESSORS!"], "selected": 0}


def test_screens_without_view_state_report_their_titles(ui):
    for screen, title in (("mixer", "001-Parity Test"), ("launcher", "001-Parity Test"),
                          ("pattern_editor", "B1 Dexed: Notes"), ("chain_manager", "Chain: Main"),
                          ("control_xy", "")):
        ui.current_screen = screen
        name, view = ws_state.current_state(ui)
        assert (name, view.state_key, view.title()) == (screen, None, title)
    ui.pattern_editor.modeTitle = "Select Block"
    ui.pattern_editor.cc_mode = True
    ui.current_screen = "pattern_editor"
    name, view = ws_state.current_state(ui)
    assert (name, view.title()) == ("pated_cc", "Select Block")
    ui.current_screen = "midi_in"
    ui.list_screens["midi_in"] = list_screen(ui, "midi_in", [entry("USB")], title="1#Dexed/MIDI Input")
    assert ws_state.current_state(ui)[0] == "midi_config"


def test_overlays_come_first(ui):
    ui.confirmText = "Remove all chains?"
    name, view = ws_state.current_state(ui)
    assert (name, view.state_key, view.get_state(), view.title()) == \
        ("confirm", "zyngui_confirm", {"text": "Remove all chains?"}, "")
    ui.keyboardShown = True
    ui.confirmText = ""
    assert ws_state.current_state(ui)[0] == "keyboard"
    ui.busy = True
    assert ws_state.current_state(ui)[0] == "loading"


# --- "screen_state" feedback --------------------------------------------------------------------------------

def test_subscribing_sends_the_full_state(app, subscribed):
    assert screen_states(subscribed) == [{"screen": "admin", "title": "Admin", "zyngui_selector": {
        "items": ["> MIDI", "Program Change => ZS3", "Test MIDI"], "selected": 1}}]


def test_changes_send_only_what_differs(app, subscribed):
    ui = subscribed
    drain(ui.websocket_queue)
    ui.list_screens["admin"].move(1)
    settle(app, ui)
    assert screen_states(ui) == [{"zyngui_selector": {"selected": 2}}]
    ui.list_screens["admin"].set_title("Admin 2")
    settle(app, ui)
    assert screen_states(ui) == [{"title": "Admin 2"}]
    ui.list_screens["admin"].set_entries([entry("Only")])
    settle(app, ui)
    assert screen_states(ui) == [{"zyngui_selector": {"items": ["Only"], "selected": 0}}]


def test_a_burst_of_changes_is_one_message(app, subscribed):
    ui = subscribed
    drain(ui.websocket_queue)
    screen = ui.list_screens["admin"]
    screen.move(1)
    screen.move(-1)
    screen.set_title("Admin 3")
    settle(app, ui)
    assert screen_states(ui) == [{"title": "Admin 3"}]


def test_screen_change_and_removed_parts_send_the_full_state(app, subscribed):
    ui = subscribed
    drain(ui.websocket_queue)
    ui.show("main_menu")
    settle(app, ui)
    assert screen_states(ui) == [{"screen": "main_menu", "title": "Main Menu", "zyngui_selector_grid": {
        "items": ["Add Chain", "Admin", ""], "selected": 0, "columns": 3}}]
    cc = ui.chain_control_screen
    cc.pages.set_entries([separator("Dexed"), entry("General 1")])
    cc.selectMode = True
    ui.show("chain_control")
    settle(app, ui)
    full = screen_states(ui)[0]
    assert set(full["zyngui_chain_control"]) == {"chain_blocks", "zyngui_selector"}
    cc.selectMode = False
    cc.modeChanged.emit()
    settle(app, ui)
    state = screen_states(ui)
    # chain_blocks gone: the full state again (Tk sends it with the screen)
    assert state == [{"screen": "chain_control", "title": "1#Dexed > Bank/Preset", "zyngui_chain_control": {
        "zyngui_selector": {"items": ["> Dexed", "General 1"], "selected": 1}}}]


def test_hidden_screens_send_nothing(app, subscribed):
    ui = subscribed
    drain(ui.websocket_queue)
    ui.list_screens["main_menu"].move(1)
    wait_for(app, lambda: False, 0.1)
    assert screen_states(ui) == []


def test_signals_are_connected_only_while_subscribed(app, subscribed):
    ui = subscribed
    assert ui._ws_watch._connections
    ui.websocket_command(ui.websocket_clients[1], "/unsubscribe screen_state")
    wait_for(app, lambda: not ui.screen_state_active)
    assert not ui.screen_state_active and ui._ws_watch._connections == []
    drain(ui.websocket_queue)
    ui.list_screens["admin"].move(1)
    wait_for(app, lambda: False, 0.1)
    assert screen_states(ui) == []


def test_ui_calls_from_server_threads_run_in_the_gui_thread(app, ui):
    gui = threading.get_ident()
    seen = []
    in_thread(lambda: ui.websocket_run_idle(lambda x: seen.append(("idle", x, threading.get_ident())), 1))
    in_thread(lambda: ui.websocket_run_later(30, lambda: seen.append(("later", None, threading.get_ident()))))
    assert wait_for(app, lambda: len(seen) == 2)
    assert seen == [("idle", 1, gui), ("later", None, gui)]


def test_subscribing_from_a_server_thread_syncs_in_the_gui_thread(app, ui):
    gui = threading.get_ident()
    threads = []
    orig = ui.screen_state_watch
    ui.screen_state_watch = lambda on: (threads.append(threading.get_ident()), orig(on))
    client = {"id": 3}
    ui.websocket_clients[3] = client
    ui.websocket_subscriptions[3] = set()
    in_thread(lambda: ui.websocket_command(client, "/subscribe screen_state"))
    assert wait_for(app, lambda: ui.screen_state_active)
    assert threads == [gui]


# --- CUIA input ---------------------------------------------------------------------------------------------

class CuiaUI(QtCore.QObject):
    """ZynUI's CUIA thread and its hand-over to the GUI thread"""
    _cuiaRequested = Signal(str, list)
    _cuia_task = ZynUI._cuia_task

    def __init__(self, queue):
        super().__init__()
        self.cuia_queue = queue
        self.exit_flag = False
        self.zynswitch_autolong_disabled = False
        self.zynpot_pr_state = []
        self.state_manager = SimpleNamespace(set_event_flag=lambda: None)
        self.ran = []
        self._cuiaRequested.connect(self._run_cuia)

    def _switch_zynpot(self, i):
        return None

    @QtCore.Slot(str, list)
    def _run_cuia(self, cuia, params):
        self.ran.append((cuia, params, threading.get_ident()))


def ws_client(port):
    """A minimal websocket client (the test VM has no websocket-client): handshake, masked text frames"""
    sock = socket.create_connection(("127.0.0.1", port), timeout=3)
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall((f"GET / HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                  f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        resp += sock.recv(1024)
    assert b" 101 " in resp.split(b"\r\n")[0]

    def send(text):
        data = text.encode()
        mask = os.urandom(4)
        header = bytes([0x81, 0x80 | len(data)]) if len(data) < 126 else bytes([0x81, 0xFE]) + struct.pack("!H", len(data))
        sock.sendall(header + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    return sock, send


@pytest.mark.skipif("websocket_server" in STUBBED_MODULES,
                    reason="needs the websocket-server package (stubbed by tests/bootstrap.py when missing)")
def test_cuias_from_a_client_run_in_the_gui_thread(app, ui):
    gui = threading.get_ident()
    cuia_ui = CuiaUI(ui.cuia_queue)
    task = threading.Thread(target=cuia_ui._cuia_task, name="cuia", daemon=True)
    task.start()
    ui.websocket_port = 0
    ui.websocket_init()
    try:
        sock, send = ws_client(ui.websocket_server.server_address[1])
        send(json.dumps({"cuia": "ARROW_DOWN", "args": []}))
        send(json.dumps({"cuia": "SELECT", "args": [4]}))
        assert wait_for(app, lambda: len(cuia_ui.ran) == 2)
        assert cuia_ui.ran == [("ARROW_DOWN", [], gui), ("SELECT", [4], gui)]
        sock.close()
    finally:
        cuia_ui.exit_flag = True
        ui.cuia_queue.put("__EXIT__")
        ui.websocket_stop()
        task.join(2)


# --- keys ---------------------------------------------------------------------------------------------------

def test_key_codes_map_to_native_keycodes():
    # X11 keycodes (evdev + 8), as the key bindings use them
    assert ws_keys.key_info("ArrowDown")[:2] == (116, QtCore.Qt.Key_Down)
    assert ws_keys.key_info("KeyA")[:3] == (38, QtCore.Qt.Key_A, "a")
    assert ws_keys.key_info("Digit0")[0] == 19
    assert ws_keys.key_info("F1")[0] == 67 and ws_keys.key_info("F12")[0] == 96 and ws_keys.key_info("F13")[0] == 191
    assert ws_keys.key_info("Numpad5")[0] == 84
    assert ws_keys.key_info("Bogus") is None and ws_keys.key_info(None) is None


def test_key_events_carry_the_held_modifiers():
    keys = ws_keys.WebsocketKeys(SimpleNamespace(frontend=None))
    keys.make_event("down", "ShiftLeft")
    ev = keys.make_event("down", "KeyA")
    assert ev.type() == QtCore.QEvent.KeyPress
    assert (ev.nativeScanCode(), ev.nativeModifiers(), ev.text()) == (38, 1, "A")
    assert ev.modifiers() & QtCore.Qt.ShiftModifier
    keys.make_event("up", "ShiftLeft")
    ev = keys.make_event("up", "KeyA")
    assert ev.type() == QtCore.QEvent.KeyRelease and (ev.nativeModifiers(), ev.text()) == (0, "a")
    assert keys.make_event("press", "KeyA") is None


# --- LEDs ---------------------------------------------------------------------------------------------------

def test_keypad_leds_give_the_wsled_state_while_clients_are_connected(app):
    sm = SimpleNamespace(audio_recorder=SimpleNamespace(rec_proc=None), status_audio_player=False)
    ui = SimpleNamespace(state_manager=sm, current_screen="main_menu", screen_history=[], alt_mode=False,
                         _screen_obj=lambda name: None, _overlay_shown=lambda: False, websocket_clients={})
    leds = KeypadLeds(ui)
    leds._timer.stop()
    leds.update()
    assert leds.last_wsled_state == "" and not leds.wsled_state_changed
    ui.websocket_clients[1] = {"id": 1}
    leds.update()
    # As the Tk UI's (zynthian_wsleds_v5touch) on the main menu
    assert leds.last_wsled_state == "G,B,B,B,B,B,B,B,B,B,B,B,B,G,Y,R,Y,Y,Y,B"
    assert leds.wsled_state_changed


def test_malformed_zynpot_and_zynswitch_cuias_are_dropped():
    """They would end the CUIA thread (its int() conversions); the others go into the queue as OSC's"""
    ok = ui_mod.ws_cuia_args_ok
    assert ok("ZYNPOT", [3, -1]) and ok("zynpot", ["3", "1", "P"]) and ok("ZYNSWITCH", [1, "S"])
    assert ok("ZYNSWITCH", [1, "R", "200000"]) and ok("ARROW_DOWN", []) and ok("SELECT", ["x"])
    assert not ok("ZYNPOT", ["x", 1]) and not ok("ZYNPOT", [1, None]) and not ok("ZYNSWITCH", ["a", "S"])
    assert not ok("ZYNSWITCH", [1, "R", "soon"])
    host = SimpleNamespace(cuia_queue=SimpleQueue())
    ZynUI.websocket_cuia(host, "ZYNPOT", ["x", 1], "WS#1")
    ZynUI.websocket_cuia(host, "ZYNPOT", [3, 1], "WS#1")
    ZynUI.websocket_cuia(host, "SELECT", 4, "WS#1")
    assert drain(host.cuia_queue) == [("ZYNPOT", [3, 1], "WS#1"), ("SELECT", [4], "WS#1")]
