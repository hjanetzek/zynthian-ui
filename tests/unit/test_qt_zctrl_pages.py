"""The chain controllers' pages in the Qt UI's chain control (docs/chain-controller-pages.md): the
CHAIN section first in the page list and the grid, a selected page kept on rebuilds, the
controller options' toggle (the next free slot) and slot picker, the page manager (also from the
chain options), a driver's assignment from another thread."""

import threading
from types import SimpleNamespace

import pytest

QtCore = pytest.importorskip("PySide6.QtCore")
pytest.importorskip("zynqt.ui")

from zyngine.zynthian_zctrl_pages import ZctrlPages  # noqa: E402
from zyngine.zynthian_signal_manager import zynsigman  # noqa: E402
from zyngui import zynthian_control_grid_data as gd  # noqa: E402
from tests.unit import test_qt_control_grid_selection as base  # noqa: E402


class Chain(base.Chain):
    def __init__(self):
        super().__init__()
        for pid, proc in enumerate(self.procs, 1):
            proc.id = pid
            proc.controllers_dict = {z.symbol: z for zs in proc.screens.values() for z in zs if z is not None}
            for z in proc.controllers_dict.values():
                z.processor = proc
        self.zctrl_pages = ZctrlPages(self)
        self.midi_slots = self.audio_slots = []
        self.synth_slots = [[p] for p in self.procs]
        for p in self.procs:
            p.type = "MIDI Synth"
            p.is_bypassed = lambda: False

    def get_processors_by_id(self):
        return {p.id: p for p in self.procs}

    # as zynthian_chain's chain controllers
    zctrls = property(lambda self: self.zctrl_pages.flat())

    def toggle_zctrl(self, zctrl):
        self.zctrl_pages.toggle(zctrl)


class UI(base.UI):
    def __init__(self, chain):
        super().__init__(chain)
        self.menus = []
        self.state_manager = SimpleNamespace(get_midi_learn_zctrl=lambda: None, zctrl_x=None, zctrl_y=None)
        self.chain_manager.get_midi_binding_from_zctrl = lambda *a, **kw: None
        self.keyboard = None
        self.confirmed = None

    def show_options(self, title, options, selected=0):
        self.menus.append((title, options, selected))

    def show_keyboard(self, action, text="", title=""):
        self.keyboard = (action, text)

    def confirm(self, text, action):
        self.confirmed = action


@pytest.fixture
def screen(app, monkeypatch):
    from zynqt.screens import control
    monkeypatch.setenv(control.LAYOUT_VAR, "grid8x6")
    chain = Chain()
    ui = UI(chain)
    cc = control.ChainControl(ui)
    yield cc, chain, ui
    gd.shared_selection.clear_owner(cc)
    cc._timer.stop()


@pytest.fixture(scope="module")
def app():
    return QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


def helm(chain, screen, j):
    return chain.procs[0].screens[f"S{screen}"][j]


def choose(ui, text):
    title, options, _ = ui.menus[-1]
    label, action, _, _ = next(o for o in options if text in o[0])
    action()


def test_chain_section_first_and_selection_kept(screen):
    cc, chain, ui = screen
    chain.zctrl_pages.assign(helm(chain, 5, 2), 0, 1)
    chain.zctrl_pages.rename_page(0, "Perform")
    cc.build()
    titles = [e["title"] for e in cc.pages.entries[:3]]
    assert titles == ["CHAIN", "Perform", "Helm"]
    g = cc.grid.grid
    assert g.pages[0].section == "Chain" and g.pages[0].color_index == -1 and g.pages[1].color_index == 0
    assert cc.page_index == 0                   # a chain opens on its chain controllers
    assert cc.controllers[1].zctrl is helm(chain, 5, 2) and cc.controllers[0].zctrl is None
    cc.setPage(cc._page_rows[1])                # Helm S0
    assert chain.zctrl_pages.shown is None
    cc.setPage(cc._page_rows[0])
    assert chain.zctrl_pages.shown == 0
    assert chain.current_processor is chain.procs[0]        # no processor change
    cc.rebuild()
    assert cc.page_index == 0                   # still the chain controller page
    assert cc.chainNodes[2]["title"] == "Chain\nControllers" and cc.chainNode == 2
    assert not any(n["title"] == "Remote\nControls" for n in cc.chainNodes)
    cc.setPage(cc._page_rows[5])
    assert chain.zctrl_pages.shown is None
    cc.rebuild()
    assert cc.page_index == 5
    assert cc.grid.blocks[0]["colorIndex"] == -1 and cc.grid.cells[1].colorIndex == -1


def test_toggle_adds_to_the_next_free_slot(screen):
    cc, chain, ui = screen
    cc.build()
    cc.setPage(cc._page_rows[2])                # Helm S2 (no chain controllers yet)
    for j in range(4):
        cc.controllers[j].options()
        assert ui.menus[-1][1][0][0] == "☐ Chain Controller"
        choose(ui, "Chain Controller")
        assert ui.menus[-1][1][0][0] == "☒ Chain Controller"
    assert [e["title"] for e in cc.pages.entries[:3]] == ["CHAIN", "Controllers 1", "Helm"]
    assert chain.zctrls == tuple(helm(chain, 2, j) for j in range(4))
    assert cc.controllers[0].zctrl is helm(chain, 2, 0)     # still Helm S2
    cc.setPage(cc._page_rows[4])                # Helm S3
    cc.controllers[1].options()
    choose(ui, "☐ Chain Controller")            # all full: a new page
    assert [p.name for p in chain.zctrl_pages.pages] == ["Controllers 1", "Controllers 2"]
    assert chain.zctrls[4] is helm(chain, 3, 1)
    cc.controllers[1].options()
    choose(ui, "☒ Chain Controller")            # off: the emptied default-named last page goes
    assert [p.name for p in chain.zctrl_pages.pages] == ["Controllers 1"]


def test_controller_options_slot_picker(screen):
    cc, chain, ui = screen
    cc.build()
    cc.setPage(cc._page_rows[2])                # Helm S2
    z = cc.controllers[2].zctrl
    assert z is helm(chain, 2, 2)
    cc.controllers[2].options()
    assert [o[0] for o in ui.menus[-1][1][:2]] == ["☐ Chain Controller", "Chain Controller slot..."]
    choose(ui, "Chain Controller slot")
    choose(ui, "New page")
    assert ui.menus[-1][0] == f"Controllers 1: slot for {z.name}"
    assert len(ui.menus[-1][1]) == 4
    choose(ui, "4  –")
    assert chain.zctrl_pages.pages[0].slots[3] == (1, z.symbol)
    assert [e["title"] for e in cc.pages.entries[:2]] == ["CHAIN", "Controllers 1"]
    assert cc.controllers[2].zctrl is z         # the same page selected after the rebuild
    # back in the slot options: move it to slot 2 of the page
    assert ui.menus[-1][0] == f"Chain Controller slot: {z.name}"
    choose(ui, "Controllers 1...")
    choose(ui, "2  –")
    assert chain.zctrl_pages.find(z) == [(0, 1)]
    cc.controllers[2].options()
    assert ui.menus[-1][1][0][0] == "☒ Chain Controller"
    choose(ui, "Chain Controller slot: Controllers 1, 2")
    choose(ui, "Remove from Controllers 1, slot 2")
    assert chain.zctrl_pages.find(z) == [] and chain.zctrl_pages.pages == []


def test_add_this_page_and_the_page_manager(screen):
    cc, chain, ui = screen
    cc.build()
    cc.setPage(cc._page_rows[1])                # Helm S1
    cc.controllers[0].options()
    choose(ui, "Chain Controller slot")
    choose(ui, "Add page 'S1'")
    assert chain.zctrl_pages.pages[0].name == "S1"
    assert chain.zctrl_pages.zctrls(0) == [helm(chain, 1, j) for j in range(4)]
    chain.zctrl_pages.add_page("Two")
    choose(ui, "Manage pages")
    choose(ui, "Two")
    choose(ui, "Move up")
    assert [p.name for p in chain.zctrl_pages.pages] == ["Two", "S1"]
    choose(ui, "Rename")
    ui.keyboard[0]("Lead")
    assert chain.zctrl_pages.pages[0].name == "Lead"
    assert [e["title"] for e in cc.pages.entries[:2]] == ["CHAIN", "Lead"]
    choose(ui, "Delete")
    ui.confirmed()
    assert [p.name for p in chain.zctrl_pages.pages] == ["S1"]


def test_page_manager_from_the_chain_options(screen):
    from zynqt.screens.chain_options import ChainOptions
    cc, chain, ui = screen
    ui.chain_control_screen = cc
    chain.zctrl_pages.add_page("Perform")
    ChainOptions.chain_controller_pages(SimpleNamespace(ui=ui), chain)
    assert ui.menus[-1][0] == "Chain controller pages"
    choose(ui, "Perform")
    choose(ui, "Clear")
    assert ui.menus[-1][0] == "Chain controller page: Perform"


def test_driver_assign_from_another_thread(app, screen):
    cc, chain, ui = screen
    cc.build()
    got = []
    cb = lambda **kw: got.append(kw)  # noqa: E731
    zynsigman.register(zynsigman.S_GUI, zynsigman.SS_GUI_CONTROL_GRID_ZCTRL_PAGES, cb)
    try:
        z = helm(chain, 7, 1)
        t = threading.Thread(target=lambda: gd.shared_selection.request_zctrl_assign(chain, z, 2))
        t.start()
        t.join()
        assert base.wait_for(app, lambda: chain.zctrl_pages.pages and cc.pages.entries[0]["title"] == "CHAIN")
        assert chain.zctrl_pages.find(z) == [(0, 2)]
        assert got == [{"chain": 3}]
        # the JAM's strips 5-8: the next page
        z2 = helm(chain, 7, 2)
        gd.shared_selection.request_zctrl_assign(chain, z2, 6)
        assert base.wait_for(app, lambda: chain.zctrl_pages.find(z2) == [(1, 2)])
        gd.shared_selection.request_zctrl_assign(chain, z, -1)
        assert base.wait_for(app, lambda: chain.zctrl_pages.find(z) == [])
    finally:
        zynsigman.unregister(zynsigman.S_GUI, zynsigman.SS_GUI_CONTROL_GRID_ZCTRL_PAGES, cb)


def test_zctrl_assign_without_zctrl_pages():
    assert gd.zctrl_assign(SimpleNamespace(), None, 0) == -1
