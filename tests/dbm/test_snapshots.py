# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian Control Device Driver
#
# DrivenByMoss on zynthian: tests of zynthian's ZS3s as the host's snapshots
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

"""zynthian's ZS3s as the host's snapshots (dbm_zynthian/snapshots.py): slot i = the ZS3 of
program change i on any channel (``*/i``). The reports and the commands on a stand-in state
manager; with a binding without the snapshot names the report keys are stand-ins (the protocol's
ids), and the command records once the binding has them."""

import logging
import unittest

import zynstubs

zynstubs.install()

import drivenbymoss  # noqa: E402
from dbm_host import Banks  # noqa: E402
from drivenbymoss.protocol import Cmd  # noqa: E402
from zyngine.ctrldev.dbm_zynthian import snapshots as snapshots_module  # noqa: E402
from zyngine.ctrldev.dbm_zynthian.bridge import change_signals  # noqa: E402
from zyngine.ctrldev.dbm_zynthian.commands import SNAPSHOT_COMMANDS, ZynCommandHandler  # noqa: E402
from zyngine.ctrldev.dbm_zynthian.model import ZynthianModel  # noqa: E402
from zyngine.ctrldev.dbm_zynthian.reporter import ZynReporter  # noqa: E402
from zyngine.ctrldev.dbm_zynthian.snapshots import PROGRAMS, WINDOW, ZynSnapshots, slot_of  # noqa: E402
from zyngine.ctrldev.dbm_zynthian.views import VIEW_SNAPSHOTS, ViewsUI  # noqa: E402
from zyngine.zynthian_signal_manager import zynsigman  # noqa: E402

# The protocol's report ids (doc/HOST_BRIDGE_GUIDE.md §4.14), for a binding without them
STAND_IN_KEYS = {"SNAPSHOT_COUNT": 0x0E01, "SNAPSHOT_ACTIVE": 0x0E02, "SNAPSHOT_APPEND_ONLY": 0x0E03,
                 "SNAPSHOT_EXISTS": 0x0E10, "SNAPSHOT_NAME": 0x0E11}


def keys():
    """The report keys: the binding's, else the stand-ins (patched into snapshots.py)"""
    return {name: getattr(snapshots_module, name) or STAND_IN_KEYS[name] for name in STAND_IN_KEYS}


def state_with_zs3(*programs, others=()):
    """zynstubs' project with ZS3s */P titled "P<P>" and other ids (zs3-N, C/P)"""
    state = zynstubs.project()
    for prog in programs:
        state.zs3[f"*/{prog}"] = {"title": f"P{prog}"}
    for id_ in others:
        state.zs3[id_] = {"title": id_}
    return state


class SnapshotsTest(unittest.TestCase):

    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        self.keys = keys()
        if not snapshots_module.has_reports():
            for name, value in self.keys.items():
                setattr(snapshots_module, name, value)
                self.addCleanup(setattr, snapshots_module, name, None)

    def snapshots(self, state):
        s = ZynSnapshots()
        s.state_manager = state
        return s

    def report(self, snapshots):
        """change-only, as the reporter's put"""
        out = {}
        seen = self.__dict__.setdefault("seen", {})

        def put(k, v):
            if k not in seen or seen[k] != v:
                seen[k] = out[k] = v
        snapshots.collect(put)
        return out

    def slot(self, out, name, slot):
        return out[self.keys[name] | slot << 16]

    def test_slot_of(self):
        self.assertEqual([slot_of(i) for i in ("*/0", "*/63", "*/127", "*/128", "zs3-0", "zs3-3", "0/5", "5", None, "*/x")],
                         [0, 63, 127, None, None, None, None, None, None, None])

    def test_no_zs3(self):
        out = self.report(self.snapshots(zynstubs.project()))
        self.assertEqual(out[self.keys["SNAPSHOT_COUNT"]], PROGRAMS)
        self.assertIs(out[self.keys["SNAPSHOT_APPEND_ONLY"]], False)
        self.assertEqual(out[self.keys["SNAPSHOT_ACTIVE"]], -1)
        self.assertEqual([self.slot(out, "SNAPSHOT_EXISTS", i) for i in range(WINDOW)], [False] * WINDOW)
        self.assertNotIn(self.keys["SNAPSHOT_EXISTS"] | WINDOW << 16, out, "only the window")

    def test_program_bound_zs3s_on_their_slots(self):
        """*/P on slot P; zs3-0 (the default state), zs3-N and channel bound C/P are on none;
        programs >= 64 are off the window"""
        state = state_with_zs3(0, 5, 63, 64, 100, others=("zs3-1", "3/7", "7"))
        state.last_zs3_id = "*/5"
        out = self.report(self.snapshots(state))
        exists = [i for i in range(WINDOW) if self.slot(out, "SNAPSHOT_EXISTS", i)]
        self.assertEqual(exists, [0, 5, 63])
        self.assertEqual((self.slot(out, "SNAPSHOT_NAME", 5), self.slot(out, "SNAPSHOT_NAME", 1)), ("P5", ""))
        self.assertEqual(out[self.keys["SNAPSHOT_ACTIVE"]], 5)
        self.assertEqual(self.report(self.snapshots(state)), {}, "change-only")

    def test_active(self):
        state = state_with_zs3(2, 100, others=("zs3-1", "1/2"))
        snapshots = self.snapshots(state)
        for last, active in (("*/2", 2), ("*/100", 100), ("zs3-1", -1), ("1/2", -1), ("zs3-0", -1), (None, -1), ("*/9", -1)):
            state.last_zs3_id = last
            self.report(snapshots)
            self.assertEqual(self.seen[self.keys["SNAPSHOT_ACTIVE"]], active, last)

    def test_changes(self):
        state = state_with_zs3(1, 2)
        snapshots = self.snapshots(state)
        self.report(snapshots)
        state.zs3["*/1"]["title"] = "Verse"
        del state.zs3["*/2"]
        state.zs3["*/3"] = {"title": "New"}
        out = self.report(snapshots)
        self.assertEqual(out, {self.keys["SNAPSHOT_NAME"] | 1 << 16: "Verse", self.keys["SNAPSHOT_EXISTS"] | 2 << 16: False,
                               self.keys["SNAPSHOT_NAME"] | 2 << 16: "", self.keys["SNAPSHOT_EXISTS"] | 3 << 16: True,
                               self.keys["SNAPSHOT_NAME"] | 3 << 16: "New"})

    def test_without_state_manager_nothing(self):
        self.assertEqual(self.report(ZynSnapshots()), {})
        self.assertFalse(ZynSnapshots().available)

    def test_commands(self):
        """By program, through the CUIA queue (zynthian's UI thread)"""
        state = state_with_zs3(4)
        snapshots = self.snapshots(state)
        self.assertTrue(snapshots.load(4))
        self.assertTrue(snapshots.store(4))
        self.assertTrue(snapshots.store(9), "a new ZS3 for program 9")
        self.assertTrue(snapshots.remove(4))
        self.assertEqual(state.cuias, [("ZS3_LOAD", ["*/4"]), ("ZS3_SAVE", ["*/4"]), ("ZS3_SAVE", ["*/9"]), ("ZS3_DELETE", ["*/4"])])

    def test_ignored_commands(self):
        state = state_with_zs3(4)
        snapshots = self.snapshots(state)
        # Nothing to load or remove, out of range
        self.assertFalse(snapshots.load(5))
        self.assertFalse(snapshots.remove(5))
        self.assertFalse(snapshots.store(-1))
        self.assertFalse(snapshots.store(PROGRAMS))
        # Busy (a snapshot loading)
        state.busy.add("load snapshot")
        self.assertFalse(snapshots.load(4))
        self.assertFalse(snapshots.store(4))
        self.assertFalse(snapshots.remove(4))
        self.assertEqual((state.cuias, snapshots.ignored), ([], 7))

    def test_change_signals(self):
        signals = {(signal, subsignal) for signal, subsignal, subtrees in change_signals() if "snapshots" in subtrees}
        s = zynsigman
        self.assertLessEqual({(s.S_STATE_MAN, s.SS_LOAD_ZS3), (s.S_STATE_MAN, s.SS_SAVE_ZS3), (s.S_STATE_MAN, s.SS_LOAD_SNAPSHOT),
                              (s.S_STATE_MAN, s.SS_ZS3_LIST)}, signals)

    def test_reporter_subtree(self):
        state = state_with_zs3(1)
        model = ZynthianModel(state.chain_manager, palette=["#0000FF"], zynseq=None)
        model.zs3_snapshots = self.snapshots(state)
        banks = Banks.from_model_setup({"numTracks": 8})
        reporter = ZynReporter(model, banks)
        lines = []
        reporter.put = lambda k, v: lines.append((k, v))
        reporter.collect_subtrees({"snapshots"})
        self.assertIn((self.keys["SNAPSHOT_EXISTS"] | 1 << 16, True), lines)
        self.assertTrue(all(k & 0xFFFF in self.keys.values() for k, v in lines), "only the snapshots")


class FakeUI:
    def __init__(self, screen):
        self.current_screen = screen


class SnapshotViewTest(unittest.TestCase):

    def test_the_zs3_screen_on_entry(self):
        """Shown with TOGGLE_SCREEN (keeps the history), not SCREEN_ZS3 (program change learning);
        nothing when it is shown"""
        for screen, cuias in (("mixer", [("TOGGLE_SCREEN", ["zs3"])]), ("zs3", [])):
            state = zynstubs.project()
            model = ZynthianModel(state.chain_manager, zynseq=None)
            ui = FakeUI(screen)
            model.views.ui = ViewsUI(state, get_ui=lambda: ui)
            self.assertTrue(model.views.controller_view(VIEW_SNAPSHOTS))
            self.assertEqual(state.cuias, cuias, screen)


def handler(state, with_state_manager=True):
    model = ZynthianModel(state.chain_manager, palette=["#0000FF"], zynseq=None)
    if with_state_manager:
        model.zs3_snapshots.state_manager = state
    banks = Banks.from_model_setup({"numTracks": 8})
    commands = ZynCommandHandler(model, banks, ZynReporter(model, banks))
    commands.configure()
    return commands


@unittest.skipUnless(SNAPSHOT_COMMANDS, "the binding has no snapshot commands yet")
class SnapshotCommandsTest(unittest.TestCase):

    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def test_declared_only_with_the_state_manager(self):
        state = state_with_zs3(3)
        self.assertLessEqual(set(SNAPSHOT_COMMANDS), handler(state).handled_commands())
        self.assertFalse(set(SNAPSHOT_COMMANDS) & handler(state, False).handled_commands())
        self.assertLessEqual(set(SNAPSHOT_COMMANDS), ZynCommandHandler.UNHANDLED_COMMANDS)

    def test_records(self):
        state = state_with_zs3(3)
        commands = handler(state)
        lines = ["noArg\tsnapshot\t3/load", "noArg\tsnapshot\t7/store", "noArg\tsnapshot\t3/remove", "noArg\tsnapshot\t8/load"]
        commands.process_commands(drivenbymoss.messages_from_text("\n".join(lines)))
        self.assertEqual(state.cuias, [("ZS3_LOAD", ["*/3"]), ("ZS3_SAVE", ["*/7"]), ("ZS3_DELETE", ["*/3"])])
        self.assertEqual(Cmd.SNAPSHOT_LOAD in commands.handled_commands(), True)


JAM = "72F32A83-A697-446B-9016-64AA3F9476E4"
SELECT, SONG, CLEAR = 50, 30, 33
SHIFT_DOWN = bytes.fromhex("F0002109" "1500" "4D5000014D01F7")
SHIFT_UP = bytes.fromhex("F0002109" "1500" "4D5000014D00F7")


@unittest.skipUnless(SNAPSHOT_COMMANDS, "the binding has no snapshot commands yet")
class JamSnapshotsTest(unittest.TestCase):
    """The Maschine JAM in the core: Select + SONG, the pads on zynthian's ZS3s"""

    def setUp(self):
        import tempfile
        from zyngine.ctrldev.dbm_zynthian.bridge import ZynBridge
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        self.state = state_with_zs3(0, 3, 70, others=("zs3-1",))
        self.state.last_zs3_id = "*/3"
        self.ui = FakeUI("mixer")
        model = ZynthianModel(self.state.chain_manager, palette=["#0000FF"], zynseq=None)
        model.views.ui = ViewsUI(self.state, get_ui=lambda: self.ui)
        model.zs3_snapshots.state_manager = self.state
        self.temp = tempfile.TemporaryDirectory(prefix="dbm-zynthian-snapshots-")
        self.addCleanup(self.temp.cleanup)
        self.midi_out = []
        self.bridge = ZynBridge(model, JAM, self.temp.name, "zynthian", midi_sink=self.midi_out.append)
        self.bridge.start()
        self.addCleanup(self.bridge.close)
        self.bridge.wait_for_startup()
        self.advance(1100)

    def advance(self, ms):
        for _ in range(0, ms, 10):
            self.bridge.advance(10)

    def cc(self, control, value):
        self.bridge.receive(bytes([0xB0, control, value]))

    def pad(self, slot):
        """Pad of slot (row by row from the upper left)"""
        x, y = slot % 8, slot // 8
        note = 36 + (7 - y) * 8 + x
        self.bridge.receive(bytes([0x90, note, 127]))
        self.advance(20)
        self.bridge.receive(bytes([0x80, note, 0]))
        self.advance(20)

    def led(self, slot):
        x, y = slot % 8, slot // 8
        note = 36 + (7 - y) * 8 + x
        return next((m[2] for m in reversed(self.midi_out) if len(m) == 3 and m[0] & 0xF0 == 0x90 and m[1] == note), None)

    def cuias(self):
        cuias, self.state.cuias[:] = list(self.state.cuias), []
        return cuias

    def enter(self):
        for control, value in ((SELECT, 127), (SONG, 127), (SONG, 0), (SELECT, 0)):
            self.cc(control, value)
        self.advance(200)

    def test_snapshot_view(self):
        self.enter()
        self.assertIn("Snapshots", self.bridge.take_notifications())
        self.assertEqual(self.cuias(), [("TOGGLE_SCREEN", ["zs3"])], "the ZS3 screen")
        # Stored pads lit, the active one (*/3) different, the empty ones off
        lit = [slot for slot in range(WINDOW) if self.led(slot)]
        self.assertEqual(lit, [0, 3])
        self.assertNotEqual(self.led(0), self.led(3))
        # Pad: load; an empty pad: nothing
        self.pad(0)
        self.pad(5)
        self.assertEqual(self.cuias(), [("ZS3_LOAD", ["*/0"])])
        # SHIFT + pad: store (overwrite, or a new one on an empty pad)
        self.bridge.receive(SHIFT_DOWN)
        self.advance(50)
        self.assertTrue(all(self.led(slot) for slot in range(WINDOW)), "every pad a store target (appendOnly false)")
        self.pad(3)
        self.pad(9)
        self.bridge.receive(SHIFT_UP)
        self.advance(50)
        self.assertEqual(self.cuias(), [("ZS3_SAVE", ["*/3"]), ("ZS3_SAVE", ["*/9"])])
        # zynthian stores */9: the pad lights after the signal
        self.state.zs3["*/9"] = {"title": "ZS3-4"}
        zynstubs.send_signal("S_STATE_MAN", "SS_ZS3_LIST")
        self.advance(100)
        self.assertTrue(self.led(9))
        # CLEAR + pad: remove
        self.cc(CLEAR, 127)
        self.advance(20)
        self.pad(9)
        self.cc(CLEAR, 0)
        self.advance(50)
        self.assertEqual(self.cuias(), [("ZS3_DELETE", ["*/9"])])
        self.assertEqual(self.bridge.core_errors(), [])

    def test_the_zs3_screen_shown_stays(self):
        self.ui.current_screen = "zs3"
        self.enter()
        self.assertEqual(self.cuias(), [])


if __name__ == "__main__":
    unittest.main()
