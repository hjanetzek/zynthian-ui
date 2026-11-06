# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian Autoconnector
#
# Tests of the names of PipeWire's MIDI bridge ports (zynthian_pipewire_ports.py)
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
ports, which the ctrldev drivers are matched by. The port names are
those PipeWire showed on a PC with a Launch Control XL connected (pw-link -o and the JACK port
order, 2026-11-06). The Launch Control XL has two ports: the controls ("Launch Contro", the ALSA
name "Launch Control XL Launch Contro" truncated by PipeWire) and HUI; ALSA, JACK and the uids
number them in this order.

Run from the zynthian-ui checkout (plain Python, no JACK)::

    python3 zynautoconnect/test_zynthian_pipewire_ports.py
"""

import importlib.util
import unittest
from pathlib import Path

# Loaded by path: the package zynautoconnect imports JACK
_spec = importlib.util.spec_from_file_location(
    "zynthian_pipewire_ports", Path(__file__).resolve().parent / "zynthian_pipewire_ports.py")
ports = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ports)

CAPTURE = [
    "Midi-Bridge:Midi Through: Port-0 (capture)",
    "Midi-Bridge:Virtual Raw MIDI 0-0:VirMIDI 0-0 (capture)",
    "Midi-Bridge:Scarlett 18i20 USB: MIDI 1 (capture)",
    "Midi-Bridge:Maschine MK2: In (capture)",
    "Midi-Bridge:Launch Control XL: Launch Contro (capture)",
    "Midi-Bridge:Launch Control XL: HUI (capture)",
]
PLAYBACK = [name.replace("(capture)", "(playback)") for name in CAPTURE]

LCXL_IN = "Midi-Bridge:Launch Control XL: Launch Contro (capture)"
LCXL_HUI = "Midi-Bridge:Launch Control XL: HUI (capture)"


class PipewirePortsTest(unittest.TestCase):

    def test_split(self):
        self.assertEqual(ports.split_pipewire_midi_port(LCXL_IN), ("Launch Control XL", "Launch Contro", True))
        self.assertEqual(ports.split_pipewire_midi_port("Midi-Bridge:Scarlett 18i20 USB: MIDI 1 (capture)"),
                         ("Scarlett 18i20 USB", "MIDI 1", True))
        self.assertEqual(ports.split_pipewire_midi_port("Midi-Bridge:Virtual Raw MIDI 0-0:VirMIDI 0-0 (playback)"),
                         ("Virtual Raw MIDI 0-0", "VirMIDI 0-0", False))
        self.assertIsNone(ports.split_pipewire_midi_port("system:midi_capture_1"))
        self.assertIsNone(ports.split_pipewire_midi_port("Midi-Bridge:odd"))

    def test_launch_control_xl_has_the_zynthianos_device_id(self):
        """The controls port is IN 1 (ZynthianOS: rawmidi input 0); HUI is IN 2."""
        uid, name = ports.pipewire_midi_port_name(LCXL_IN, CAPTURE)
        self.assertEqual(uid, "PW:Launch Control XL/Launch Control XL IN 1")
        self.assertEqual(name, "Launch Control XL 1")
        self.assertEqual(uid.split("/", 1)[1], "Launch Control XL IN 1", "zynautoconnect.get_midi_in_devid")
        hui_uid, hui_name = ports.pipewire_midi_port_name(LCXL_HUI, CAPTURE)
        self.assertEqual(hui_uid, "PW:Launch Control XL/Launch Control XL IN 2")
        self.assertEqual(hui_name, "Launch Control XL 2")
        out_uid, _ = ports.pipewire_midi_port_name(LCXL_IN.replace("(capture)", "(playback)"), PLAYBACK)
        self.assertEqual(ports.dev_out_uid(uid), out_uid, "dev_in_2_dev_out finds the controls output, not HUI's")
        self.assertEqual(out_uid, "PW:Launch Control XL/Launch Control XL OUT 1")

    def test_single_port_device(self):
        self.assertEqual(ports.pipewire_midi_port_name("Midi-Bridge:Scarlett 18i20 USB: MIDI 1 (capture)", CAPTURE),
                         ("PW:Scarlett 18i20 USB/Scarlett 18i20 USB IN 1", "Scarlett 18i20 USB"))

    def test_dev_out_uid_replaces_only_the_direction(self):
        # §9 Z1: str.replace("IN", "OUT") made "APC MOUTI OUT 1"
        self.assertEqual(ports.dev_out_uid("USB:1.2/APC MINI IN 1"), "USB:1.2/APC MINI OUT 1")
        self.assertEqual(ports.dev_out_uid("USB:1.2/Launchpad X IN 2"), "USB:1.2/Launchpad X OUT 2")
        self.assertIsNone(ports.dev_out_uid("Midi-Bridge:something"))


if __name__ == "__main__":
    unittest.main()
