"""Choosing a file (zynthian_gui_file_selector) in the options screen: the directories for the
file types (user files, collections, system files, USB storage), their subdirectories and files.

    FilePicker(ui).pick("Import MIDI file", ["mid"], action, path=last_file)
"""

import os

from zyngine.zynthian_engine import zynthian_engine
from zyngui.zynthian_file_data import root_dirnames, root_dirs


class FilePicker:

    def __init__(self, ui):
        self.ui = ui
        self.title = ""
        self.fexts = []
        self.action = None
        self.roots = []

    def pick(self, title, fexts, action, path=None):
        """Show the files with these extensions; action(path) for the chosen one. path: a file
        to start at (its directory, selected)"""
        self.title = title
        self.fexts = [f.lower() for f in fexts]
        self.action = action
        self.roots = root_dirs(root_dirnames(self.fexts))
        dirpath = os.path.dirname(path) if path and os.path.isfile(path) else None
        if dirpath and os.path.isdir(dirpath):
            self._show_dir(dirpath, path)
        else:
            self._show_roots()

    def _is_root(self, dirpath):
        return any(os.path.normpath(dirpath) == os.path.normpath(p) for _, p in self.roots)

    def _show_roots(self, selected_path=None):
        rows = zynthian_engine.get_dir_file_list(fexts=self.fexts, root_dirs=self.roots, recursion=1)
        opts = []
        selected = 0
        for row in rows:
            path, title = row[0], row[2]
            if path is None:
                opts.append((title, None, None, None))      # heading
                continue
            if path == selected_path:
                selected = len(opts)
            opts.append(self._option(path, title))
        if not any(action for _, action, _, _ in opts):
            opts.append((f"No {', '.join(self.fexts)} files", None, None, None))
        self.ui.show_options(self.title, opts, selected)

    def _show_dir(self, dirpath, selected_path=None):
        parent = os.path.dirname(dirpath)
        up = (lambda: self._show_roots(dirpath)) if self._is_root(dirpath) or not parent \
            else (lambda: self._show_dir(parent, dirpath))
        opts = [("‹ Back", up, None, None)]
        selected = 0
        for row in zynthian_engine.get_filelist(dirpath, self.fexts, include_dirs=True):
            if row[0] == selected_path:
                selected = len(opts)
            opts.append(self._option(row[0], row[2]))
        self.ui.show_options(f"{self.title}: {os.path.basename(dirpath)}", opts, selected)

    def _option(self, path, title):
        if os.path.isdir(path):
            return (title, lambda: self._show_dir(path), None, None)
        return (title, lambda: self.action(path), None, None)
