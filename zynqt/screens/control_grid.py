"""Chain control's grid layouts (ZYNTHIAN_QT_CONTROL_LAYOUT grid4x6 / grid8x6): the shared grid
model (zyngui.zynthian_control_grid_data) for QML. docs/qt-control-grid.md

ControlGridModel is the grid as QML sees it: the cells (GridCellProxy, a controller slot like the
four of the controller column, so the looks and the touch read the same properties), the window's
pages (`blocks`: row by row, one or two a row) and the window's place in the page list. The
selection is chain control's page (ChainControl.setPage): the grid follows it, a tap on a page
selects it there; the four encoders keep turning chain control's four controllers, i.e. the
selected page's.
"""

from PySide6.QtCore import QObject, Property, Signal, Slot

from zyngui import zynthian_control_grid_data as gd
from zynqt.screens.control import ControllerProxy

LAYOUT_V5 = "v5"
LAYOUTS = (LAYOUT_V5,) + tuple(gd.LAYOUTS)
MAX_CELLS = max(lay.columns * lay.rows for lay in gd.LAYOUTS.values())


class GridCellProxy(ControllerProxy):
    """A cell: the controller of its page at its slot (or none). Touch: a drag changes it, a tap
    selects its page (and switches a toggle, presses a trigger, steps a list), a long press selects
    its page and opens the controller's options (as the controller column's long press)"""

    stateChanged = Signal()     # the page's selection, the place
    # (the base class's changed, re-emitted: PySide6 can't take a base class's signal as the
    # notify of a subclass's property, QML crashes in notifySignalIndex)
    cellChanged = Signal()

    def __init__(self, index, control, grid):
        super().__init__(index % gd.CELLS_PER_PAGE, control)
        self.changed.connect(self.cellChanged)
        self.cell_index = index
        self.grid = grid        # ControlGridModel
        self.cell = None        # the model's GridCell
        self.page = -1

    def set_cell(self, cell):
        self.cell = cell
        page = cell.page if cell is not None else -1
        zctrl = cell.zctrl if cell is not None else None
        if page != self.page:
            self.page = page
            self.stateChanged.emit()
        if zctrl is not self.zctrl:
            self.set_zctrl(zctrl)

    @Property(bool, notify=stateChanged)
    def valid(self):
        """The cell belongs to a page (a page with fewer than 4 controllers: blank cells)"""
        return self.page >= 0

    @Property(bool, notify=stateChanged)
    def selected(self):
        """Its page is the selected one (the encoders turn it)"""
        return self.page >= 0 and self.page == self.grid.grid.selected

    @Property(int, notify=stateChanged)
    def sectionIndex(self):
        g = self.grid.grid
        return g.pages[self.page].section_index if 0 <= self.page < len(g.pages) else 0

    @Property(str, notify=cellChanged)
    def kind(self):
        return gd.cell_kind(self.zctrl)

    @Property(bool, notify=cellChanged)
    def enabled(self):
        return self.zctrl is not None and not getattr(self.zctrl, "readonly", False)

    @Property(float, notify=cellChanged)
    def origin(self):
        return gd.cell_origin(self.zctrl)

    @Property(int, notify=cellChanged)
    def listIndex(self):
        return gd.cell_list_index(self.zctrl)[0]

    @Property(int, notify=cellChanged)
    def listCount(self):
        return gd.cell_list_index(self.zctrl)[1]

    @Property(str, notify=cellChanged)
    def gridName(self):
        return gd.cell_name(self.zctrl)

    def _select_page(self):
        """Select the cell's page (chain control's page, through the model's on_select); False
        when it has none"""
        return self.page >= 0 and self.grid.grid.select_cell(self.cell_index)

    @Slot()
    def tapped(self):
        """Select its page; then a press (toggle, trigger, list step, file selector), or while
        MIDI learning: learn it"""
        if not self._select_page():
            return
        c = self.control
        if c.midi_learning or c.note_learn:
            c.controllers[self.index].touched()
            return
        z = self.grid.grid.press(self.cell_index)
        if z is not None:
            c.zctrl_changed(z)

    @Slot(int)
    def nudge(self, steps):
        """A drag or the wheel: the model's turn (zctrl.is_dirty stays for the controller slots)"""
        z = self.grid.grid.turn(self.cell_index, steps)
        if z is not None:
            self.control.zctrl_changed(z)

    @Slot()
    def options(self):
        if self.zctrl is not None and self._select_page():
            self.control.controllers[self.index].options()

    @Slot()
    def touched(self):
        """A drag started on it: while MIDI learning, learn it (its page selected first)"""
        c = self.control
        if c.midi_learning and self.zctrl is not None and self._select_page():
            c.controllers[self.index].touched()


class ControlGridModel(QObject):
    """The grid for QML; owned by ChainControl"""

    layoutChanged = Signal()

    def __init__(self, control):
        super().__init__(control)
        self.control = control
        self.grid = gd.ControlGrid()
        self.entries = []       # page index -> chain control's page list entry
        self._cells = [GridCellProxy(i, control, self) for i in range(MAX_CELLS)]
        self.watcher = gd.ValueWatcher()    # the grid's own (chain control's slots: is_dirty)
        self.grid.on_select = self.select_page
        self.grid.add_listener(self._grid_event)

    def _grid_event(self, event, data):
        if event == "structure":
            self._sync()
            self.layoutChanged.emit()
        elif event == "state":
            for proxy in self._cells:
                proxy.stateChanged.emit()
            self.layoutChanged.emit()
        elif event == "values":
            for z in {cell.zctrl for cell in data}:
                self.control.zctrl_changed(z)

    def _sync(self):
        cells = self.grid.cells
        for i, proxy in enumerate(self._cells):
            proxy.set_cell(cells[i] if i < len(cells) else None)
        for proxy in self._cells:
            proxy.stateChanged.emit()

    def set_layout(self, name):
        if name in gd.LAYOUTS:
            self.grid.set_layout(name)

    def set_pages(self, entries, selected_entry):
        """chain control's page list (EntryModel entries): the pages (not the section rows), the
        selected one"""
        pages = []
        self.entries = []
        section, section_index = "", -1
        for row, e in enumerate(entries):
            if e["separator"]:
                section = e["title"]
                section_index += 1
                continue
            kind, proc, arg = e["data"]
            if kind == "chain":
                zctrls = arg
            elif kind == "empty":
                section = e["title"]
                section_index += 1
                zctrls = []
            else:
                try:
                    zctrls = proc.get_ctrl_screen(e["title"])
                except Exception:
                    zctrls = []
            pages.append(gd.GridPage(row, e["title"], section.title() if section.isupper() else section,
                                     max(0, section_index), zctrls, empty=(kind == "empty")))
            self.entries.append(row)
        sel = self.entries.index(selected_entry) if selected_entry in self.entries else -1
        self.grid.set_pages(pages, sel)

    def select_entry(self, entry):
        """chain control's page changed: select it here too"""
        if entry in self.entries:
            self.grid.select(self.entries.index(entry))

    def select_page(self, page):
        """A page chosen in the grid (the model's on_select): select it in chain control, which
        selects it in the model"""
        if 0 <= page < len(self.entries):
            self.control.setPage(self.entries[page])

    def poll(self):
        return self.grid.poll(self.watcher)

    def proxies_of(self, zctrl):
        return [p for p in self._cells if p.zctrl is zctrl]

    # QML

    @Property(int, notify=layoutChanged)
    def columns(self):
        return self.grid.columns

    @Property(int, notify=layoutChanged)
    def rows(self):
        return self.grid.rows

    @Property(int, notify=layoutChanged)
    def pagesPerRow(self):
        return self.grid.pages_per_row

    @Property("QVariantList", constant=True)
    def cells(self):
        return self._cells

    @Property("QVariantList", notify=layoutChanged)
    def blocks(self):
        """The window's pages, row by row (pagesPerRow a row): title, section, sectionIndex,
        selected, empty, valid (false: no page there), first (the first page of its section)"""
        g = self.grid
        out = []
        for r in range(g.rows):
            for part in range(g.pages_per_row):
                p = g.page_at(r, part)
                if p < 0:
                    out.append({"valid": False, "title": "", "section": "", "sectionIndex": 0,
                                "selected": False, "empty": False, "first": False})
                    continue
                page = g.pages[p]
                out.append({"valid": True, "title": page.title, "section": page.section,
                            "sectionIndex": page.section_index, "selected": p == g.selected,
                            "empty": page.empty,
                            "first": p == 0 or g.pages[p - 1].section_index != page.section_index})
        return out

    @Property(int, notify=layoutChanged)
    def firstRow(self):
        return self.grid.first_row

    @Property(int, notify=layoutChanged)
    def totalRows(self):
        return self.grid.total_rows

    @Property(int, notify=layoutChanged)
    def selectedRow(self):
        return self.grid.selected_row

    @Property(int, notify=layoutChanged)
    def selectedPart(self):
        return self.grid.selected_half

    @Property(int, notify=layoutChanged)
    def firstEntry(self):
        """The page list rows shown in the grid: from firstEntry to lastEntry (section rows
        between them included)"""
        p = self.grid.page_at(0, 0)
        return self.entries[p] if p >= 0 else -1

    @Property(int, notify=layoutChanged)
    def lastEntry(self):
        g = self.grid
        last = min(len(g.pages), (g.first_row + g.rows) * g.pages_per_row) - 1
        return self.entries[last] if last >= 0 else -1

    @Slot(int)
    def tapPage(self, block):
        """A tap on a page's header: select it (on the selected processor without pages: its
        banks / presets, as the page list)"""
        g = self.grid
        p = g.page_at(block // g.pages_per_row, block % g.pages_per_row)
        if p >= 0:
            self.control.pageTapped(self.entries[p])

    @Slot(int)
    def scrollRows(self, n):
        self.grid.scroll(n)

    @Slot(int)
    def scrollTo(self, first):
        self.grid.scroll_to(first)
