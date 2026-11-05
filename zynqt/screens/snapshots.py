"""Options list (zynthian_gui_option) and snapshots (zynthian_gui_snapshot, with the file logic
shared through zynthian_snapshot_files)"""

import logging
import os
from os.path import isdir, isfile

from zyngine.zynthian_snapshot_files import zynthian_snapshot_files
from zynqt.screens.base import SelectorScreen, entry
from zynqt.screens.chain_screens import list_data_entries


class Options(SelectorScreen):
    """A list of options, each with its own action: config(), then show the screen"""

    name = "option"

    def __init__(self, ui, parent=None):
        super().__init__(ui, parent)
        self._options_title = ""
        self._options = []

    def config(self, title, options):
        """options: list of (label, action, info, icon); the screen closes before the action runs"""
        self._options_title = title
        self._options = options

    def fill(self):
        self.set_title(self._options_title)
        self.set_entries([entry(label, action, info=info, icon=icon)
                          for label, action, info, icon in self._options], 0)

    def select_action(self, index, t):
        if t != "S":
            return
        action = self.entries[index]["action"]
        self.ui.back()
        if callable(action):
            action()


class Snapshots(SelectorScreen):
    name = "snapshot"

    def __init__(self, ui, parent=None):
        super().__init__(ui, parent)
        self.files = zynthian_snapshot_files(self.state_manager)

    def fill(self):
        sm = self.state_manager
        self.files.check_bankless_mode()
        if sm.snapshot_bank is None:
            rows, index, _ = self.files.bank_list(self.index)
            self.set_title("Snapshots")
        else:
            rows, index, _ = self.files.snapshot_list(self.index)
            self.set_title("Snapshots" if self.files.bankless_mode else f"Snapshots > {sm.snapshot_bank}")
        self.set_entries(list_data_entries(rows, "Bold to show options."), index)

    def select_action(self, index, t):
        sm = self.state_manager
        row = self.entries[index]["data"]
        fpath, title = row[0], row[2]
        if fpath == "NEW_BANK":
            self.ui.show_keyboard(self.new_bank, "", "New bank name")
        elif fpath == "SAVE":
            self.ui.show_keyboard(self.save_new, "New Snapshot", "Snapshot name")
        elif isdir(fpath):
            sm.snapshot_bank = None if fpath == sm.snapshot_dir else title
            self.fill()
        elif fpath:
            self.show_options(fpath, title, title == "Last State")

    def back(self):
        # Inside a bank (with several banks): back to the bank list
        sm = self.state_manager
        if sm.snapshot_bank is not None and not self.files.bankless_mode:
            sm.snapshot_bank = None
            self.fill()
            return True
        return False

    def show_options(self, fpath, title, restricted):
        options = [
            ("Load", lambda: self.load(fpath), "Load full snapshot", "snapshot.png"),
            ("Load Replace Chains", lambda: self.load(fpath, load_sequences=False),
             "Load chains from snapshot, replacing current state.", "snapshot_chains.png"),
            ("Load Merge Chains", lambda: self.load(fpath, load_sequences=False, merge=True),
             "Load chains from snapshot, merging with current state.", "snapshot_chains.png"),
            ("Save Overwriting", lambda: self.save(fpath),
             "Save current state, overwriting this snapshot.", "snapshot_overwrite.png"),
        ]
        if not restricted:
            parts = self.files.get_parts_from_path(fpath)
            options += [
                ("Rename", lambda: self.ui.show_keyboard(lambda name: self.rename(fpath, name),
                                                          parts[1] if parts else "", "Rename snapshot"),
                 "Rename snapshot", "rename.png"),
                ("Delete", lambda: self.ui.confirm(f"Do you really want to delete '{title}'?",
                                                   lambda: self.delete(fpath)),
                 "Delete snapshot", "snapshot_delete.png"),
            ]
        self.ui.show_options(title, options)

    # Actions

    def _save_last_state(self, fpath):
        if self.files.is_not_empty_snapshot() and fpath != self.state_manager.last_state_snapshot_fpath:
            self.state_manager.save_last_state_snapshot()

    def load(self, fpath, load_sequences=True, merge=False):
        sm = self.state_manager

        def task():
            self._save_last_state(fpath)
            return sm.load_snapshot(fpath, load_sequences=load_sequences, merge=merge)

        def done(state):
            if state is None:
                self.ui.show_info("Failed to load snapshot")
            self.ui.show_screen_reset("mixer")

        self.ui.run_background(task, done)

    def save(self, fpath):
        sm = self.state_manager
        parts = self.files.get_parts_from_path(fpath)

        def task():
            sm.start_busy("save_snapshot", "Saving snapshot", parts[1] if parts else "")
            try:
                sm.backup_snapshot(fpath)
                sm.save_snapshot(fpath)
            finally:
                sm.end_busy("save_snapshot")

        self.ui.run_background(task, lambda result: self.ui.show_screen_reset("mixer"))

    def save_new(self, name):
        if name:
            self.save(self.files.new_snapshot_fpath(name))

    def new_bank(self, title):
        self.files.new_bank(title)
        self.fill()

    def rename(self, fpath, new_name):
        parts = self.files.get_parts_from_path(fpath)
        if not new_name or parts is None or parts[1] == new_name:
            return
        new_path = self.files.rename_fpath(fpath, new_name)

        def do_rename():
            try:
                os.rename(fpath, new_path)
            except Exception as e:
                logging.warning(f"Failed to rename snapshot '{fpath}' to '{new_path}' => {e}")
            self.fill()

        if isfile(new_path):
            self.ui.confirm(f"Do you really want to overwrite '{new_name}'?", do_rename)
        else:
            do_rename()

    def delete(self, fpath):
        logging.info(f"DELETE SNAPSHOT: {fpath}")
        try:
            os.remove(fpath)
        except Exception as e:
            logging.error(e)
        self.fill()
