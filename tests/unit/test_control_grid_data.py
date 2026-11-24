"""zyngui.zynthian_control_grid_data: chain control's pages as a grid (layouts, window, selection,
cells, polling)."""

from zyngine.zynthian_controller import zynthian_controller as Controller
from zyngui import zynthian_control_grid_data as g


def ctrl(symbol, **options):
    c = Controller(None, symbol, options or {"value_min": 0, "value_max": 127, "value": 0})
    c.is_dirty = False
    return c


def pages(n, per=4):
    return [g.GridPage(i, f"P{i}", "S", 0, [ctrl(f"p{i}c{j}") for j in range(per)]) for i in range(n)]


def test_kinds():
    assert g.cell_kind(None) == g.KIND_EMPTY
    assert g.cell_kind(ctrl("f", value_min=0.0, value_max=1.0, value=0.5)) == g.KIND_FLOAT
    assert g.cell_kind(ctrl("i", value_min=0, value_max=127, value=3)) == g.KIND_INTEGER
    assert g.cell_kind(ctrl("t", labels=["off", "on"])) == g.KIND_TOGGLE
    assert g.cell_kind(ctrl("l", labels=["a", "b", "c"])) == g.KIND_LIST
    assert g.cell_kind(ctrl("x", labels=["go"])) == g.KIND_TRIGGER


def test_origin_and_list_index():
    assert g.cell_origin(ctrl("pan", value_min=-64, value_max=63, value=0)) > 0.4
    assert g.cell_origin(ctrl("vol", value_min=0, value_max=127, value=0)) == 0
    lst = ctrl("l", labels=["a", "b", "c"], value=1)
    assert g.cell_list_index(lst) == (1, 3)


def test_4x6_window_follows_selection():
    grid = g.ControlGrid("grid4x6")
    grid.set_pages(pages(10), 0)
    assert len(grid.cells) == 24 and grid.total_rows == 10 and grid.first_row == 0
    assert grid.cells[0].zctrl.symbol == "p0c0" and grid.cells[23].zctrl.symbol == "p5c3"
    grid.select(7)
    assert grid.first_row == 2 and grid.selected_row == 5
    grid.move(-1)
    assert grid.first_row == 2 and grid.selected_row == 4
    grid.select(0)
    assert grid.first_row == 0


def test_8x6_two_pages_a_row():
    grid = g.ControlGrid("grid8x6")
    grid.set_pages(pages(15), 3)
    assert len(grid.cells) == 48 and grid.total_rows == 8
    assert grid.selected_row == 1 and grid.selected_half == 1
    assert grid.cells[4].zctrl.symbol == "p1c0"     # row 0, right half: page 1
    grid.select(14)
    assert grid.first_row == 2 and grid.selected_row == 5 and grid.selected_half == 0
    # page 15 does not exist: the last row's right half is empty
    assert all(c.zctrl is None and c.page == -1 for c in grid.cells[44:48])


def test_short_pages_and_few_pages():
    grid = g.ControlGrid("grid4x6")
    grid.set_pages(pages(2, per=2), 1)
    assert grid.cells[1].zctrl is not None and grid.cells[2].zctrl is None
    assert grid.cells[2].page == 0
    assert all(c.page == -1 for c in grid.cells[8:])
    assert grid.scroll(3) is False


def test_layout_switch_keeps_selection():
    grid = g.ControlGrid("grid4x6")
    grid.set_pages(pages(20), 13)
    grid.set_layout("grid8x6")
    assert grid.selected == 13 and grid.selected_row >= 0 and len(grid.cells) == 48


def test_watcher_compares_values_and_leaves_is_dirty():
    grid = g.ControlGrid("grid4x6")
    pp = pages(3)
    grid.set_pages(pp, 0)
    events = []
    grid.add_listener(lambda e, d: events.append((e, d)))
    w = g.ValueWatcher()
    assert grid.poll(w) == [] and events == []      # the first look: all seen
    pp[1].zctrls[2].set_value(64)
    changed = grid.poll(w)
    assert [c.id for c in changed] == [6] and pp[1].zctrls[2].is_dirty   # the flag stays
    assert events[0][0] == "values"
    assert grid.poll(w) == []
    w2 = g.ValueWatcher()
    grid.poll(w2)
    pp[0].zctrls[0].set_value(5)
    assert [c.id for c in grid.poll(w)] == [0] and [c.id for c in grid.poll(w2)] == [0]


def test_events_structure_and_state():
    grid = g.ControlGrid("grid4x6")
    grid.set_pages(pages(10), 0)
    events = []
    grid.add_listener(lambda e, d: events.append(e))
    grid.select(3)
    grid.select(8)
    assert events == ["state", "structure"]


def test_input_and_anchor():
    grid = g.ControlGrid("grid4x6")
    pp = pages(4)
    pp[1].zctrls[1] = ctrl("t", labels=["off", "on"])
    grid.set_pages(pp, 0)
    assert grid.selected_zctrl is pp[0].zctrls[0]
    asked = []
    grid.on_select = asked.append
    grid.select_cell(5)
    assert asked == [1] and grid.selected == 0      # the owner selects
    grid.on_select = None
    grid.select_row(2)
    assert grid.selected == 2 and grid.page_of_zctrl(pp[2].zctrls[3]) == 2
    assert grid.turn(0, 3) is pp[0].zctrls[0] and pp[0].zctrls[0].value > 0
    v = pp[1].zctrls[1].value
    grid.press(5)
    assert pp[1].zctrls[1].value != v
    assert g.cell_items(pp[1].zctrls[1])[1][0] == "on"


def test_press_steps_float_lists_and_wraps():
    grid = g.ControlGrid("grid4x6")
    pp = pages(1)
    z = ctrl("w", labels=["a", "b", "c", "d"], ticks=[0.0, 0.10000000149011612, 0.20000000298023224,
                                                     0.30000001192092896], value=0.3, is_integer=False)
    z.set_value(0.3)
    pp[0].zctrls[0] = z
    grid.set_pages(pp, 0)
    assert z.get_value2label() == "d"
    grid.press(0)
    assert z.get_value2label() == "a"
    grid.press(0)
    assert z.get_value2label() == "b"


# The page list without Qt

class FakeEngine:
    def __init__(self, name):
        self.name = name


class FakeProc:
    def __init__(self, name, screens):
        self.engine = FakeEngine(f"Plugin/{name}")
        self.screens = dict(screens)
        self.screen = 0

    def get_ctrl_screens(self):
        return self.screens

    def get_ctrl_screen(self, title):
        return self.screens[title]

    def get_current_screen_index(self):
        return self.screen


class FakeChain:
    """A chain with its chain controllers' pages (zyngine.zynthian_zctrl_pages) over procs"""

    def __init__(self, procs, chain_id=1):
        from zyngine.zynthian_zctrl_pages import ZctrlPages
        self.procs = procs
        self.chain_id = chain_id
        self.zctrl_pages = ZctrlPages(self)

    def get_processors(self):
        return list(self.procs)


def chain_and_procs(chain_ctrls=6):
    synth = FakeProc("Helm", [(f"S{i}", [ctrl(f"s{i}{j}") for j in range(4)]) for i in range(3)])
    empty = FakeProc("Player", [])
    fx = FakeProc("Reverb", [("Room", [ctrl("size"), None, ctrl("wet")])])
    procs = [synth, empty, fx]
    for i, p in enumerate(procs):
        p.id = i + 1
        p.controllers_dict = {z.symbol: z for zs in p.screens.values() for z in zs if z is not None}
        for z in p.controllers_dict.values():
            z.processor = p
    chain = FakeChain(procs)
    chain.zctrl_pages.from_dense([(1, f"s{i // 4}{i % 4}") for i in range(chain_ctrls)])
    return chain, procs


def test_chain_page_items_as_chain_control():
    chain, procs = chain_and_procs()
    items, selected = g.chain_page_items(chain, procs, None)
    assert [(i.title, i.separator, i.header) for i in items] == [
        ("CHAIN", True, False), ("Controllers 1", False, False), ("Controllers 2", False, False),
        ("Helm", True, False), ("S0", False, False), ("S1", False, False), ("S2", False, False),
        ("Player", False, True), ("Reverb", True, False), ("Room", False, False)]
    assert selected == 1                                # no current processor: the first page
    kind, proc, (page, zctrls) = items[2].data
    assert kind == "chain" and page == 1 and zctrls[:2] == [procs[0].controllers_dict["s10"],
                                                            procs[0].controllers_dict["s11"]]
    assert zctrls[2:] == [None, None]
    procs[0].screen = 2
    assert g.chain_page_items(chain, procs, procs[0])[1] == 6
    assert g.chain_page_items(chain, procs, procs[1])[1] == 7     # the processor without pages
    assert g.chain_page_items(None, [], None) == ([], None)


def test_grid_pages_sections_and_rows():
    chain, procs = chain_and_procs()
    items, _ = g.chain_page_items(chain, procs, procs[0])
    pages, rows = g.grid_pages(items)
    assert rows == [1, 2, 4, 5, 6, 7, 9]
    assert [(p.title, p.section, p.section_index, p.empty) for p in pages] == [
        ("Controllers 1", "Chain", 0, False), ("Controllers 2", "Chain", 0, False), ("S0", "Helm", 1, False),
        ("S1", "Helm", 1, False), ("S2", "Helm", 1, False), ("Player", "Player", 2, True), ("Room", "Reverb", 3, False)]
    # the chain controllers have a colour of their own, the processors count from 0 without them
    assert [(p.kind, p.color_index) for p in pages] == [
        ("chain", -1), ("chain", -1), ("proc", 0), ("proc", 0), ("proc", 0), ("empty", 1), ("proc", 2)]
    # the Qt UI's entry dicts give the same pages
    dicts = [{"title": i.title, "separator": i.separator, "header": i.header, "data": i.data} for i in items]
    assert [p.title for p in g.grid_pages(dicts)[0]] == [p.title for p in pages]
    pages, selected = g.chain_pages(chain, procs, procs[0])
    assert selected == 2 and g.first_slot(pages[6]) == 0 and g.first_slot(pages[5]) == -1


def test_processor_colours_without_chain_controllers():
    chain, procs = chain_and_procs(chain_ctrls=0)
    pages, _ = g.chain_pages(chain, procs, procs[0])
    assert pages[0].section == "Helm" and [p.color_index for p in pages] == [0, 0, 0, 1, 2]


def test_section_colors():
    assert g.section_color(0) == (0x5a, 0x9e, 0xf0) and g.section_color(5) == g.section_color(0)
    g.set_section_colors(["#ff0000", "#8000ff00", "bad"])
    try:
        assert g.section_colors() == ["#ff0000", "#00ff00"] and g.section_color(3) == (0, 255, 0)
    finally:
        g.set_section_colors(None)
    assert g.section_color(1) == (0xf4, 0x95, 0x00)
    # the chain controllers' own colour (color_index -1)
    assert g.section_color(-1) == g._rgb(g.DEFAULT_CHAIN_COLOR)
    g.set_chain_color("#102030")
    try:
        assert g.section_color(-1) == (0x10, 0x20, 0x30)
        assert g.page_color(g.GridPage(0, "C", "Chain", 0, kind="chain", color_index=-1)) == (0x10, 0x20, 0x30)
    finally:
        g.set_chain_color(None)
    assert g.chain_color() == g.DEFAULT_CHAIN_COLOR


# The window by whole windows (a controller's pages), the selected cell

def test_paged_window():
    grid = g.ControlGrid("grid8x6", paged=True)
    grid.set_pages(pages(27), 0)
    assert grid.total_rows == 14 and grid.window_count == 3 and grid.window == 0
    grid.select(12)
    assert grid.first_row == 6 and grid.window == 1 and grid.shown_pages == list(range(12, 24))
    grid.select(26)
    assert grid.first_row == 12 and grid.shown_pages == [24, 25, 26]    # not clamped back to row 8
    assert grid.scroll_to(7) and grid.first_row == 6
    unpaged = g.ControlGrid("grid8x6")
    unpaged.set_pages(pages(27), 26)
    assert unpaged.first_row == 8


def test_selected_slot():
    grid = g.ControlGrid("grid8x6")
    pp = pages(4)
    pp[1].zctrls[0] = None
    grid.set_pages(pp, 0)
    assert grid.selected_slot == 0 and grid.selected_cell == 0
    events = []
    grid.add_listener(lambda e, d: events.append(e))
    grid.select(1)
    assert grid.selected_slot == 1 and grid.selected_cell == 5      # its first controller
    assert grid.select_slot(3) and grid.selected_cell == 7 and events == ["state", "state"]
    assert grid.select(1, 2) and grid.selected_slot == 2
    assert grid.select(3, 1) and grid.selected_cell == 13
    grid.set_pages(pp, 2, slot=3)
    assert grid.selected_cell == 11


# turn_travel: a strip's travel

def test_turn_travel_continuous_and_fine():
    grid = g.ControlGrid("grid4x6")
    pp = pages(1)
    pp[0].zctrls[0] = z = ctrl("f", value_min=0.0, value_max=2.0, value=0.0, is_integer=False)
    grid.set_pages(pp, 0)
    assert grid.turn_travel(0, 127) is z and z.value == 2.0
    grid.turn_travel(0, -127, fine=True)
    assert abs(z.value - 1.8) < 1e-9
    assert grid.turn_travel(0, 0) is None


def test_turn_travel_integers_accumulate():
    grid = g.ControlGrid("grid4x6")
    pp = pages(1)
    pp[0].zctrls[0] = z = ctrl("i", value_min=0, value_max=4, value=0)
    grid.set_pages(pp, 0)
    # 5 values: one step per 127 / 4 = 31.75 of travel
    for _ in range(3):
        grid.turn_travel(0, 10)
    assert z.value == 0
    grid.turn_travel(0, 2)
    assert z.value == 1
    grid.turn_travel(0, -1)     # the direction turns: the rest is dropped
    assert z.value == 1
    grid.turn_travel(0, 127)
    assert z.value == 4
    # a full-range integer (0..127): one step per unit of travel
    pp[0].zctrls[1] = w = ctrl("w")
    grid.set_pages(pp, 0)
    grid.turn_travel(1, 1)
    assert w.value == 1
    grid.turn_travel(1, 1, fine=True)
    assert w.value == 1


def test_turn_travel_lists_toggles_triggers():
    grid = g.ControlGrid("grid4x6")
    pp = pages(1)
    pp[0].zctrls[0] = wave = ctrl("l", labels=["a", "b", "c", "d", "e"])
    pp[0].zctrls[1] = tog = ctrl("t", labels=["off", "on"])
    pp[0].zctrls[2] = trig = ctrl("x", labels=["go"])
    grid.set_pages(pp, 0)
    grid.turn_travel(0, 20)
    assert wave.get_value2label() == "a"
    grid.turn_travel(0, 12)     # 32 > 127 / 4
    assert wave.get_value2label() == "b"
    wave.set_value(wave.ticks[3])   # changed elsewhere: no rest
    grid.turn_travel(0, 31)
    assert wave.get_value2label() == "d"
    grid.turn_travel(1, 100)
    assert tog.get_value2label() == "off"
    grid.turn_travel(1, 30)
    assert tog.get_value2label() == "on"
    assert grid.turn_travel(2, 127) is None and trig.value == trig.value_min
    # a detent drops the rest
    grid.turn_travel(0, 31)
    grid.turn(0, -1)
    v = wave.value
    grid.turn_travel(0, 1)
    assert wave.value == v


# The shared selection

def test_shared_selection_without_owner_and_signals():
    from zyngine.zynthian_signal_manager import zynsigman
    sel = g.SharedSelection()
    got = []

    def on_page(**kw):
        got.append(("page", kw))

    def on_cell(**kw):
        got.append(("cell", kw))

    def on_window(**kw):
        got.append(("window", kw))
    zynsigman.register(zynsigman.S_GUI, zynsigman.SS_GUI_CONTROL_GRID_PAGE, on_page)
    zynsigman.register(zynsigman.S_GUI, zynsigman.SS_GUI_CONTROL_GRID_CELL, on_cell)
    zynsigman.register(zynsigman.S_GUI, zynsigman.SS_GUI_CONTROL_GRID_WINDOW, on_window)
    try:
        assert sel.get(1) is None
        sel.request_page(1, 3)
        assert sel.get(1).page == 3 and sel.get(2) is None
        assert got == [("page", {"chain": 1, "page": 3, "slot": -1}), ("cell", {"chain": 1, "page": 3, "slot": -1})]
        got.clear()
        sel.request_cell(1, 3, 2)
        assert got == [("cell", {"chain": 1, "page": 3, "slot": 2})]
        got.clear()
        sel.report_cell(1, 3, 2)
        assert got == []                            # no change, no signal
        sel.request_window(1, 6)
        assert got == [("window", {"chain": 1, "first_row": 6, "rows": 0, "layout": ""})]
        got.clear()
        sel.request_open(1, 4)                      # without an owner: only selected
        assert sel.get(1).page == 4 and got[0] == ("page", {"chain": 1, "page": 4, "slot": -1})
    finally:
        zynsigman.unregister(zynsigman.S_GUI, zynsigman.SS_GUI_CONTROL_GRID_PAGE, on_page)
        zynsigman.unregister(zynsigman.S_GUI, zynsigman.SS_GUI_CONTROL_GRID_CELL, on_cell)
        zynsigman.unregister(zynsigman.S_GUI, zynsigman.SS_GUI_CONTROL_GRID_WINDOW, on_window)


def test_shared_selection_requests_go_to_the_owner():
    sel = g.SharedSelection()

    class Owner:
        def __init__(self):
            self.asked = []

        def grid_selection_request(self, *args):
            self.asked.append(args)
    owner = Owner()
    sel.set_owner(owner)
    sel.request_cell(4, 2, 1)
    sel.request_page(4, 5)
    sel.request_window(4, 12)
    sel.request_open(4, 3)
    assert owner.asked == [("cell", 4, 2, 1, 0), ("page", 4, 5, -1, 0), ("window", 4, -1, -1, 12), ("open", 4, 3, -1, 0)]
    assert sel.get(4) is None                       # only what the owner reports
    assert not sel.request_show(4)  # an owner without show requests: nothing
    owner.grid_show_request = lambda chain: owner.asked.append(("show", chain))
    assert sel.request_show(4)
    assert owner.asked[-1] == ("show", 4)
    assert not sel.owner_shown()
    owner.shown = True
    assert sel.owner_shown()
    sel.clear_owner(object())
    assert sel.owner is owner
    sel.clear_owner(owner)
    assert sel.owner is None and not sel.owner_shown()


def test_chain_controller_pages_named_with_gaps():
    chain, procs = chain_and_procs(chain_ctrls=0)
    rp = chain.zctrl_pages
    synth, fx = procs[0], procs[2]
    rp.assign(synth.controllers_dict["s21"], 0, 0)
    rp.assign(fx.controllers_dict["wet"], 0, 3)
    rp.rename_page(0, "Perform")
    rp.add_page("Empty")
    items, selected = g.chain_page_items(chain, procs, synth)
    assert [(i.title, i.separator) for i in items[:4]] == [
        ("CHAIN", True), ("Perform", False), ("Empty", False), ("Helm", True)]
    assert selected == 4                                # the current processor's screen, as before
    pages, rows = g.grid_pages(items)
    assert [(p.title, p.section, p.section_index) for p in pages[:3]] == [
        ("Perform", "Chain", 0), ("Empty", "Chain", 0), ("S0", "Helm", 1)]
    assert pages[0].zctrls == [synth.controllers_dict["s21"], None, None, fx.controllers_dict["wet"]]
    # grid8x6: two pages a row
    grid = g.ControlGrid("grid8x6")
    grid.set_pages(pages, 0)
    assert grid.page_at(0, 0) == 0 and grid.page_at(0, 1) == 1 and grid.page_at(1, 0) == 2
    # the page shown is selected when the list is built again
    rp.set_shown(1)
    assert g.chain_page_items(chain, procs, synth)[1] == 2
    assert g.chain_pages(chain, procs, synth)[1] == 1
    rp.set_shown(None)
    assert g.chain_pages(chain, procs, synth)[1] == 2   # S0 of Helm (screen 0)


def test_zctrl_assign_maps_a_row_of_eight_onto_two_pages():
    """A driver's flat slot (the JAM's strips 1-8): 0-3 the current page, 4-7 the next one"""
    chain, procs = chain_and_procs(chain_ctrls=0)
    rp = chain.zctrl_pages
    s = procs[0].controllers_dict
    assert g.zctrl_assign(chain, s["s00"], 5) == 1
    assert len(rp.pages) == 2 and rp.pages[1].slots[1] == (1, "s00")
    rp.current = 1
    assert g.zctrl_assign(chain, s["s01"], 6) == 2 and rp.pages[2].slots[2] == (1, "s01")
    assert g.zctrl_assign(chain, s["s02"], 0, page=0) == 0 and rp.pages[0].slots[0] == (1, "s02")
    assert g.zctrl_assign(chain, s["s01"], -1) == 0 and rp.find(s["s01"]) == []
    assert len(rp.pages) == 2                           # the emptied default-named last page went


def test_no_chain_section_without_pages():
    chain, procs = chain_and_procs(chain_ctrls=0)
    assert g.chain_page_items(chain, procs, None)[0][0].title == "Helm"
