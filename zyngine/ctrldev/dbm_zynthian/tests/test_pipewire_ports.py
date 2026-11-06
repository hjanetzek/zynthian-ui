# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian Control Device Driver
#
# DrivenByMoss on zynthian: tests of the PipeWire MIDI port names (zynautoconnect)
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

"""zynautoconnect/zynthian_pipewire_ports.py: the uids and device IDs of PipeWire's MIDI bridge
ports, which the dbm drivers (and all other ctrldev drivers) are matched by. The port names are
those PipeWire showed on a PC (pw-link -o, 2026-11-06); the Launch Control XL's is inferred
from them."""

import importlib.util
import unittest

from zyngine.ctrldev.dbm_zynthian.tests import zynstubs

# Loaded by path: the package zynautoconnect imports JACK
_spec = importlib.util.spec_from_file_location(
    "zynthian_pipewire_ports", zynstubs.UI_DIR / "zynautoconnect" / "zynthian_pipewire_ports.py")
ports = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ports)

CAPTURE = [
    "Midi-Bridge:Midi Through: Port-0 (capture)",
    "Midi-Bridge:Scarlett 18i20 USB: MIDI 1 (capture)",
    "Midi-Bridge:Launch Control XL: MIDI 1 (capture)",
    "Midi-Bridge:Launchpad X: LPX DAW (capture)",
    "Midi-Bridge:Launchpad X: LPX MIDI (capture)",
]


class PipewirePortsTest(unittest.TestCase):

    def test_split(self):
        self.assertEqual(ports.split_pipewire_midi_port("Midi-Bridge:Launch Control XL: MIDI 1 (capture)"),
                         ("Launch Control XL", "MIDI 1", True))
        self.assertEqual(ports.split_pipewire_midi_port("Midi-Bridge:Virtual Raw MIDI 0-0:VirMIDI 0-0 (playback)"),
                         ("Virtual Raw MIDI 0-0", "VirMIDI 0-0", False))
        self.assertIsNone(ports.split_pipewire_midi_port("system:midi_capture_1"))
        self.assertIsNone(ports.split_pipewire_midi_port("Midi-Bridge:odd"))

    def test_launch_control_xl_has_the_zynthianos_device_id(self):
        uid, name = ports.pipewire_midi_port_name("Midi-Bridge:Launch Control XL: MIDI 1 (capture)", CAPTURE)
        self.assertEqual(uid, "PW:Launch Control XL/Launch Control XL IN 1")
        self.assertEqual(uid.split("/", 1)[1], "Launch Control XL IN 1", "zynautoconnect.get_midi_in_devid")
        self.assertEqual(name, "Launch Control XL")
        out_uid, _ = ports.pipewire_midi_port_name("Midi-Bridge:Launch Control XL: MIDI 1 (playback)")
        self.assertEqual(ports.dev_out_uid(uid), out_uid, "dev_in_2_dev_out finds the output")

    def test_several_ports_of_one_device(self):
        self.assertEqual(ports.pipewire_midi_port_name("Midi-Bridge:Launchpad X: LPX MIDI (capture)", CAPTURE),
                         ("PW:Launchpad X/Launchpad X IN 2", "Launchpad X 2"))
        self.assertEqual(ports.pipewire_midi_port_name("Midi-Bridge:Launchpad X: LPX DAW (capture)", CAPTURE)[0],
                         "PW:Launchpad X/Launchpad X IN 1")

    def test_dev_out_uid_replaces_only_the_direction(self):
        # §9 Z1: str.replace("IN", "OUT") made "APC MOUTI OUT 1"
        self.assertEqual(ports.dev_out_uid("USB:1.2/APC MINI IN 1"), "USB:1.2/APC MINI OUT 1")
        self.assertEqual(ports.dev_out_uid("USB:1.2/Launchpad X IN 2"), "USB:1.2/Launchpad X OUT 2")
        self.assertIsNone(ports.dev_out_uid("Midi-Bridge:something"))


if __name__ == "__main__":
    unittest.main()
