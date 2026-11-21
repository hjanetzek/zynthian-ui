"""The Qt UI's file selector for path controllers (zynqt.screens.file_selector, as
zynthian_gui_file_selector) and the engines' GUI signals:

- SS_GUI_SHOW_FILE_SELECTOR (zynthian_controller.nudge of an is_path controller) reaches the GUI
  thread and opens the file selector with the controller's file types, directories, current file
  and preload flag;
- choosing a file closes it and calls cb_func(path) once; directories open, BACK goes up;
- preload: moving the selection applies the file after 200 ms, leaving without a choice restores
  the value it had; without preload nothing is applied before the choice;
- SS_GUI_CONTROL_MODE (SooperLooper's loop selection) ends chain control's select mode."""

import threading
from types import SimpleNamespace

import pytest

QtCore = pytest.importorskip("PySide6.QtCore")
ui_mod = pytest.importorskip("zynqt.ui")

from tests.unit.test_qt_gui_thread import app, wait_for  # noqa: E402,F401
from zyngine.zynthian_signal_manager import zynsigman  # noqa: E402
from zynqt import bridge as bridge_mod  # noqa: E402
from zynqt.screens import file_selector as fs_mod  # noqa: E402

ZynUI = ui_mod.ZynUI


@pytest.fixture
def files(tmp_path, monkeypatch):
    """User Samples: a.wav, c.txt (not listed), sub/b.wav, sub/d.wav"""
    root = tmp_path / "Samples"
    (root / "sub").mkdir(parents=True)
    for p in ("a.wav", "c.txt", "sub/b.wav", "sub/d.wav"):
        (root / p).write_bytes(b"RIFF")
    monkeypatch.setattr(fs_mod, "root_dirs", lambda dirnames: [(f"User {d}", str(root)) for d in sorted(dirnames)])
    monkeypatch.setattr(fs_mod, "COLLECTIONS_DIR", str(tmp_path / "no-collections"))
    monkeypatch.setattr(fs_mod.zynthian_engine, "ex_data_dir", str(tmp_path / "no-usb"), raising=False)
    return root


class Value:
    """A path controller's set_value"""

    def __init__(self, value=""):
        self.value = value
        self.calls = []

    def set_value(self, path):
        self.value = path
        self.calls.append(path)


def selector(app):
    closed = []
    ui = SimpleNamespace(state_manager=None, chain_manager=None, close_screen=lambda: closed.append(True))
    screen = fs_mod.FileSelector(ui)
    return screen, closed


def titles(screen):
    return [e["title"] for e in screen.entries]


def index_of(screen, path):
    return [e["data"] for e in screen.entries].index(str(path))


def test_opens_in_the_current_files_directory(app, files):
    screen, _ = selector(app)
    v = Value(str(files / "sub" / "d.wav"))
    screen.config(v.set_value, fexts=["wav"], dirnames=["Samples"], path=v.value)
    screen.build()
    assert titles(screen) == ["b", "d"]
    assert screen.entries[screen.index]["data"] == v.value
    assert screen.title == "File Selector > User Samples/sub"


def test_root_list_and_directories(app, files):
    screen, _ = selector(app)
    v = Value()
    screen.config(v.set_value, fexts=["wav"], dirnames=["Samples"])
    screen.build()
    # The root directory as a heading, its sub-directory and its files of the types asked for
    assert titles(screen) == ["SD> User Samples", "> sub", "a"]
    assert screen.title == "File Selector"
    screen.activate(index_of(screen, files / "sub"))
    assert titles(screen) == ["b", "d"]
    # BACK: up to the root list, then not handled (ZynUI closes the screen)
    assert screen.back() is True
    assert "> sub" in titles(screen)
    assert screen.entries[screen.index]["data"] == str(files / "sub")
    assert screen.back() is False
    assert v.calls == []


def test_choosing_a_file_closes_and_calls_back_once(app, files):
    screen, closed = selector(app)
    v = Value(str(files / "a.wav"))
    screen.config(v.set_value, fexts=["wav"], dirnames=["Samples"], path=v.value)
    screen.build()
    screen.activate(index_of(screen, files / "sub"))
    screen.activate(index_of(screen, files / "sub" / "b.wav"))
    assert closed == [True]
    assert v.calls == [str(files / "sub" / "b.wav")]
    screen.hide()   # ZynUI hides it when the previous screen comes back: no restore
    assert v.calls == [str(files / "sub" / "b.wav")]


def test_preload_previews_and_restores_on_leaving(app, files):
    screen, closed = selector(app)
    a = str(files / "a.wav")
    v = Value(a)
    screen.config(v.set_value, fexts=["wav"], dirnames=["Samples"], path=a, preload=True)
    screen.build()
    screen.activate(index_of(screen, files / "sub"))
    screen.setIndex(index_of(screen, files / "sub" / "d.wav"))
    assert wait_for(app, lambda: v.calls == [str(files / "sub" / "d.wav")], timeout=2.0)
    assert closed == []
    screen.hide()   # BACK out of it (or another screen): the file it had
    assert v.calls[-1] == a and v.value == a


def test_preload_then_choice_keeps_the_choice(app, files):
    screen, closed = selector(app)
    a = str(files / "a.wav")
    v = Value(a)
    screen.config(v.set_value, fexts=["wav"], dirnames=["Samples"], path=a, preload=True)
    screen.build()
    screen.activate(index_of(screen, files / "sub"))
    b = str(files / "sub" / "b.wav")
    screen.setIndex(index_of(screen, b))
    assert wait_for(app, lambda: v.value == b, timeout=2.0)
    screen.activate(index_of(screen, b))
    screen.hide()
    assert v.value == b and closed == [True]
    assert v.calls.count(a) == 0


def test_without_preload_nothing_before_the_choice(app, files):
    screen, _ = selector(app)
    a = str(files / "a.wav")
    v = Value(a)
    screen.config(v.set_value, fexts=["wav"], dirnames=["Samples"], path=a, preload=False)
    screen.build()
    screen.activate(index_of(screen, files / "sub"))
    screen.setIndex(1)
    wait_for(app, lambda: False, timeout=0.4)
    screen.hide()
    assert v.calls == []


def test_no_files(app, files):
    screen, closed = selector(app)
    v = Value()
    screen.config(v.set_value, fexts=["nam"], dirnames=["Neural Models"])
    screen.build()
    assert titles(screen) == ["No nam files"]
    screen.activate(0)
    assert closed == [True] and v.calls == []


# The signal: zynsigman (any thread) -> SignalBridge -> ZynUI.show_file_selector in the GUI thread

def test_signal_opens_the_file_selector_with_the_controllers_args(app):
    bridge = bridge_mod.SignalBridge()
    got = []
    bridge.showFileSelector.connect(lambda kw: got.append((kw, threading.get_ident())))
    v = Value("/x/a.wav")
    try:
        zynsigman.send_queued(zynsigman.S_GUI, zynsigman.SS_GUI_SHOW_FILE_SELECTOR, cb_func=v.set_value,
                              fexts=["wav", "flac"], dirnames=["Samples"], path=v.value, preload=True)
        assert wait_for(app, lambda: got)
    finally:
        bridge.stop()
    kw, ident = got[0]
    assert ident == threading.get_ident()   # the GUI thread
    assert kw == {"cb_func": v.set_value, "fexts": ["wav", "flac"], "dirnames": ["Samples"], "path": "/x/a.wav",
                  "preload": True}

    # ZynUI.show_file_selector: config, then the screen
    configured, shown = [], []
    screen = SimpleNamespace(cb_func=None, config=lambda *a, **k: configured.append((a, k)))
    ui = SimpleNamespace(_gui=SimpleNamespace(in_gui_thread=lambda: True), current_screen="chain_control",
                         list_screens={"file_selector": screen}, show_screen=shown.append,
                         _close_overlays=lambda: None)
    ZynUI.show_file_selector.__get__(ui)(**kw)
    assert configured == [((v.set_value,), {"fexts": ["wav", "flac"], "dirnames": ["Samples"], "path": "/x/a.wav",
                                            "preload": True})]
    assert shown == ["file_selector"]
    # Asked again while it is shown (the knob turned on): the preview's start value stays
    ui.current_screen = "file_selector"
    screen.cb_func = v.set_value
    ZynUI.show_file_selector.__get__(ui)(**kw)
    assert len(configured) == 1 and shown == ["file_selector"]


def test_path_controller_nudge_reaches_the_bridge(app):
    import sys
    zynthian_controller = sys.modules["zyngine.zynthian_controller"].zynthian_controller
    bridge = bridge_mod.SignalBridge()
    got = []
    bridge.showFileSelector.connect(got.append)
    try:
        z = zynthian_controller(None, "sample", {"is_path": True, "path_file_types": ["wav"], "path_preload": True})
        z.nudge(1)
        assert wait_for(app, lambda: got)
    finally:
        bridge.stop()
    assert got[0]["fexts"] == ["wav"] and got[0]["preload"] is True and got[0]["cb_func"] == z.set_value


# SS_GUI_CONTROL_MODE

def test_control_mode_signal_leaves_select_mode(app):
    bridge = bridge_mod.SignalBridge()
    modes = []
    cc = SimpleNamespace(set_mode=modes.append)
    ui = SimpleNamespace(current_screen="chain_control", chain_control_screen=cc)
    control_mode = ZynUI._control_mode.__get__(ui)
    bridge.controlMode.connect(control_mode)
    try:
        zynsigman.send_queued(zynsigman.S_GUI, zynsigman.SS_GUI_CONTROL_MODE, mode="control")
        assert wait_for(app, lambda: modes)
    finally:
        bridge.stop()
    assert modes == ["control"]
    ui.current_screen = "mixer"     # not shown: nothing
    control_mode("control")
    assert modes == ["control"]


def test_chain_control_set_mode_from_select(app):
    from zynqt.screens.control import ChainControl
    emitted, zynpots = [], []
    cc = SimpleNamespace(_mode="select", modeChanged=SimpleNamespace(emit=lambda: emitted.append(True)),
                         exit_midi_learn=lambda: None, ui=SimpleNamespace(setup_zynpots=zynpots.append))
    ChainControl.set_mode(cc, "control")
    assert cc._mode == "control" and emitted == [True] and zynpots == [cc]

