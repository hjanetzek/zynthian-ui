"""Selector screens of the Qt UI: a list (with an info pane) or a grid of entries.

A screen fills its entries in fill() when it is shown and acts on them in select_action(), as
zynthian_gui_selector's subclasses do; the QML side (SelectorScreen.qml) only shows them. Entries
are dicts:

    title      text in the list or on the tile
    info       text for the info pane (lists)
    icon       file name in zynthian-ui's icons/ or an absolute path ("" for none)
    separator  True for a section title, which can't be selected
    enabled    False shows it greyed out (e.g. not ported to the Qt UI yet)
    data, action: for the screen's own use (action: called with the entry on selection)
"""

import logging
import os

from PySide6.QtCore import (QAbstractListModel, QModelIndex, QObject, QUrl, Qt, Property, Signal,
                            Slot)

from zynconf import zynthian_paths

NOT_PORTED = "Not in the Qt UI yet."


def icon_url(icon):
    if not icon:
        return ""
    path = icon if os.path.isabs(icon) else os.path.join(zynthian_paths.ui_dir, "icons", icon)
    return QUrl.fromLocalFile(path).toString() if os.path.isfile(path) else ""


def entry(title, action=None, info="", icon="", separator=False, enabled=True, data=None):
    return {"title": title, "action": action, "info": info, "icon": icon, "separator": separator,
            "enabled": enabled, "data": data}


def separator(title):
    return entry(title, separator=True)


def placeholder():
    """An empty cell of a grid (drawn darkened, not selectable: a separator without title)"""
    return entry("", separator=True)


def fill_grid(entries, cells=16):
    """entries padded with placeholders to cells (a full 4x4 grid)"""
    return entries + [placeholder() for _ in range(max(0, cells - len(entries)))]


class EntryModel(QAbstractListModel):
    TitleRole, InfoRole, IconRole, SeparatorRole, EnabledRole = range(Qt.UserRole + 1, Qt.UserRole + 6)
    _ROLES = {TitleRole: b"title", InfoRole: b"info", IconRole: b"icon",
              SeparatorRole: b"separator", EnabledRole: b"entryEnabled"}

    countChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.entries = []

    @staticmethod
    def _shown_fields(e):
        return (e["title"], e["info"], e["icon"], e["separator"], e["enabled"])

    def set_entries(self, entries):
        entries = list(entries)
        if len(entries) == len(self.entries):
            # Same number of entries: update in place, so the views keep their delegates (a reset
            # recreates them all, with their images: ~200 ms for the main menu grid on the Duet)
            changed = [i for i, (a, b) in enumerate(zip(self.entries, entries))
                       if self._shown_fields(a) != self._shown_fields(b)]
            self.entries = entries
            for i in changed:
                self.dataChanged.emit(self.index(i), self.index(i))
            return
        self.beginResetModel()
        self.entries = entries
        self.endResetModel()
        self.countChanged.emit()

    def update_entry(self, row, entry):
        if 0 <= row < len(self.entries):
            self.entries[row] = entry
            i = self.index(row)
            self.dataChanged.emit(i, i)

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.entries)

    @Property(int, notify=countChanged)
    def count(self):
        return len(self.entries)

    def roleNames(self):
        return self._ROLES

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.entries):
            return None
        e = self.entries[index.row()]
        if role == self.TitleRole:
            return e["title"]
        if role == self.InfoRole:
            return e["info"]
        if role == self.IconRole:
            return icon_url(e["icon"])
        if role == self.SeparatorRole:
            return e["separator"]
        if role == self.EnabledRole:
            return e["enabled"]
        return None


class SelectorScreen(QObject):
    """Base of list and grid screens. Subclasses set name, kind, columns and implement fill()."""

    name = ""
    kind = "list"       # "list" (with info pane) or "grid"
    columns = 4         # grid only

    titleChanged = Signal()
    indexChanged = Signal()
    categoriesChanged = Signal()

    def __init__(self, ui, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.state_manager = ui.state_manager
        self.chain_manager = ui.chain_manager
        self.model = EntryModel(self)
        self._title = ""
        self._index = 0
        self._categories = []
        self._category_index = 0

    # Building (when shown)

    def build(self):
        """Called by ZynUI when the screen is shown"""
        self.fill()

    def fill(self):
        raise NotImplementedError

    def set_entries(self, entries, index=None):
        self.model.set_entries(entries)
        if index is None:
            index = self._index
        index = self._first_selectable(index)
        if index == self._index:
            self.indexChanged.emit()   # same index, other entry
            self.selection_changed()
        else:
            self.set_index(index)

    @property
    def entries(self):
        return self.model.entries

    def _first_selectable(self, index):
        entries = self.model.entries
        index = max(0, min(index, len(entries) - 1))
        for i in list(range(index, len(entries))) + list(range(index - 1, -1, -1)):
            if not entries[i]["separator"]:
                return i
        return 0

    # Properties for QML

    def _get_kind(self):
        return self.kind

    def _get_columns(self):
        return self.columns

    viewKind = Property(str, _get_kind, constant=True)
    gridColumns = Property(int, _get_columns, constant=True)

    @Property(QObject, constant=True)
    def entryModel(self):
        return self.model

    @Property(str, notify=titleChanged)
    def title(self):
        return self._title

    def set_title(self, title):
        if title != self._title:
            self._title = title
            self.titleChanged.emit()

    @Property(int, notify=indexChanged)
    def index(self):
        return self._index

    def set_index(self, index):
        if index != self._index:
            self._index = index
            self.indexChanged.emit()
            self.selection_changed()

    def _current(self):
        entries = self.model.entries
        return entries[self._index] if 0 <= self._index < len(entries) else None

    @Property(str, notify=indexChanged)
    def currentInfo(self):
        e = self._current()
        return e["info"] if e else ""

    @Property(str, notify=indexChanged)
    def currentIcon(self):
        e = self._current()
        return icon_url(e["icon"]) if e else ""

    def selection_changed(self):
        """Selection moved (override to update things that depend on it)"""

    @Property("QStringList", notify=categoriesChanged)
    def categories(self):
        return self._categories

    @Property(int, notify=categoriesChanged)
    def categoryIndex(self):
        return self._category_index

    def set_categories(self, categories, index=0):
        self._categories = list(categories)
        self._category_index = max(0, min(index, len(self._categories) - 1))
        self.categoriesChanged.emit()

    @Slot(int)
    def setCategory(self, index):
        if 0 <= index < len(self._categories) and index != self._category_index:
            self._category_index = index
            self.categoriesChanged.emit()
            self.category_changed()

    def category_changed(self):
        """Category selected (override)"""

    # Actions from QML and navigation

    @Slot(int)
    def setIndex(self, index):
        if 0 <= index < len(self.model.entries) and not self.model.entries[index]["separator"]:
            self.set_index(index)

    @Slot(int, str)
    def activate(self, index, t="S"):
        """Entry tapped (t: "S" short, "B" bold/long press)"""
        if not 0 <= index < len(self.model.entries):
            return
        e = self.model.entries[index]
        if e["separator"]:
            return
        self.set_index(index)
        if not e["enabled"]:
            self.ui.show_info(e["info"] or NOT_PORTED)
            return
        try:
            self.select_action(index, t)
        except Exception as ex:
            logging.exception(f"{self.name}: action on '{e['title']}' failed: {ex}")

    def select_action(self, index, t):
        """Default: call the entry's action with the entry (short press)"""
        e = self.model.entries[index]
        if t == "S" and callable(e["action"]):
            e["action"](e)

    def move(self, step):
        entries = self.model.entries
        i = self._index + step
        while 0 <= i < len(entries) and entries[i]["separator"]:
            i += 1 if step > 0 else -1
        if 0 <= i < len(entries):
            self.set_index(i)

    def navigate(self, what):
        """Keys and encoders: up/down/left/right/select/select_bold"""
        step = self.columns if self.kind == "grid" else 1
        if what == "up":
            self.move(-step)
        elif what == "down":
            self.move(step)
        elif what == "left":
            if self.kind == "grid":
                self.move(-1)
            elif self._categories:
                self.setCategory(self._category_index - 1)
        elif what == "right":
            if self.kind == "grid":
                self.move(1)
            elif self._categories:
                self.setCategory(self._category_index + 1)
        elif what == "select":
            self.activate(self._index, "S")
        elif what == "select_bold":
            self.activate(self._index, "B")

    def back(self):
        """BACK pressed: True if handled by the screen (e.g. leaving a sub-folder)"""
        return False
