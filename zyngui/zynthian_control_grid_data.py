"""Chain control's controller pages as a grid of cells (the Qt UI's grid layouts, inspired by the
Electra One's control grid). UI independent: no Qt, no Tk, so other consumers (e.g. a later
mapping onto a controller's pad grid) can share it. docs/qt-control-grid.md

The model:

- a **page** (GridPage) is one zynthian controller page: up to 4 controllers, in order, with its
  title and section (the chain's controllers, or the processor it belongs to). A processor
  without pages is a page without controllers (`empty`), so it stays selectable;
- the **layout** (GridLayout) has `rows` grid rows of `pages_per_row` pages, each page 4 cells
  wide: grid4x6 one page a row (24 cells), grid8x6 two (48 cells). A page never spans rows;
  pages fill the rows in order (page p is in row p // pages_per_row);
- the **window**: the `rows` grid rows shown, from `first_row`; it scrolls by rows to keep the
  selected page in view;
- the **selection**: one page (the one the four encoders turn);
- **cells** (GridCell): rows x columns, in reading order; a cell holds its page's controller
  (zctrl, name, kind, value, value text, enabled) or nothing;
- **the anchor**: the selected page's first controller (`selected_zctrl`), which views with
  other row widths keep in step with (page boundaries differ between 4x6 and 8x6);
- **change notification**: listeners get ("structure", None) when the pages, the layout or the
  window change (the cells hold other controllers), ("state", None) when only the selection
  changes, ("values", cells) from poll() when shown controllers changed;
- **values** are watched by comparison (ValueWatcher: one per consumer), never through
  zctrl.is_dirty, which chain control's controller slots consume (two consumers of the flag
  would steal each other's updates). zynthian has no per-value signal, and some engines write
  zctrl.value directly;
- **input**: turn, press, release, touch, set_default, select_page / select_row / select_cell,
  as methods (the QML calls them through the Qt wrapper; other consumers would too). A
  selection goes through `on_select` when set (the owner's page selection, which calls select()
  back), else straight to select().

Not thread safe: call it from one thread (the Qt UI's main thread); a provider on another thread
needs a lock or the GUI thread (zynqt.gui_thread), or a ControlGrid of its own.

Shared with other consumers (a controller driver, e.g. DrivenByMoss's host pages):

- **the page list without Qt**: chain_page_items() (chain control's page list: the chain
  controllers' named pages of 4, then each processor's controller screens, a processor without
  screens as one selectable header) and grid_pages() (its GridPages), chain_pages() both at once;
- **section colours** as RGB: page_color(page) / section_color(color_index), the chain
  controllers' own (controlGridChainColor), the processors' from the theme's controlGridColors
  (the Qt UI passes them with set_section_colors / set_chain_color; without it ThemeBase's
  defaults);
- **the shared selection** (shared_selection, a SharedSelection): chain control's page, selected
  cell and window, readable and requestable from any thread, with a zynsigman signal for every
  change (SS_GUI_CONTROL_GRID_PAGE / _CELL / _WINDOW);
- **turn_travel**: a strip's travel (delta / 127 of the range) next to turn (an encoder's detent).
"""

import functools
import logging
import math
import threading
from collections import namedtuple

from zyngine.zynthian_signal_manager import zynsigman

CELLS_PER_PAGE = 4

# turn_travel: the travel of a whole range (a controller's strip or fader, as MIDI's 0..127) and
# the fine resolution's divisor
TRAVEL = 127.0
FINE = 10.0

GridLayout = namedtuple("GridLayout", "name columns rows pages_per_row")

LAYOUTS = {
    "grid4x6": GridLayout("grid4x6", 4, 6, 1),
    "grid8x6": GridLayout("grid8x6", 8, 6, 2),
}

# Cell kinds: what a cell shows and what a tap does
KIND_EMPTY = "empty"        # no controller
KIND_FLOAT = "float"        # continuous: a bar or arc
KIND_INTEGER = "integer"    # integer steps: a bar or arc
KIND_LIST = "list"          # more than two labelled values: the label and its position
KIND_TOGGLE = "toggle"      # two values: on / off
KIND_TRIGGER = "trigger"    # one value: a button
KIND_PATH = "path"          # a file: its name


def cell_kind(zctrl):
    if zctrl is None:
        return KIND_EMPTY
    if getattr(zctrl, "is_path", False):
        return KIND_PATH
    if zctrl.is_trigger:
        return KIND_TRIGGER
    if zctrl.is_toggle:
        return KIND_TOGGLE
    if zctrl.ticks or (isinstance(zctrl.labels, list) and len(zctrl.labels) > 2):
        return KIND_LIST
    if zctrl.is_integer:
        return KIND_INTEGER
    return KIND_FLOAT


def cell_value_text(zctrl):
    """The value as text: the controller's label for it (zynthian_controller.get_value2label)"""
    if zctrl is None:
        return ""
    try:
        label = zctrl.get_value2label()
    except Exception:
        label = zctrl.value
    if isinstance(label, float):
        return f"{label:.3g}" if abs(label) < 1000 else f"{label:.0f}"
    return str(label)


def cell_fraction(zctrl):
    """The value's position, 0..1 (logarithmic controllers as their MIDI mapping)"""
    if zctrl is None:
        return 0.0
    if isinstance(zctrl.value, str):
        labels = getattr(zctrl, "labels", None) or []
        if zctrl.value in labels and len(labels) > 1:
            return labels.index(zctrl.value) / (len(labels) - 1)
        return 0.0
    try:
        return max(0.0, min(1.0, zctrl.get_ctrl_midi_val() / 127))
    except Exception:
        rng = zctrl.value_range or 1
        try:
            return max(0.0, min(1.0, (zctrl.value - zctrl.value_min) / rng))
        except TypeError:
            return 0.0


def cell_origin(zctrl):
    """Where a bar starts, 0..1: the zero of a range across it (pan, detune), else 0"""
    try:
        if zctrl is None or zctrl.ticks or zctrl.is_logarithmic or not zctrl.value_range:
            return 0.0
        if zctrl.value_min < 0 < zctrl.value_max:
            return -zctrl.value_min / zctrl.value_range
    except (TypeError, AttributeError):
        pass
    return 0.0


def cell_list_index(zctrl):
    """(index, count) of a list's / toggle's value, (-1, 0) for others"""
    if zctrl is None or not zctrl.ticks:
        return -1, 0
    try:
        return zctrl.get_value2index(), len(zctrl.ticks)
    except Exception:
        return -1, len(zctrl.ticks)


def cell_items(zctrl):
    """A list's / toggle's values as [(label, value)], [] for others"""
    if zctrl is None or not zctrl.ticks or not isinstance(zctrl.labels, list):
        return []
    return list(zip((str(label) for label in zctrl.labels), zctrl.ticks))


def cell_name(zctrl):
    if zctrl is None:
        return ""
    return (zctrl.short_name or zctrl.name or "").replace("_", " ")


def cell_steps(zctrl):
    """The values of a stepped controller in order (a list's / toggle's ticks, a toggle's two
    values, the integers of an integer range), None for continuous ones"""
    if zctrl is None:
        return None
    ticks = getattr(zctrl, "ticks", None)
    if ticks and len(ticks) > 1:
        return list(ticks)
    lo, hi = zctrl.value_min, zctrl.value_max
    if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)) or hi <= lo:
        return None
    if zctrl.is_toggle:
        return [lo, hi]
    if zctrl.is_integer and not zctrl.is_logarithmic:
        return range(int(lo), int(hi) + 1) if hi - lo >= 1 else None
    return None


# Chain control's page list (zynthian_gui_control.fill_list), without Qt

PageItem = namedtuple("PageItem", "title separator header data")
"""A row of chain control's page list: a section title (separator: "CHAIN", the processor's
name), a page (data ("chain", None, (chain controller page, zctrls)) or ("proc", processor,
screen index)) or a processor without pages (header: a selectable section title, data
("empty", processor, 0))"""

CHAIN_SECTION = "CHAIN"


def chain_zctrl_pages(chain):
    """The chain's controller pages (zyngine.zynthian_zctrl_pages.ZctrlPages: the chain
    controllers), None without"""
    zpages = getattr(chain, "zctrl_pages", None) if chain is not None else None
    return zpages if zpages is not None and hasattr(zpages, "zctrls") else None


def zctrl_assign(chain, zctrl, slot, page=None):
    """Put a controller (None: clear the slot) into a chain controller slot: page None: flat
    slot `slot` counted from the current page (slots 0-3 the current page, 4-7 the next one:
    the JAM's row of 8 strips; the pages up to it created), else slot `slot` (0-3) of `page`;
    slot -1: remove the controller from all pages (empty default-named last pages go). The
    page's index (-1: nothing done). Call it in the GUI thread (drivers:
    shared_selection.request_zctrl_assign)"""
    zpages = chain_zctrl_pages(chain)
    if zpages is None:
        return -1
    if slot < 0:
        if zctrl is None or not zpages.remove(zctrl, prune=True):
            return -1
        zctrl_pages_changed(chain)
        return 0
    if page is None:
        page = zpages.assign_flat(zctrl, slot, max(0, zpages.current_page()))
    else:
        page = zpages.assign(zctrl, page, slot)
    if page >= 0:
        zctrl_pages_changed(chain)
    return page


def zctrl_pages_changed(chain):
    """A chain's controller pages changed (assigned, renamed, moved ...): SS_GUI_CONTROL_GRID_ZCTRL_PAGES,
    so consumers (DrivenByMoss's host pages) read the pages again"""
    zynsigman.send(zynsigman.S_GUI, zynsigman.SS_GUI_CONTROL_GRID_ZCTRL_PAGES, chain=getattr(chain, "chain_id", None))


def chain_page_items(chain, processors, current_processor=None):
    """Chain control's page list of a chain: the chain controllers' pages (CHAIN: named pages of
    4), then each processor's controller screens under its name, a processor without screens
    (no soundfont / preset loaded yet, the audio player without a file, a plugin without
    controllers) as a selectable header. Returns (items, selected): selected is the row of the
    chain controller page the screen shows (zctrl_pages.shown), else of the current processor's
    current screen (or of its header), else the first page, None without pages. chain None:
    only the processors (a special processor's screen)"""
    items = []
    selected = None
    zctrl_selected = None
    zpages = chain_zctrl_pages(chain)
    if zpages is not None and zpages.pages:
        # The chain controllers first (docs/chain-controller-pages.md)
        items.append(PageItem(CHAIN_SECTION, True, False, None))
        for i, page in enumerate(list(zpages.pages)):
            if zpages.shown == i:
                zctrl_selected = len(items)
            items.append(PageItem(page.name, False, False, ("chain", None, (i, zpages.zctrls(i)))))
    for proc in processors:
        screens = proc.get_ctrl_screens()
        name = proc.engine.name.split("/")[-1]
        if not screens:
            if proc == current_processor:
                selected = len(items)
            items.append(PageItem(name, False, True, ("empty", proc, 0)))
            continue
        items.append(PageItem(name, True, False, None))
        for j, title in enumerate(screens):
            if proc == current_processor and j == proc.get_current_screen_index():
                selected = len(items)
            items.append(PageItem(title, False, False, ("proc", proc, j)))
    if zctrl_selected is not None:
        selected = zctrl_selected
    if selected is None:
        selected = next((i for i, item in enumerate(items) if not item.separator), None)
    return items, selected


def _page_item(item):
    """A PageItem of a page list row (a PageItem, or the Qt UI's entry dict)"""
    if isinstance(item, dict):
        return PageItem(item["title"], item["separator"], item.get("header", False), item["data"])
    return item


def grid_pages(items):
    """The GridPages of a page list (chain_page_items' items, or the Qt UI's entries): one per
    page row, its key the row, sections counted from 0 (the chain controllers, then each
    processor); colours: the chain controllers' own (color_index -1), the processors' counted
    from 0 without them (a processor keeps its colour with or without chain controllers).
    Returns (pages, rows): rows[i] is page i's row"""
    pages = []
    rows = []
    section, section_index = "", -1
    chain_sections = 0
    for row, item in enumerate(items):
        item = _page_item(item)
        if item.separator:
            section = item.title
            section_index += 1
            continue
        kind, proc, arg = item.data
        if kind == "chain":
            zctrls = arg[1]
        elif kind == "empty":
            section = item.title
            section_index += 1
            zctrls = []
        else:
            try:
                zctrls = proc.get_ctrl_screen(item.title)
            except Exception:
                zctrls = []
        if kind == "chain":
            if not chain_sections:
                chain_sections = 1
            color_index = -1
        else:
            color_index = max(0, section_index - chain_sections)
        pages.append(GridPage(row, item.title, section.title() if section.isupper() else section,
                              max(0, section_index), zctrls, empty=(kind == "empty"),
                              kind=kind, color_index=color_index))
        rows.append(row)
    return pages, rows


def chain_pages(chain, processors, current_processor=None):
    """The GridPages of a chain's page list (chain_page_items + grid_pages) and the index of the
    selected one (-1: none)"""
    items, selected = chain_page_items(chain, processors, current_processor)
    pages, rows = grid_pages(items)
    return pages, rows.index(selected) if selected in rows else -1


def first_slot(page):
    """The slot (0-3) of a page's first controller, -1 if it has none (the default selected cell)"""
    return next((i for i, z in enumerate(page.zctrls) if z is not None), -1) if page is not None else -1


# Section colours: the theme's controlGridColors (ThemeBase.qml's until the UI passes its theme's)

DEFAULT_SECTION_COLORS = ("#5a9ef0", "#f49500", "#03a598", "#c44795", "#f45c51")
_section_colors = [DEFAULT_SECTION_COLORS]
# The chain controllers' section: a fixed colour of its own (ThemeBase.qml's controlGridChainColor)
DEFAULT_CHAIN_COLOR = "#d8d8d8"
_chain_color = [DEFAULT_CHAIN_COLOR]


def _rgb(color):
    """(r, g, b) of "#rrggbb" / "#aarrggbb" / "rrggbb", None if it isn't one"""
    text = str(color).strip().lstrip("#")
    if len(text) == 8:
        text = text[2:]
    try:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)) if len(text) == 6 else None
    except ValueError:
        return None


def set_section_colors(colors):
    """The theme's section colours (controlGridColors, "#rrggbb"); empty or None: the defaults"""
    rgb = [c for c in (_rgb(color) for color in (colors or ())) if c is not None]
    _section_colors[0] = tuple(f"#{r:02x}{g:02x}{b:02x}" for r, g, b in rgb) or DEFAULT_SECTION_COLORS


def section_colors():
    return list(_section_colors[0])


def set_chain_color(color):
    """The theme's colour of the chain controllers' section (controlGridChainColor); None: the
    default"""
    _chain_color[0] = color if _rgb(color) is not None else DEFAULT_CHAIN_COLOR


def chain_color():
    return _chain_color[0]


def section_color(index):
    """The RGB colour of a colour index (GridPage.color_index: -1 the chain controllers' own,
    processors from 0, wrapping as ControlGrid.qml's accent)"""
    if int(index) < 0:
        return _rgb(_chain_color[0])
    colors = _section_colors[0]
    return _rgb(colors[int(index) % len(colors)])


def page_color(page):
    """The RGB colour of a GridPage (its section's)"""
    return section_color(page.color_index)


class GridPage:
    """A controller page: key (the UI's own reference, e.g. the page list entry), title, section
    (its section's title), section_index (the sections in order), zctrls (up to 4, None for
    gaps), empty (a processor without pages), kind ("chain": a chain controller page, "proc",
    "empty"), color_index (the colour: -1 the chain controllers', else the processor sections
    from 0)"""

    def __init__(self, key, title, section="", section_index=0, zctrls=(), empty=False, kind="proc",
                 color_index=None):
        self.key = key
        self.title = title
        self.section = section
        self.section_index = section_index
        self.zctrls = list(zctrls)[:CELLS_PER_PAGE]
        self.empty = empty
        self.kind = kind
        self.color_index = section_index if color_index is None else color_index

    def __repr__(self):
        return f"GridPage({self.section}/{self.title})"


class GridCell:
    """A cell: its place (row, column of the shown grid), the page it shows (or None) and the
    page's controller at slot (column within the page), or none"""

    def __init__(self, row, column, columns):
        self.row = row
        self.column = column
        self.id = row * columns + column
        self.slot = column % CELLS_PER_PAGE
        self.page = None        # the index of its page in ControlGrid.pages, or -1
        self.zctrl = None

    @property
    def enabled(self):
        return self.zctrl is not None and not getattr(self.zctrl, "readonly", False)

    @property
    def kind(self):
        return cell_kind(self.zctrl)

    @property
    def name(self):
        return cell_name(self.zctrl)

    @property
    def value(self):
        return None if self.zctrl is None else self.zctrl.value

    @property
    def value_text(self):
        return cell_value_text(self.zctrl)

    @property
    def fraction(self):
        return cell_fraction(self.zctrl)

    @property
    def items(self):
        return cell_items(self.zctrl)

    def __repr__(self):
        return f"GridCell({self.row},{self.column}: {self.name or '-'})"


class ControlGrid:
    """The grid: pages, layout, window, selection, cells. See the module's doc."""

    def __init__(self, layout="grid4x6", paged=False):
        self.layout = LAYOUTS.get(layout, LAYOUTS["grid4x6"])
        # paged: the window moves by whole windows (first_row a multiple of rows, the last one
        # may be partly empty), as a controller's pages; else by rows (the Qt UI)
        self.paged = paged
        self.pages = []
        self.selected = -1
        self.selected_slot = -1     # the selected cell's slot in the selected page (-1: none)
        self.first_row = 0
        self.cells = []
        self._listeners = []
        self._travel = {}           # turn_travel: id(zctrl) -> (zctrl, value, the rest)
        self.on_select = None   # f(page): the owner selects the page (and calls select())
        self._make_cells()

    # Notification

    def add_listener(self, cb):
        """cb(event, data): ("structure", None), ("state", None) or ("values", [GridCell])"""
        self._listeners.append(cb)

    def remove_listener(self, cb):
        if cb in self._listeners:
            self._listeners.remove(cb)

    def _notify(self, event, data=None):
        for cb in list(self._listeners):
            try:
                cb(event, data)
            except Exception as e:
                logging.exception(f"control grid listener: {e}")

    # Layout and pages

    @property
    def columns(self):
        return self.layout.columns

    @property
    def rows(self):
        return self.layout.rows

    @property
    def pages_per_row(self):
        return self.layout.pages_per_row

    @property
    def total_rows(self):
        return (len(self.pages) + self.pages_per_row - 1) // self.pages_per_row

    def _make_cells(self):
        self.cells = [GridCell(r, c, self.columns) for r in range(self.rows) for c in range(self.columns)]

    def set_layout(self, name):
        layout = LAYOUTS.get(name)
        if layout is None or layout == self.layout:
            return False
        self.layout = layout
        self._make_cells()
        self.first_row = 0
        self._scroll_to_selected()
        self._fill()
        self._notify("structure")
        return True

    def set_pages(self, pages, selected=-1, slot=None):
        """New pages (a chain or processor change, a rebuild), selected: the selected page's
        index, slot: the selected cell's (None: the page's first controller)"""
        self.pages = list(pages)
        self.selected = selected if 0 <= selected < len(self.pages) else (0 if self.pages else -1)
        self.selected_slot = self._slot_of(self.selected, slot)
        self.first_row = self._clamp_first(self.first_row)
        self._scroll_to_selected()
        self._fill()
        self._notify("structure")

    # Selection and window

    def row_of(self, page):
        return page // self.pages_per_row if page >= 0 else -1

    @property
    def selected_row(self):
        """The selected page's row in the window (-1: not shown)"""
        r = self.row_of(self.selected) - self.first_row
        return r if 0 <= r < self.rows else -1

    @property
    def selected_half(self):
        """The selected page's place in its row (0, or 0 / 1 with two pages a row)"""
        return self.selected % self.pages_per_row if self.selected >= 0 else 0

    def page_at(self, row, part=0):
        """The page shown at window row `row`, part `part` (0 or 1), or -1"""
        p = (self.first_row + row) * self.pages_per_row + part
        return p if 0 <= row < self.rows and 0 <= part < self.pages_per_row and p < len(self.pages) else -1

    @property
    def window(self):
        """The window's number (first_row // rows; paged: the windows don't overlap)"""
        return self.first_row // self.rows

    @property
    def window_count(self):
        return max(1, math.ceil(self.total_rows / self.rows))

    @property
    def first_page(self):
        """The index of the window's first page"""
        return self.first_row * self.pages_per_row

    @property
    def shown_pages(self):
        """The indices of the window's pages"""
        return list(range(self.first_page, min(len(self.pages), self.first_page + self.rows * self.pages_per_row)))

    def _slot_of(self, page, slot):
        """A valid selected slot of a page: slot if it is one, else the page's first controller"""
        if not 0 <= page < len(self.pages):
            return -1
        if slot is not None and 0 <= slot < CELLS_PER_PAGE:
            return slot
        return first_slot(self.pages[page])

    @property
    def selected_cell(self):
        """The id of the selected cell (the selected page's selected slot), -1 if not shown"""
        if self.selected_slot < 0:
            return -1
        return next((c.id for c in self.cells if c.page == self.selected and c.slot == self.selected_slot), -1)

    def select_slot(self, slot):
        """Select a cell of the selected page by its slot (0-3)"""
        if not 0 <= slot < CELLS_PER_PAGE or slot == self.selected_slot or self.selected < 0:
            return False
        self.selected_slot = slot
        self._notify("state")
        return True

    def select(self, page, slot=None):
        """Select a page (scrolls the window to show it) and a cell of it (slot; None: its first
        controller)"""
        if not 0 <= page < len(self.pages):
            return False
        if page == self.selected:
            return slot is not None and self.select_slot(slot)
        self.selected = page
        self.selected_slot = self._slot_of(page, slot)
        if self._scroll_to_selected():
            self._fill()
            self._notify("structure")
        else:
            self._notify("state")
        return True

    @property
    def selected_zctrl(self):
        """The anchor: the selected page's first controller (None: none)"""
        if 0 <= self.selected < len(self.pages):
            return next((z for z in self.pages[self.selected].zctrls if z is not None), None)
        return None

    def page_of_zctrl(self, zctrl):
        return next((i for i, p in enumerate(self.pages) if zctrl in p.zctrls), -1)

    def move(self, step):
        """The previous / next page (the window follows)"""
        if not self.pages:
            return False
        return self.select(max(0, min(len(self.pages) - 1, self.selected + step)))

    def _clamp_first(self, first):
        if self.paged:
            last = max(0, (self.total_rows - 1) // self.rows * self.rows)
            return max(0, min(first // self.rows * self.rows, last))
        return max(0, min(first, max(0, self.total_rows - self.rows)))

    def _scroll_to_selected(self):
        row = self.row_of(self.selected)
        first = self.first_row
        if row >= 0:
            if self.paged:
                first = row // self.rows * self.rows
            elif row < first:
                first = row
            elif row >= first + self.rows:
                first = row - self.rows + 1
        first = self._clamp_first(first)
        if first != self.first_row:
            self.first_row = first
            return True
        return False

    def scroll(self, rows):
        """Scroll the window by rows (the selection stays; it may scroll out of view)"""
        return self.scroll_to(self._clamp_first(self.first_row + rows))

    def scroll_to(self, first):
        first = self._clamp_first(first)
        if first == self.first_row:
            return False
        self.first_row = first
        self._fill()
        self._notify("structure")
        return True

    # Cells

    def _fill(self):
        """Put the window's pages into the cells"""
        for cell in self.cells:
            part = cell.column // CELLS_PER_PAGE
            p = self.page_at(cell.row, part)
            cell.page = p
            zctrls = self.pages[p].zctrls if p >= 0 else []
            cell.zctrl = zctrls[cell.slot] if cell.slot < len(zctrls) else None

    def page_cells(self, page):
        return [c for c in self.cells if c.page == page and page >= 0]

    def shown_zctrls(self):
        return [c.zctrl for c in self.cells if c.zctrl is not None]

    # Input (cells by id: row * columns + column)

    def cell(self, cell_id):
        return self.cells[cell_id] if 0 <= cell_id < len(self.cells) else None

    def select_page(self, page):
        """Select a page as input (through on_select when set)"""
        if not 0 <= page < len(self.pages):
            return False
        if self.on_select is not None:
            self.on_select(page)
            return True
        return self.select(page)

    def select_row(self, row, part=0):
        return self.select_page(self.page_at(row, part))

    def select_cell(self, cell_id):
        c = self.cell(cell_id)
        return c is not None and self.select_page(c.page)

    def turn(self, cell_id, delta, fine=False):
        """Change a cell's controller by delta steps (as an encoder: zctrl.nudge); the changed
        controller, or None"""
        c = self.cell(cell_id)
        z = c.zctrl if c is not None else None
        if z is None or getattr(z, "readonly", False) or not delta or getattr(z, "is_path", False):
            return None
        z.nudge(delta, fine=fine)
        self._travel.pop(id(z), None)
        return z

    def turn_travel(self, cell_id, delta, fine=False):
        """Change a cell's controller by a strip's travel: the normalized value moves by
        delta / TRAVEL (fine: a tenth of it), so a swipe across a strip of TRAVEL is the whole
        range (logarithmic controllers in their logarithmic scale, as nudge). Stepped controllers
        (lists, toggles, integers) accumulate the travel and step by one value at every
        1 / (values - 1); the rest is kept per controller (dropped when the direction turns or the
        value was changed elsewhere). The changed controller, or None"""
        c = self.cell(cell_id)
        z = c.zctrl if c is not None else None
        if z is None or getattr(z, "readonly", False) or not delta or getattr(z, "is_path", False) or z.is_trigger:
            return None
        amount = delta / TRAVEL / (FINE if fine else 1.0)
        steps = cell_steps(z)
        if steps is not None:
            index = z.get_value2index() if z.ticks else min(range(len(steps)), key=lambda i: abs(steps[i] - z.value))
            last = self._travel.get(id(z))
            rest = last[2] if last is not None and last[0] is z and last[1] == z.value and last[2] * amount > 0 else 0.0
            rest += amount * (len(steps) - 1)
            move = int(rest + (1e-9 if rest > 0 else -1e-9))
            rest -= move
            target = max(0, min(len(steps) - 1, index + move))
            if target in (0, len(steps) - 1) and target != index + move:
                rest = 0.0      # at an end: no rest to turn back first
            if target != index:
                z.set_value(steps[target])
            self._travel[id(z)] = (z, z.value, rest)
            return z
        rng = z.value_range
        if not rng:
            return None
        if z.is_logarithmic:
            log_val = math.log10((9 * z.value - (10 * z.value_min - z.value_max)) / rng)
            log_val = min(1, max(0, log_val + amount))
            z.set_value((math.pow(10, log_val) * rng + (10 * z.value_min - z.value_max)) / 9)
        else:
            z.set_value(z.value + amount * rng)
        return z

    def press(self, cell_id):
        """Press a cell: a toggle switches, a trigger fires, a list steps to the next label
        (wrapping), a file controller opens the file selector; the changed controller, or None"""
        c = self.cell(cell_id)
        z = c.zctrl if c is not None else None
        if z is None or getattr(z, "readonly", False):
            return None
        kind = cell_kind(z)
        if kind == KIND_TOGGLE:
            z.toggle()
            return z
        if kind in (KIND_TRIGGER, KIND_LIST) and z.ticks:
            # (not zctrl.toggle(): it looks the value up in the ticks exactly, which fails for
            # float ticks, e.g. 0.3 against 0.30000001192092896)
            n = len(z.ticks)
            try:
                i = z.get_value2index()
            except Exception:
                i = -1
            z.set_value(z.ticks[0] if kind == KIND_TRIGGER else z.ticks[(i + 1) % n])
            return z
        if kind == KIND_PATH:
            z.nudge(1)
        return None

    def release(self, cell_id):
        """A press ended (momentary controls: nothing yet)"""
        return None

    def touch(self, cell_id):
        """A cell touched (a drag starts): nothing in the model (MIDI learn is the UI's)"""
        return self.cell(cell_id)

    def set_default(self, cell_id):
        c = self.cell(cell_id)
        z = c.zctrl if c is not None else None
        if z is None or getattr(z, "readonly", False):
            return None
        z.reset_value()
        return z

    # Values

    def poll(self, watcher):
        """The shown cells whose values changed since the watcher last looked (notifies
        ("values", cells) when there are)"""
        changed = watcher.changed(self.cells)
        if changed:
            self._notify("values", changed)
        return changed


class ValueWatcher:
    """One consumer's view of the cells' values: changed(cells) compares each cell's controller
    and value with what it saw last (never zctrl.is_dirty) and returns the changed cells; a cell
    that now shows another controller counts as seen, not changed (its consumer redraws it with
    the structure)"""

    def __init__(self):
        self._seen = {}     # cell id -> (zctrl, value)

    def changed(self, cells):
        out = []
        seen = self._seen
        for c in cells:
            z = c.zctrl
            v = None if z is None else z.value
            old = seen.get(c.id)
            if old is None or old[0] is not z:
                seen[c.id] = (z, v)
            elif old[1] != v:
                seen[c.id] = (z, v)
                out.append(c)
        return out

    def reset(self):
        self._seen.clear()


# The shared selection: chain control's, read and requested by other consumers

Selection = namedtuple("Selection", "chain page slot first_row rows layout")
"""A chain's selection: chain (its chain_id), page (the index in chain_pages' pages, -1: none),
slot (the selected cell's slot in that page, -1: none), first_row / rows / layout (the screen's
grid window; layout "" without a grid shown)"""


class SharedSelection:
    """Chain control's selection (the page the encoders turn, its selected cell, the grid's
    window), shared with other consumers, e.g. a controller driver showing the grid (DrivenByMoss's
    host pages). One instance: shared_selection.

    - **The owner** (the screen, set_owner) holds the selection and reports every change with
      report_page / report_cell / report_window, whatever its origin (touch, encoders, the page
      list, a driver's request). Each report that changes the state sends a zynsigman signal
      (S_GUI, SS_GUI_CONTROL_GRID_PAGE / _CELL / _WINDOW) with the new state as keywords: chain,
      page, slot (page and cell), first_row, rows, layout (window). Sent directly from the
      reporting thread (the GUI thread); receivers on other threads only take note.
    - **Requests** (request_page, request_cell, request_open, request_window), from any thread:
      passed to the owner (owner.grid_selection_request(kind, chain, page, slot, first_row)), which
      applies them on its thread (Qt: queued to the GUI thread) and reports the result; without
      an owner (no chain control screen, e.g. the Tk UI) applied here at once (an "open" only
      selects). A request names the chain it means: one for another chain than the owner's is
      dropped by it.
    - **Reading** (get(chain)), from any thread: the last reported state of that chain, None if
      the selection is another chain's (the consumer then uses chain_pages' default).

    Page indices are those of chain_pages(chain, chain.get_processors(), chain.current_processor),
    the same for the screen and the consumers."""

    def __init__(self):
        self._lock = threading.Lock()
        self.owner = None
        self._state = Selection(None, -1, -1, 0, 0, "")

    def set_owner(self, owner):
        self.owner = owner

    def clear_owner(self, owner):
        if self.owner is owner:
            self.owner = None

    def owner_shown(self):
        """The owner (chain control) is on screen: its `shown` (False without an owner)"""
        return bool(getattr(self.owner, "shown", False))

    @property
    def state(self):
        with self._lock:
            return self._state

    def get(self, chain):
        """The selection of a chain (its chain_id), None if the shared one is another chain's"""
        state = self.state
        return state if state.chain is not None and state.chain == chain else None

    # The owner's reports (its thread)

    def _update(self, **changes):
        with self._lock:
            old = self._state
            new = old._replace(**changes)
            self._state = new
        return old, new

    def report_page(self, chain, page, slot=-1):
        """The selected page changed (and with it the cell: slot)"""
        old, new = self._update(chain=chain, page=page, slot=slot)
        if (old.chain, old.page) != (new.chain, new.page):
            zynsigman.send(zynsigman.S_GUI, zynsigman.SS_GUI_CONTROL_GRID_PAGE, chain=chain, page=page, slot=slot)
        if (old.chain, old.page, old.slot) != (new.chain, new.page, new.slot):
            zynsigman.send(zynsigman.S_GUI, zynsigman.SS_GUI_CONTROL_GRID_CELL, chain=chain, page=page, slot=slot)

    def report_cell(self, chain, page, slot):
        """The selected cell changed (a controller of the selected page touched or turned)"""
        self.report_page(chain, page, slot)

    def report_window(self, chain, first_row, rows, layout):
        """The screen's grid window changed (layout "": no grid shown)"""
        old, new = self._update(chain=chain, first_row=first_row, rows=rows, layout=layout)
        if (old.chain, old.first_row, old.rows, old.layout) != (new.chain, new.first_row, new.rows, new.layout):
            zynsigman.send(zynsigman.S_GUI, zynsigman.SS_GUI_CONTROL_GRID_WINDOW, chain=chain, first_row=first_row,
                           rows=rows, layout=layout)

    # Requests (any thread)

    def _request(self, kind, chain, page=-1, slot=-1, first_row=0):
        owner = self.owner
        if owner is not None:
            owner.grid_selection_request(kind, chain, page, slot, first_row)
        elif kind == "window":
            state = self.state
            self.report_window(chain, first_row, state.rows, state.layout)
        else:
            self.report_page(chain, page, slot)

    def request_page(self, chain, page):
        """Select a page (its first controller the selected cell)"""
        self._request("page", chain, page)

    def request_cell(self, chain, page, slot):
        """Select a page and a cell of it"""
        self._request("cell", chain, page, slot)

    def request_open(self, chain, page):
        """As a tap on the page's header: select the page; the selected page of a processor
        without pages (an empty page) opens its banks / presets (the owner's; without an owner
        only selected)"""
        self._request("open", chain, page)

    def request_window(self, chain, first_row):
        """Show the window from first_row (the selection stays)"""
        self._request("window", chain, first_row=first_row)

    def request_show(self, chain):
        """Bring chain control of the active chain (chain: its chain_id; another one is dropped)
        to the front, if it isn't shown: a controller switched to the host's pages (the JAM's
        HostPageShow), or navigates them. The owner decides (not over a dialog, a menu or a
        move); it lands where its selection is, so a page / cell request right after it selects
        the driver's page. Without an owner (the Tk UI): nothing. True if the owner got it"""
        owner = self.owner
        if owner is not None and hasattr(owner, "grid_show_request"):
            owner.grid_show_request(chain)
            return True
        return False

    def request_zctrl_assign(self, chain, zctrl, slot, page=None):
        """zctrl_assign (a chain controller slot; page None: flat slot `slot` from the current
        page, 4-7 the next page) in the owner's thread, which then rebuilds its pages (chain: the
        chain object, not its id); without an owner at once"""
        owner = self.owner
        call = functools.partial(zctrl_assign, chain, zctrl, slot, page)
        if owner is not None and hasattr(owner, "grid_zctrl_request"):
            owner.grid_zctrl_request(chain, call)
        else:
            call()


shared_selection = SharedSelection()
