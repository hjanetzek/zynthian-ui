# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian Engine
#
# Snapshot files: banks (directories), names and MIDI program numbers, and the
# lists the snapshot screens show. UI-independent, used by the Tk and Qt UIs.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

import os
import logging
from glob import glob
from os.path import isfile, isdir, join, basename


class zynthian_snapshot_files:
    """Snapshot files of a state manager (snapshot_dir, snapshot_bank, ...).

    File names: "[program-]name.zss", program a MIDI program number 000..127; ">" and "/" in
    names are stored as ";". Banks are directories "NNN[-name]" in snapshot_dir; with a single
    bank ("bankless mode") its snapshots are listed directly.
    """

    def __init__(self, state_manager):
        self.sm = state_manager
        self.cm = state_manager.chain_manager
        self.bankless_mode = False

    def is_not_empty_snapshot(self):
        return self.cm.get_chain_count() > 1 or self.cm.get_processor_count() > 0

    def check_bankless_mode(self):
        """Create the first bank if there is none, select the only bank if there is one.
        Returns True in bankless mode (a single bank)."""
        bank_dirs = [d for d in os.listdir(self.sm.snapshot_dir)
                     if d[0] != "." and isdir(join(self.sm.snapshot_dir, d))]
        if len(bank_dirs) == 0:
            os.makedirs(f"{self.sm.snapshot_dir}/000")
            self.bankless_mode = True
        elif len(bank_dirs) == 1:
            self.bankless_mode = True
            self.sm.snapshot_bank = bank_dirs[0]
        else:
            self.bankless_mode = False
        return self.bankless_mode

    @staticmethod
    def get_midi_number(f):
        try:
            return int(f.split('-')[0])
        except:
            return None

    def get_snapshot_fpath(self, f):
        if f in ["last_state.zss", "default.zss"]:
            return join(self.sm.snapshot_dir, f)
        return join(self.sm.snapshot_dir, self.sm.snapshot_bank, f)

    def get_next_program(self, offset):
        """Get the next available program number
        offset : Minimum program number to return
        Returns : Next available program mumber as integer or None if none available
        """
        files = os.listdir(self.get_snapshot_fpath(''))
        files.sort()
        for filename in files:
            if offset > 127:
                return None
            program = self.get_midi_number(filename)
            if type(program) != int:
                continue
            if program < offset:
                continue
            if program == offset:
                offset += 1
        return offset

    @staticmethod
    def get_parts_from_path(path):
        """Get an list of parts of a snapshot filename

        path : Full path and filename of snapshot file
        Returns : List of parts: [program, display name, filename, path] or None for invalid path
        """
        if path[-4:].lower() != '.zss':
            return None
        filename = os.path.basename(path)
        name = filename[:-4].replace(';', '>', 1).replace(';', '/')
        # Check if prefix is program-
        try:
            program = int(filename.split('-')[0])
            name = name.split('-', 1)[1]
        except:
            program = None
        return [program, name, filename, path]

    def get_path_from_parts(self, parts):
        """Get full path and filename from parts

        parts : List of parts [program, display name, filename, path]
        returns : Valid filename or None if invalid parts
        """
        if type(parts) != list or len(parts) != 4:
            return None
        name = parts[1] + '.zss'
        if type(parts[0]) == int and 0 <= parts[0] < 128:
            name = format(parts[0], "03") + '-' + name
        return self.get_snapshot_fpath(name.replace('>', ';').replace('/', ';'))

    # Lists, as rows [value, index, title, (info, icon)] (zynthian_gui_selector's list_data)

    def bank_list(self, index=0):
        """Banks, with Default, Last State and New Bank first. Returns (rows, index of the
        current bank or the given index, number of rows before the banks)."""
        rows = []
        if isfile(self.sm.default_snapshot_fpath):
            rows.append([self.sm.default_snapshot_fpath, len(rows), "Default", ["Default snapshot", "snapshot_default.png"]])
        if isfile(self.sm.last_state_snapshot_fpath):
            rows.append([self.sm.last_state_snapshot_fpath, len(rows), "Last State", ["Last state snapshot", "snapshot_default.png"]])
        rows.append(["NEW_BANK", len(rows), "New Bank", ["Create an empty bank", "folder_new.png"]])
        offset = len(rows)
        for dpath in sorted(glob(f"{self.sm.snapshot_dir}/[0-9][0-9][0-9]*")):
            if isdir(dpath):
                bank_name = basename(dpath)
                if bank_name.startswith('.'):
                    continue
                rows.append([dpath, len(rows), bank_name])
                if self.get_midi_number(bank_name) is None:
                    logging.warning(f"Snapshot Bank '{bank_name}' don't have a MIDI bank number")
                if bank_name == self.sm.snapshot_bank:
                    index = len(rows) - 1
        return rows, index, offset

    def snapshot_list(self, index=0):
        """Snapshots of the current bank (with "..", "Save as new snapshot", ... first).
        Returns (rows, index of the last loaded snapshot or the given index, number of rows
        before the snapshots)."""
        rows = []
        if not self.bankless_mode:
            rows.append([self.sm.snapshot_dir, len(rows), ".."])
        if self.is_not_empty_snapshot():
            # TODO: Add better validation of populated state, e.g. sequences
            rows.append(["SAVE", len(rows), "Save as new snapshot", ["Save current state as new snapshot", "snapshot_new.png"]])
        if self.bankless_mode:
            rows.append(["NEW_BANK", len(rows), "New Bank", ["Create an empty bank", "folder_new.png"]])
            rows.append([None, None, "> Saved snapshots:"])
            if isfile(self.sm.default_snapshot_fpath):
                rows.append([self.sm.default_snapshot_fpath, len(rows), "Default", ["Default snapshot", "snapshot_default.png"]])
            if isfile(self.sm.last_state_snapshot_fpath):
                rows.append([self.sm.last_state_snapshot_fpath, len(rows), "Last State", ["Last state snapshot", "snapshot_default.png"]])
        offset = len(rows)
        for fpath in sorted(glob(f"{self.sm.snapshot_dir}/{self.sm.snapshot_bank}/*.zss")):
            if isfile(fpath):
                title = basename(fpath)[:-4].replace(';', '>', 1).replace(';', '/')
                rows.append([fpath, len(rows), title])
                if fpath == self.sm.last_snapshot_fpath:
                    index = len(rows) - 1
        return rows, index, offset

    # Changes

    def new_bank(self, title):
        """Create a bank numbered after the highest one; select it. Returns its name or None."""
        numbers = [self.get_midi_number(basename(d)) for d in glob(f"{self.sm.snapshot_dir}/[0-9][0-9][0-9]*")]
        full_title = f"{max([n for n in numbers if n is not None], default=0) + 1:03d}"
        if title:
            full_title = f"{full_title}-{title}"
        try:
            os.mkdir(join(self.sm.snapshot_dir, full_title))
            self.sm.snapshot_bank = full_title
            return full_title
        except Exception as e:
            logging.warning(f"Failed to create new snapshot bank: {e}")
            return None

    def new_snapshot_fpath(self, name):
        """Path for a new snapshot called name in the current bank, with the next program"""
        program = self.get_next_program(1)
        if type(program) == int and program < 128:
            name = format(program, "03") + "-" + name
        return self.get_snapshot_fpath(name.replace('>', ';').replace('/', ';')) + '.zss'

    def rename_fpath(self, fpath, new_name):
        """Path of fpath renamed to new_name (keeping its program), None if invalid"""
        parts = self.get_parts_from_path(fpath)
        if parts is None:
            return None
        if type(parts[0]) == int and parts[0] < 128:
            new_name = format(parts[0], "03") + '-' + new_name
        new_path = self.get_snapshot_fpath(new_name.replace('>', ';').replace('/', ';'))
        if new_path[-4:].lower() != '.zss':
            new_path += '.zss'
        return new_path
