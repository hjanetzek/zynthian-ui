"""Chain control's shared selection (zyngui.zynthian_control_grid_data.shared_selection, docs/
qt-control-grid.md): the Qt screen (zynqt.screens.control.ChainControl) reports its page, selected
cell and window with a signal for every change, whatever the origin, and applies a driver's
requests in the GUI thread. The grid's page list is the shared one."""

import threading
import time
from types import SimpleNamespace

import pytest

QtCore = pytest.importorskip("PySide6.QtCore")
pytest.importorskip("zynqt.ui")

from zyngine.zynthian_controller import zynthian_controller as Controller  # noqa: E402
from zyngine.zynthian_signal_manager import zynsigman  # noqa: E402
from zyngui import zynthian_control_grid_data as gd  # noqa: E402
from zynqt.gui_thread import GuiCaller  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


def ctrl(symbol):
    c = Controller(None, symbol, {"value_min": 0, "value_max": 127, "value": 0})
    c.is_dirty = False
    return c


class Proc:
    eng_code = "XX"
    type = "MIDI Synth"
    id = 1

    def __init__(self, name, screens, chain):
        self.engine = SimpleNamespace(name=name, custom_gui_fpath=None, refresh_custom_gui=lambda: None)
        self.screens = dict(screens)
        self.screen = 0
        self.chain = chain

    def get_ctrl_screens(self):
        return self.screens

    def get_ctrl_screen(self, title):
        return self.screens[title]

    def get_current_screen_index(self):
        return self.screen

    def set_current_screen_index(self, i):
        self.screen = i

    def get_name(self):
        return self.engine.name


class Chain:
    chain_id = 3
    title = ""
    midi_chan = 0
    audio_thru = False
    zynmixer_proc = None

    def __init__(self):
        from zyngine.zynthian_zctrl_pages import ZctrlPages
        self.procs = [Proc("Helm", [(f"S{i}", [ctrl(f"s{i}{j}") for j in range(4)]) for i in range(30)], self),
                      Proc("Reverb", [("Room", [None, ctrl("size")])], self)]
        helm = self.procs[0]
        helm.controllers_dict = {z.symbol: z for zs in helm.screens.values() for z in zs}
        for z in helm.controllers_dict.values():
            z.processor = helm
        self.procs[1].id = 2
        self.procs[1].controllers_dict = {}
        self.current_processor = self.procs[0]
        # The chain controllers: one page of 4 (CHAIN, page 0)
        self.zctrl_pages = ZctrlPages(self)
        self.zctrl_pages.from_dense([(1, f"s2{j}") for j in range(4)])

    def get_processors(self):
        return self.procs

    def set_current_processor(self, p):
        self.current_processor = p

    def get_title(self):
        return "Synth"

    def is_midi(self):
        return True

    def is_audio(self):
        return False


class Bridge(QtCore.QObject):
    processorControllersChanged = QtCore.Signal()
    chainsChanged = QtCore.Signal()
    activeChainChanged = QtCore.Signal()
    midiCc = QtCore.Signal(int, int, int, int)
    midiNoteOn = QtCore.Signal(int, int, int, int)


class UI(QtCore.QObject):
    def __init__(self, chain):
        super().__init__()
        self._gui = GuiCaller(self)
        self.bridge = Bridge(self)
        self.chain_manager = SimpleNamespace(get_active_chain=lambda: chain)
        self.current_processor = None
        self.state_manager = SimpleNamespace(get_midi_learn_zctrl=lambda: None)

    def set_current_processor(self, p):
        self.current_processor = p
        if p is not None:
            p.chain.set_current_processor(p)

    def setup_zynpots(self, screen=None):
        pass

    def zynpot_push_rotate(self, i):
        return False


@pytest.fixture
def screen(app, monkeypatch):
    from zynqt.screens import control
    monkeypatch.setenv(control.LAYOUT_VAR, "grid8x6")
    chain = Chain()
    ui = UI(chain)
    cc = control.ChainControl(ui)
    got = []
    callbacks = {}
    for name in ("PAGE", "CELL", "WINDOW"):
        callbacks[name] = lambda name=name, **kw: got.append((name, kw))
        zynsigman.register(zynsigman.S_GUI, getattr(zynsigman, f"SS_GUI_CONTROL_GRID_{name}"), callbacks[name])
    yield cc, chain, got
    for name, cb in callbacks.items():
        zynsigman.unregister(zynsigman.S_GUI, getattr(zynsigman, f"SS_GUI_CONTROL_GRID_{name}"), cb)
    gd.shared_selection.clear_owner(cc)
    cc._timer.stop()


def wait_for(app, cond, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        app.processEvents(QtCore.QEventLoop.AllEvents, 20)
        if cond():
            return True
        time.sleep(0.005)
    return cond()


def on_processor_page(cc):
    """Built (it opens on the chain controllers' first page), then the processor's first page"""
    cc.build()
    cc.setPage(cc._page_rows[1])


def test_build_opens_on_the_chain_controllers(screen):
    cc, chain, got = screen
    assert not gd.shared_selection.owner_shown()
    cc.build()
    assert cc.shown and gd.shared_selection.owner_shown()
    assert cc.page_index == 0 and chain.zctrl_pages.shown == 0
    pages, selected = gd.chain_pages(chain, chain.procs, chain.current_processor)
    assert selected == 0 and pages[0].kind == "chain"
    cc.setPage(cc._page_rows[1])
    cc.build()                                  # the same chain again: where it was
    assert cc.page_index == 1


def test_build_reports_and_pages_are_the_shared_ones(screen):
    cc, chain, got = screen
    on_processor_page(cc)
    pages, selected = gd.chain_pages(chain, chain.procs, chain.current_processor)
    assert [p.title for p in cc.grid.grid.pages] == [p.title for p in pages]
    assert cc.page_index == selected == 1 and cc.cell == 0
    assert gd.shared_selection.get(3) == gd.Selection(3, 1, 0, 0, 6, "grid8x6")
    assert ("PAGE", {"chain": 3, "page": 1, "slot": 0}) in got


def test_touch_and_encoders_move_the_cell(screen):
    cc, chain, got = screen
    on_processor_page(cc)
    got.clear()
    cc.controllers[2].nudge(1)                  # the controller column (v5's touch)
    assert cc.cell == 2 and cc.grid.grid.selected_slot == 2
    assert got == [("CELL", {"chain": 3, "page": 1, "slot": 2})]
    cc.zynpot(3, 1)                             # an encoder
    assert cc.cell == 3
    proxies = cc.grid.cells
    assert proxies[7].current and not proxies[6].current
    proxies[0].nudge(1)                         # a drag on another page: the selection stays
    assert (cc.page_index, cc.cell) == (1, 3)
    proxies[1].tapped()                         # a tap: its page and the cell
    assert (cc.page_index, cc.cell) == (0, 1)
    assert gd.shared_selection.get(3).page == 0
    # a page without a controller in slot 0: its first one
    cc.setPage(cc._page_rows[31])
    assert (cc.page_index, cc.cell) == (31, 1)


def test_driver_requests_from_another_thread(app, screen):
    cc, chain, got = screen
    on_processor_page(cc)
    got.clear()
    t = threading.Thread(target=lambda: gd.shared_selection.request_cell(3, 20, 2))
    t.start()
    t.join()
    assert cc.page_index == 1                   # not yet: queued to the GUI thread
    assert wait_for(app, lambda: cc.page_index == 20)
    assert cc.cell == 2 and chain.procs[0].screen == 19
    assert cc.grid.grid.first_row == 5          # the screen's window follows (by rows)
    assert ("PAGE", {"chain": 3, "page": 20, "slot": 0}) in got
    assert got[-1][0] == "CELL" or ("CELL", {"chain": 3, "page": 20, "slot": 2}) in got
    assert ("WINDOW", {"chain": 3, "first_row": 5, "rows": 6, "layout": "grid8x6"}) in got
    gd.shared_selection.request_page(4, 2)      # another chain: dropped
    gd.shared_selection.request_window(3, 0)
    app.processEvents()
    assert cc.page_index == 20 and cc.grid.grid.first_row == 0
    assert gd.shared_selection.get(3).first_row == 0


def test_request_while_not_shown_builds_the_chain(app, screen):
    cc, chain, got = screen
    assert not cc._shown
    gd.shared_selection.request_page(3, 2)
    assert cc.page_index == 2 and cc.cell == 0 and chain.current_processor is chain.procs[0]


def test_open_request_on_a_processor_without_pages(app, screen):
    """A driver's press on an empty page (a processor without pages, e.g. a soundfont player
    without soundfont): selects it, a second one opens its banks / presets as a header tap"""
    cc, chain, got = screen
    empty = Proc("Player", [], chain)
    chain.procs.append(empty)
    opened = []
    cc.ui.cuia_bank_preset = lambda params=None: opened.append(cc.ui.current_processor)
    cc.build()
    pages, _ = gd.chain_pages(chain, chain.procs, chain.current_processor)
    page = next(i for i, p in enumerate(pages) if p.empty)
    gd.shared_selection.request_open(3, page)
    assert cc.page_index == page and cc.ui.current_processor is empty and not opened
    assert gd.shared_selection.get(3).page == page
    gd.shared_selection.request_open(3, page)
    assert opened == [empty] and cc.page_index == page


def test_a_failing_widget_keeps_the_selection(app, screen, monkeypatch):
    """An exception in a page's widget (e.g. the audio player without a file) doesn't stop the
    selection: the page is selected, shown and reported"""
    cc, chain, got = screen
    cc.build()

    def fail(proc, zctrls=()):
        raise KeyError("zoom")
    monkeypatch.setattr(cc, "_set_widget", fail)
    gd.shared_selection.request_page(3, 5)
    assert cc.page_index == 5 and cc.grid.grid.selected == 5
    assert gd.shared_selection.get(3).page == 5 and cc.widgetType == ""


def test_theme_colors(screen):
    cc, chain, got = screen
    cc.setThemeGridColors(["#102030", "#405060"])
    try:
        assert gd.section_color(1) == (0x40, 0x50, 0x60)
    finally:
        gd.set_section_colors(None)


@pytest.mark.parametrize("layout", ["grid4x6", "grid8x6"])
def test_driver_selections_are_always_on_screen(app, layout, monkeypatch):
    """The screen is the driver's name display: whatever a driver selects, the selected page and
    cell are in the grid's window (it scrolls by rows, not the driver's windows)"""
    from zynqt.screens import control
    monkeypatch.setenv(control.LAYOUT_VAR, layout)
    chain = Chain()
    cc = control.ChainControl(UI(chain))
    try:
        cc.build()
        g = cc.grid.grid
        for page, slot in ((25, 1), (0, 0), (31, 1), (12, 3), (2, 2), (30, 0)):
            gd.shared_selection.request_cell(3, page, slot)
            assert (cc.page_index, cc.cell) == (page, slot)
            assert g.selected_row >= 0 and g.selected_cell >= 0
            assert cc.grid.cells[g.selected_cell].current
    finally:
        gd.shared_selection.clear_owner(cc)
        cc._timer.stop()


def test_show_request_brings_chain_control_to_the_front(app, screen):
    """A driver switched to the host's pages (the JAM's HostPageShow) or navigates them:
    chain control of the active chain comes to the front (in the GUI thread), where the driver's
    page request right after puts it; not over a menu, a dialog or the keyboard"""
    cc, chain, got = screen
    shown = []

    def show_screen(name):
        shown.append(name)
        cc.build()
    cc.ui.show_screen = show_screen
    cc.ui.current_screen = "mixer"
    gd.shared_selection.request_show(4)             # another chain: dropped
    app.processEvents()
    assert shown == []
    for blocker in (dict(current_screen="option"), dict(_confirm_text="Delete?"), dict(_keyboard_action=print),
                    dict(_busy=True), dict(_moving_chain=True)):
        for k, v in blocker.items():
            setattr(cc.ui, k, v)
        assert not cc._apply_show_request(3)
        for k in blocker:
            setattr(cc.ui, k, {"current_screen": "mixer", "_confirm_text": "", "_busy": False,
                               "_moving_chain": False}.get(k))
    t = threading.Thread(target=lambda: (gd.shared_selection.request_show(3), gd.shared_selection.request_page(3, 7)))
    t.start()
    t.join()
    assert shown == []                              # queued to the GUI thread
    assert wait_for(app, lambda: shown == ["chain_control"] and cc.page_index == 7)
    gd.shared_selection.request_show(3)             # shown already: nothing
    app.processEvents()
    assert shown == ["chain_control"] and cc.page_index == 7
