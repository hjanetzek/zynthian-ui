"""File selector for path controllers (zynthian_gui_file_selector): a controller with is_path (LV2
atom:Path parameters: samplv1's sample, Neural Amp Modeler's and AIDA-X's model; Clippy's clip
file; SooperLooper's load file) asks for it with zynsigman's SS_GUI_SHOW_FILE_SELECTOR
(zynthian_controller.nudge); ZynUI.show_file_selector configures this screen and shows it.

As Tk's:
- the root list: the directories of the file types (user files, each collection's, the system's,
  USB storage), with the files directly in them; "Current (dir)" when the current file is outside
  them; it opens in the current file's directory with that file selected;
- a directory's entries: sub-directories and files; BACK goes up to the root list, then closes;
- choosing a file closes the screen and calls cb_func(path);
- preload: moving the selection applies the selected file after 200 ms (a preview), and leaving
  without a choice (BACK, another screen) puts the file back that was set when it opened.
"""

import logging
import os

from PySide6.QtCore import QTimer

from zyngine.zynthian_engine import zynthian_engine
from zyngui.zynthian_file_data import FEXT2DIRNAME, COLLECTIONS_DIR, root_dirnames, root_dirs
from zynqt.screens.base import SelectorScreen, entry, separator


class FileSelector(SelectorScreen):
    name = "file_selector"
    default_icon = "folder.png"
    preload_ms = 200    # zynthian_gui_file_selector.preload_timer_ms

    def __init__(self, ui, parent=None):
        super().__init__(ui, parent)
        self.cb_func = None
        self.fexts = []
        self.root_dirs = []
        self.collection_info = {}
        self.path = None        # the entry to select (a file or the directory left)
        self.dirpath = None     # the directory shown, None: the root list
        self.init_path = None   # the value when opened (restored on leaving after a preview)
        self.sel_path = None    # the value set last (by preloading)
        self.preload = False
        self.shown = False
        self._preload_timer = QTimer(self, singleShot=True, interval=self.preload_ms)
        self._preload_timer.timeout.connect(self.preload_file)

    # Configuration (zynthian_gui_file_selector.config)

    @staticmethod
    def get_dirpath(path):
        if path:
            if os.path.isfile(path):
                return os.path.dirname(path)
            if os.path.isdir(path):
                return path
        return None

    def config(self, cb_func, fexts=None, dirnames=None, path=None, preload=False):
        self.cb_func = cb_func
        self.preload = bool(preload)
        self.fexts = [f.lower() for f in fexts] if fexts else ["wav"]
        self.init_path = self.sel_path = self.path = path or None
        self.dirpath = self.get_dirpath(self.path)
        if dirnames is None:
            dirnames = root_dirnames(self.fexts)
        self.root_dirs = root_dirs(dirnames)
        self.collection_info = {}
        if os.path.isdir(COLLECTIONS_DIR):
            for de in os.scandir(COLLECTIONS_DIR):
                if de.is_dir():
                    self.load_collection_info(de.name)
        if self.dirpath and not self.is_confined_to_root_dirs(self.dirpath):
            self.root_dirs.append((f"Current ({os.path.basename(self.dirpath)})", self.dirpath))
        self._index = 0

    def is_confined_to_root_dirs(self, path):
        return any(path.startswith(p) for _, p in self.root_dirs)

    def is_root_dir(self, path):
        return any(path == p for _, p in self.root_dirs)

    def get_relative_path(self, path):
        for title, p in self.root_dirs:
            if len(path) > len(p) and path.startswith(p):
                return title + path[len(p):]
        return ""

    # Collections' info (info.yml: title, icon, author, license, description)

    def load_collection_info(self, dname):
        dpath = f"{COLLECTIONS_DIR}/{dname}"
        try:
            import yaml
            with open(f"{dpath}/info.yml") as fh:
                info = yaml.safe_load(fh)
            info["icon"] = f"{dpath}/{info['icon']}"
            self.collection_info[dname] = info
        except Exception as e:
            if os.path.exists(f"{dpath}/info.yml"):
                logging.error(f"Bad yaml info file for collection '{dpath}' => {e}")
            icon = ""
            try:
                for de in os.scandir(f"{dpath}/Art"):
                    if de.is_file() and os.path.splitext(de.name)[-1] in (".jpg", ".png"):
                        icon = de.path
                        break
            except OSError:
                pass
            self.collection_info[dname] = {"title": dname, "icon": icon, "author": "Unknown",
                                           "license": "Unknown", "description": ""}

    def get_collection_info(self, path):
        if path and path.startswith(COLLECTIONS_DIR + "/"):
            return self.collection_info.get(path[len(COLLECTIONS_DIR) + 1:].split("/")[0])
        return None

    # The list (zynthian_gui_file_selector.fill_list)

    def list_rows(self):
        if self.dirpath and not self.is_root_dir(self.dirpath):
            return zynthian_engine.get_filelist(self.dirpath, self.fexts, include_dirs=True)
        return zynthian_engine.get_dir_file_list(fexts=self.fexts, root_dirs=self.root_dirs, recursion=1)

    def _row_entry(self, row):
        path, title = row[0], row[2]
        colinfo = self.get_collection_info(path)
        if colinfo:
            text = ""
            if colinfo.get("author"):
                text += f"Author: {colinfo['author']}\n"
            if colinfo.get("license"):
                text += f"License: {colinfo['license']}\n"
            text += "\n" + (colinfo.get("description") or "")
            info, icon = text.strip("\n"), colinfo.get("icon") or ""
        elif len(row) == 6:
            info, icon = "", FEXT2DIRNAME.get(row[5], [None, "file.png"])[1]
        else:
            info, icon = "Folder", "folder.png"
        return entry(title, info=info, icon=icon, data=path)

    def fill(self):
        entries = []
        index = 0
        for row in self.list_rows():
            if not row[0]:
                entries.append(separator(row[2]))
                continue
            if row[0] == self.path:
                index = len(entries)
            entries.append(self._row_entry(row))
        if not any(not e["separator"] for e in entries):
            entries.append(entry(f"No {', '.join(self.fexts)} files", info="", icon="", data=None))
        rel = self.get_relative_path(self.dirpath) if self.dirpath else ""
        self.set_title(f"File Selector > {rel}" if rel else "File Selector")
        self.set_entries(entries, index)

    def build(self):
        self.shown = True
        self.fill()

    # Actions

    def enters(self, index):
        """A directory (a file is chosen: its callback runs)"""
        e = self._entry_at(index)
        return bool(e and e["data"]) and os.path.isdir(e["data"])

    def select_action(self, index, t):
        if t != "S":
            return
        path = self.entries[index]["data"]
        if path and os.path.isdir(path):
            self.path = path
            self.dirpath = path
            self.fill()
        elif path and os.path.isfile(path):
            self._preload_timer.stop()
            self.path = self.sel_path = self.init_path = path
            self.ui.close_screen()
            self.cb_func(path)
        else:
            self.ui.close_screen()

    def back(self):
        """BACK: up one directory while inside the root directories, else close (ZynUI)"""
        if self.dirpath:
            parent = os.path.dirname(self.dirpath)
            if self.is_confined_to_root_dirs(parent):
                self.path = self.dirpath
                self.dirpath = parent
                self.fill()
                return True
        return False

    def hide(self):
        """Leaving: the value it had when opened, if a preview changed it"""
        self._preload_timer.stop()
        if (self.shown and self.cb_func and self.init_path and self.sel_path != self.init_path
                and os.path.isfile(self.init_path)):
            self.sel_path = self.init_path
            self.cb_func(self.init_path)
        self.shown = False

    # Preload (preview)

    def selection_changed(self):
        if self.preload and self.shown:
            self._preload_timer.start()

    def preload_file(self):
        e = self._current()
        path = e["data"] if e else None
        if path and os.path.isfile(path) and path != self.sel_path:
            self.sel_path = path
            self.cb_func(path)
