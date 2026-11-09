"""Options list (zynthian_gui_option) and snapshots (zynthian_gui_snapshot, with the file logic
shared through zynthian_snapshot_files)"""

import logging
import os
import shutil
from glob import escape as glob_escape, glob
from os.path import dirname, isdir, isfile, splitext

from zyngine.zynthian_snapshot_files import zynthian_snapshot_files
from zynqt.screens.base import SelectorScreen, entry, separator
from zynqt.screens.chain_screens import list_data_entries


class Options(SelectorScreen):
    """A list of options, each with its own action: config(), then show the screen"""

    name = "option"

    def __init__(self, ui, parent=None):
        super().__init__(ui, parent)
        self._options_title = ""
        self._options = []
        self._options_selected = 0

    def config(self, title, options, selected=0):
        """options: list of (label, action, info, icon), action None for a heading; the screen closes
        before the action runs"""
        self._options_title = title
        self._options = options
        self._options_selected = selected

    def fill(self):
        self.set_title(self._options_title)
        self.set_entries([entry(label, action, info=info or "", icon=icon or "") if action else separator(label)
                          for label, action, info, icon in self._options], self._options_selected)

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

    def show_menu(self):
        """MENU: the selected entry's options (Tk's show_menu: bold select)"""
        self.activate(self._index, "B")

    def select_action(self, index, t):
        sm = self.state_manager
        row = self.entries[index]["data"]
        fpath, title = row[0], row[2]
        if fpath == "NEW_BANK":
            self.ui.show_keyboard(self.new_bank, "", "New bank name")
        elif fpath == "SAVE":
            self.ui.show_keyboard(self.save_new, "New Snapshot", "Snapshot name")
        elif isdir(fpath):
            if fpath == sm.snapshot_dir:
                sm.snapshot_bank = None
            elif t == "B":
                self.show_bank_options(title)
                return
            else:
                sm.snapshot_bank = title
            self.fill()
        elif fpath:
            self.show_options(fpath, title, title == "Last State")

    def show_options(self, fpath, title, restricted):
        options = [
            ("Load", lambda: self.load(fpath), "Load full snapshot", "snapshot.png"),
            ("Load Replace Chains", lambda: self.load(fpath, load_sequences=False),
             "Load chains from snapshot, replacing current state.", "snapshot_chains.png"),
            ("Load Merge Chains", lambda: self.load(fpath, load_sequences=False, merge=True),
             "Load chains from snapshot, merging with current state.", "snapshot_chains.png"),
            ("Load Replace Sequences", lambda: self.load(fpath, load_chains=False),
             "Load sequences from snapshot, replacing current state", "snapshot_sequences.png"),
            ("Save Overwriting", lambda: self.save(fpath),
             "Save current state, overwriting this snapshot.", "snapshot_overwrite.png"),
        ]
        budir = dirname(fpath) + "/.backup"
        if isdir(budir):
            options.append(("Restore Backup", lambda: self.show_backups(fpath, title),
                            "Restore snapshot from a backup copy", "snapshot.png"))
        if not restricted:
            parts = self.files.get_parts_from_path(fpath)
            options += [
                ("Rename", lambda: self.ui.show_keyboard(lambda name: self.rename(fpath, name),
                                                          parts[1] if parts else "", "Rename snapshot"),
                 "Rename snapshot", "rename.png"),
                ("Set Program", lambda: self.pick_program(fpath), "Assign a MIDI program number", "settings.png"),
                ("Delete", lambda: self.ui.confirm(f"Do you really want to delete '{title}'?",
                                                   lambda: self.delete(fpath)),
                 "Delete snapshot", "snapshot_delete.png"),
            ]
        self.ui.show_options(title, options)

    def show_bank_options(self, bank):
        """Bold select on a bank (zynthian_gui_snapshot.show_bank_options)"""
        sm = self.state_manager
        if not isdir(f"{sm.snapshot_dir}/{bank}"):
            return
        n = len(glob(f"{sm.snapshot_dir}/{bank}/*.zss"))
        options = [
            ("Delete Bank", lambda: self.ui.confirm(
                f"Do you really want to delete bank {bank} with {n} snapshots", lambda: self.delete_bank(bank)),
             "Delete Bank", "folder_delete.png"),
            ("Rename Bank", lambda: self.ask_bank_name(bank), None, None),
        ]
        self.ui.show_options(bank, options)

    def delete_bank(self, bank):
        sm = self.state_manager
        try:
            shutil.rmtree(f"{sm.snapshot_dir}/{bank}")
            if sm.snapshot_bank == bank:
                sm.snapshot_bank = None
        except Exception as e:
            logging.warning(f"Failed to delete snapshot bank {bank}: {e}")
        self.fill()

    def ask_bank_name(self, bank):
        prog, _, name = bank.partition("-")

        def rename(new_name):
            sm = self.state_manager
            new_path = f"{sm.snapshot_dir}/{prog}-{new_name}" if new_name else f"{sm.snapshot_dir}/{prog}"
            try:
                os.rename(f"{sm.snapshot_dir}/{bank}", new_path)
                if sm.snapshot_bank == bank:
                    sm.snapshot_bank = os.path.basename(new_path)
            except Exception as e:
                logging.warning(f"Failed to rename snapshot bank: {e}")
            self.fill()
        self.ui.show_keyboard(rename, name, "Rename bank")

    def show_backups(self, fpath, title):
        """Restore Backup: the snapshot's backups (option.config_file_list), newest first"""
        parts = self.files.get_parts_from_path(fpath)
        budir = dirname(fpath) + "/.backup"
        fbase = splitext(parts[2])[0] if parts else ""
        files = sorted(glob(f"{budir}/{glob_escape(fbase)}.*.zss"), reverse=True)
        options = [(os.path.basename(f), lambda f=f: self.load(f), None, None) for f in files]
        if not options:
            options = [("No backups", None, None, None)]
        self.ui.show_options(f"Restore backup: {title}", options)

    def pick_program(self, fpath):
        """Set Program (Tk: the midi_prog screen): None or 0..127; files with that program and
        the following ones move up to the next free program, as zynthian_gui_snapshot.set_program"""
        parts = self.files.get_parts_from_path(fpath)
        current = parts[0] if parts and isinstance(parts[0], int) else -1
        choices = [("None", -1)] + [(str(i), i) for i in range(128)]
        selected = next((i for i, (_, v) in enumerate(choices) if v == current), 0)
        self.ui.show_options("MIDI Program", [(label, lambda v=v: self.set_program(fpath, v), None, None)
                                              for label, v in choices], selected)

    def set_program(self, fpath, program):
        parts = self.files.get_parts_from_path(fpath)
        if parts is None:
            return
        parts[0] = program if 0 <= program <= 127 else None
        dfpath = self.files.get_path_from_parts(parts)
        to_change = []
        if parts[0] is not None:
            path = self.files.get_snapshot_fpath("")
            first_gap = program
            for filename in sorted(os.listdir(path)):
                dparts = self.files.get_parts_from_path(path + filename)
                if dparts is None or dparts[0] is None or dparts[0] < program or dparts[3] == parts[3]:
                    continue
                if dparts[0] > first_gap:
                    break
                dparts[0] += 1
                first_gap = dparts[0]
                to_change.append([dparts[3], self.files.get_path_from_parts(dparts)])

        def do():
            try:
                for src, dst in sorted(to_change, reverse=True):
                    os.rename(src, dst)
                os.rename(fpath, dfpath)
            except Exception as e:
                logging.warning(f"Failed to set program for snapshot {fpath}: {e}")
            self.fill()
        if to_change:
            self.ui.confirm(f"Do you want to move {len(to_change)} snapshots up to next available program?", do)
        else:
            do()

    # Actions

    def _save_last_state(self, fpath):
        if self.files.is_not_empty_snapshot() and fpath != self.state_manager.last_state_snapshot_fpath:
            self.state_manager.save_last_state_snapshot()

    def load(self, fpath, load_sequences=True, merge=False, load_chains=True):
        sm = self.state_manager

        def task():
            self._save_last_state(fpath)
            return sm.load_snapshot(fpath, load_chains=load_chains, load_sequences=load_sequences, merge=merge)

        def done(state):
            if state is None and load_chains:
                self.ui.show_info("Failed to load snapshot")
            # Tk: the launcher after loading the sequences only
            self.ui.show_screen_reset("mixer" if load_chains else "launcher")

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
