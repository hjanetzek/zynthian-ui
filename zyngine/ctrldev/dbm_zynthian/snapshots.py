# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian Control Device Driver
#
# DrivenByMoss on zynthian: zynthian's ZS3s as the host's snapshots
#
# Copyright (C) 2026 Hannes Janetzek
#
# ******************************************************************************
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

"""zynthian's ZS3s as the host's snapshots (the core's ``snapshots`` feature, area 0x0E / 0x8E;
HOST_BRIDGE_GUIDE §4.14): the Maschine JAM's snapshot view (Select + SONG) shows them on its
8x8 pads.

**The mapping: by program number.** Slot i (pad i, 0..63) is the ZS3 bound to MIDI program
change i on any channel, the id ``*/i``: the one the internal program change i recalls, and the
one an external program change i on any channel falls back to (``state_manager.load_zs3``'s
fallback, when no ``C/i`` ZS3 of that channel exists). So the pad and program change i recall the
same ZS3, and a ZS3 stored on pad i is recalled by program change i.

- ZS3s without a program number (``zs3-N``: "Save as new ZS3" on zynthian's screen) and the
  channel bound ones (``C/P``, MIDI learn on a channel) are not on the grid.
- The default state ``zs3-0`` (what the snapshot starts with) is not program 0: program 0 is
  ``*/0``, pad 0; ``zs3-0`` is on no pad.
- Programs 64..127 exist but are off the grid (the window is the first 64; paging later).

**Reports** (change-only through the reporter's ``put``, subtree ``"snapshots"``): ``count`` 128
(the program range: the number of slots, not of ZS3s), ``appendOnly`` false (every empty pad is a
store target), ``active`` the program of the last loaded or stored ZS3 if it is a ``*/P`` one,
else -1; for the 64 slots ``exists`` and ``name`` (the ZS3's title, "" for an empty one). No
colours (``SnapshotColor`` is not reported: zynthian's ZS3s have none).

**Commands** (by slot, resolved to the id at command time; ignored while zynthian is busy, e.g.
loading a snapshot, and outside 0..127): ``load`` = CUIA ``ZS3_LOAD */i`` (if it exists),
``store`` = ``ZS3_SAVE */i`` (overwrites without asking, as zynthian's "Update", keeping title,
note and restore flags; a new one gets ``save_zs3``'s title ``ZS3-N``), ``remove`` =
``ZS3_DELETE */i`` (no confirmation). The CUIAs run in zynthian's UI thread (the CUIA queue):
loading and saving touch the chains, the autoconnect and zynseq.

The protocol's names are guarded (``getattr``): with a binding without them nothing is reported
and the commands stay undeclared (commands.py).
"""

import logging

from dbm_host.reporter import M

logger = logging.getLogger("dbm_zynthian")

WINDOW = 64
"""The slots the core shows (the bank window, offset 0)."""
PROGRAMS = 128
"""The slots there are: MIDI programs 0..127."""

SNAPSHOT_COUNT = getattr(M, "SNAPSHOT_COUNT", None)
SNAPSHOT_ACTIVE = getattr(M, "SNAPSHOT_ACTIVE", None)
SNAPSHOT_APPEND_ONLY = getattr(M, "SNAPSHOT_APPEND_ONLY", None)
SNAPSHOT_EXISTS = getattr(M, "SNAPSHOT_EXISTS", None)
SNAPSHOT_NAME = getattr(M, "SNAPSHOT_NAME", None)


def has_reports():
    """The binding has the snapshot reports"""
    return all(r is not None for r in (SNAPSHOT_COUNT, SNAPSHOT_ACTIVE, SNAPSHOT_APPEND_ONLY, SNAPSHOT_EXISTS, SNAPSHOT_NAME))


def zs3_id(slot):
    """The ZS3 id of a slot: program change ``slot`` on any channel"""
    return f"*/{slot}"


def slot_of(zs3_id):
    """The slot of a ZS3 id (``*/P``: P), None for any other id"""
    if not isinstance(zs3_id, str) or not zs3_id.startswith("*/"):
        return None
    try:
        prog = int(zs3_id[2:])
    except ValueError:
        return None
    return prog if 0 <= prog < PROGRAMS else None


class ZynSnapshots:
    """zynthian's ZS3s as the host's snapshots (the module's doc)"""

    def __init__(self):
        self.state_manager = None
        """zynthian's state manager (its ``zs3`` dict, ``last_zs3_id``, ``send_cuia``,
        ``is_busy``), set by the driver; None: no snapshots."""
        self._keys = [(SNAPSHOT_EXISTS | slot << 16, SNAPSHOT_NAME | slot << 16) for slot in range(WINDOW)] \
            if has_reports() else []
        self.ignored = 0
        """Commands ignored (busy, out of range, nothing to load or remove; tests)."""

    @property
    def available(self):
        return self.state_manager is not None and hasattr(self.state_manager, "zs3")

    # The reports

    def titles(self):
        """{slot: title} of the program-bound ZS3s (``*/P``), read from zynthian's dict (a
        copy: the UI thread changes it)"""
        for _ in range(3):
            try:
                items = list(self.state_manager.zs3.items())
                break
            except RuntimeError:
                # Changed while copying: again
                continue
        else:
            return None
        titles = {}
        for id_, state in items:
            slot = slot_of(id_)
            if slot is not None:
                try:
                    titles[slot] = str(state.get("title", "") or "")
                except AttributeError:
                    titles[slot] = ""
        return titles

    def collect(self, put):
        """The reports (the module's doc)"""
        if not self.available or not self._keys:
            return
        titles = self.titles()
        if titles is None:
            return
        put(SNAPSHOT_APPEND_ONLY, False)
        put(SNAPSHOT_COUNT, PROGRAMS)
        for slot, (exists, name) in enumerate(self._keys):
            title = titles.get(slot)
            put(exists, title is not None)
            put(name, title or "")
        active = slot_of(getattr(self.state_manager, "last_zs3_id", None))
        put(SNAPSHOT_ACTIVE, active if active is not None and active in titles else -1)

    # The commands

    def _command(self, slot):
        """The ZS3 id of a command's slot, None if the command is to be ignored"""
        sm = self.state_manager
        try:
            slot = int(slot)
        except (TypeError, ValueError):
            slot = -1
        busy = False
        try:
            busy = bool(sm.is_busy())
        except AttributeError:
            pass
        if sm is None or busy or not 0 <= slot < PROGRAMS:
            self.ignored += 1
            return None
        return zs3_id(slot)

    def _exists(self, id_):
        try:
            return id_ in self.state_manager.zs3
        except Exception:
            return False

    def load(self, slot):
        id_ = self._command(slot)
        if id_ is None:
            return False
        if not self._exists(id_):
            self.ignored += 1
            return False
        self.state_manager.send_cuia("ZS3_LOAD", [id_])
        return True

    def store(self, slot):
        id_ = self._command(slot)
        if id_ is None:
            return False
        self.state_manager.send_cuia("ZS3_SAVE", [id_])
        return True

    def remove(self, slot):
        id_ = self._command(slot)
        if id_ is None:
            return False
        if not self._exists(id_):
            self.ignored += 1
            return False
        self.state_manager.send_cuia("ZS3_DELETE", [id_])
        return True
