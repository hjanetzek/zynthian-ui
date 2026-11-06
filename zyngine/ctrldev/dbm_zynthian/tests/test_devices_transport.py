# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian Control Device Driver
#
# DrivenByMoss on zynthian: tests of phase 2, the devices and the transport
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

"""Phase 2 (doc/ZYNTHIAN_PLAN.md §4): the active chain's processors as the cursor device with its
siblings and parameter pages (two zynthian screens of 4 per page of 8), and zynseq's transport.
The adapter without the core, then the Launch Control XL with the core."""

import tempfile
import unittest

from zyngine.ctrldev.dbm_zynthian.tests import zynstubs

zynstubs.install()

from dbm_host import Banks  # noqa: E402
from zyngine.ctrldev.dbm_zynthian.bridge import ZynBridge  # noqa: E402
from zyngine.ctrldev.dbm_zynthian.commands import ZynCommandHandler  # noqa: E402
from zyngine.ctrldev.dbm_zynthian.model import ZynthianModel  # noqa: E402
from zyngine.ctrldev.dbm_zynthian.reporter import ZynReporter  # noqa: E402
from zyngine.ctrldev.dbm_zynthian.transport import TRANSPORT_CLIENT_ALL, TRANSPORT_CLIENT_DBM  # noqa: E402
from zyngine.ctrldev.zynthian_ctrldev_dbm_launchcontrol_xl import zynthian_ctrldev_dbm_launchcontrol_xl as driver  # noqa: E402

SYNTH_SCREENS = [(f"screen {n}", [f"p{n}{i}" for i in range(4)]) for n in range(1, 6)] + [("modes", ["mode", "p61"])]


def project():
    """The project of test_model with a synth (6 screens: 3 pages) and an effect on chain 1, a
    synth on chain 2, and zynseq."""
    state = zynstubs.project()
    state.zynseq = zynstubs.FakeZynseq()
    state.synth = state.add_processor(1, "Synth A", SYNTH_SCREENS)
    state.effect = state.add_processor(1, "Reverb FX", [("main", ["mix", "size"])])
    state.add_processor(2, "Piano B", [("main", ["tone"])])
    return state


class Host:

    def __init__(self, setup=None):
        self.state = project()
        self.clock = 0.0
        self.model = ZynthianModel(self.state.chain_manager, zynseq=self.state.zynseq)
        self.banks = Banks.from_model_setup(setup or {"numTracks": 8, "numSends": 2, "numParamPages": 8})
        self.reporter = ZynReporter(self.model, self.banks, clock=lambda: self.clock)
        self.commands = ZynCommandHandler(self.model, self.banks, self.reporter, clock=lambda: self.clock)
        self.commands.configure()
        self.reporter.features = self.commands.host_features

    def report(self):
        return dict(line.split(" ", 1) for line in self.reporter.collect().splitlines())

    def command(self, processor, command, value=None):
        self.commands.handle(processor, command, value)


class DeviceTest(unittest.TestCase):

    def test_device_chain_and_pages(self):
        host = Host()
        chain = host.model.devices
        self.assertEqual([d.name for d in chain.devices()], ["Synth A", "Reverb FX"], "Without the mixer strip")
        device = chain.cursor()
        self.assertEqual(device.name, "Synth A")
        self.assertEqual(device.page_names(), ["screen 1", "screen 3", "screen 5"])
        self.assertEqual(device.zctrl(0).symbol, "p10")
        self.assertEqual(device.zctrl(5).symbol, "p21", "The second screen fills the parameters 4..7 of a page")
        self.assertEqual(device.zctrl(9).symbol, "p31")
        self.assertEqual(device.zctrl(20).symbol, "mode")
        self.assertIsNone(device.zctrl(22), "The last screen has only two zctrls")
        self.assertIsNone(device.zctrl(24))

    def test_report(self):
        report = Host().report()
        self.assertIn("deviceCommands", report["/host/features"])
        self.assertIn("transportCommands", report["/host/features"])
        self.assertEqual(report["/device/exists"], "1")
        self.assertEqual(report["/device/name"], "Synth A")
        self.assertEqual(report["/device/count"], "2")
        self.assertEqual(report["/device/position"], "0")
        self.assertEqual(report["/device/sibling/2/name"], "Reverb FX")
        self.assertEqual(report["/device/sibling/3/name"], "")
        self.assertEqual(report["/device/param/count"], "24")
        self.assertEqual(report["/device/param/0/name"], "p10")
        self.assertAlmostEqual(float(report["/device/param/0/value"]), 64 / 127, places=5)
        self.assertEqual(report["/device/param/0/value/str"], "64")
        self.assertEqual(report["/device/param/20/value/str"], "saw")
        self.assertEqual(report["/device/param/22/name"], "")
        self.assertEqual(report["/device/page/count"], "3")
        self.assertEqual(report["/device/page/1/name"], "screen 3")
        self.assertEqual(report["/device/page/selected"], "0")
        self.assertEqual(report["/device/hasDrumPads"], "0")

    def test_commands(self):
        host = Host()
        synth = host.state.synth
        host.command("device", "param/1/value", 1.0)
        self.assertEqual(synth.controllers_dict["p11"].value, 127)
        host.command("device", "param/1/value/inc", -0.5)
        self.assertEqual(synth.controllers_dict["p11"].value, 63)
        host.command("device", "param/1/value/reset")
        self.assertEqual(synth.controllers_dict["p11"].value, 64)
        host.command("device", "param/20/value", 1.0)
        self.assertEqual(synth.controllers_dict["mode"].get_value2label(), "sine", "A zctrl with labels by index")
        host.command("device", "param/30/value", 1.0)
        host.command("device", "parameterPage", 2)
        self.assertEqual(synth.current_screen_index, 4)
        self.assertEqual(host.report()["/device/page/selected"], "2")
        host.command("device", "bypass")
        self.assertTrue(synth.bypassed)
        host.command("device", "1/bypass", 0)
        self.assertFalse(synth.bypassed, "The Reaper path sets the state")
        host.command("device", "+")
        self.assertIs(host.state.chain_manager.chains[1].current_processor, host.state.effect)
        host.command("device", "sibling/1/select")
        self.assertIs(host.state.chain_manager.chains[1].current_processor, synth)
        host.command("device", "window/toggle")
        self.assertEqual(host.commands.unhandled, [])
        host.command("device", "remove")
        self.assertEqual(host.commands.unhandled, ["device remove"])

    def test_cursor_follows_the_active_chain(self):
        host = Host()
        host.report()
        host.state.chain_manager.set_active_chain_by_id(2)
        report = host.report()
        self.assertEqual(report["/device/name"], "Piano B")
        self.assertEqual(report["/device/param/count"], "8")
        host.state.chain_manager.set_active_chain_by_id(3)
        report = host.report()
        self.assertEqual(report["/device/exists"], "0", "Audio In has only its mixer strip")


class TransportTest(unittest.TestCase):

    def test_report_and_commands(self):
        host = Host()
        libseq = host.state.zynseq.libseq
        report = host.report()
        self.assertEqual((report["/play"], report["/tempo"], report["/numerator"], report["/click"]), ("0", "120.000000", "4", "0"))
        host.command("transport", "play")
        self.assertEqual(libseq.calls[-1], ("start", TRANSPORT_CLIENT_DBM))
        self.assertEqual(host.report()["/play"], "1")
        host.command("transport", "stop")
        self.assertEqual(libseq.calls[-1], ("stop", TRANSPORT_CLIENT_ALL))
        host.command("transport", "restart")
        self.assertEqual(libseq.calls[-2:], [("stop", TRANSPORT_CLIENT_ALL), ("start", TRANSPORT_CLIENT_DBM)])
        host.command("tempo", "++")
        host.command("tempo", "-")
        self.assertAlmostEqual(libseq.tempo, 120.99)
        host.command("tempo", "", 90.0)
        self.assertEqual(libseq.tempo, 90.0)
        host.command("transport", "toggleMetronome")
        self.assertEqual(libseq.metronome_mode, 1, "Metronome while the transport runs")
        self.assertEqual(host.report()["/click"], "1")
        host.command("transport", "metronomeVolume/inc", 0.25)
        self.assertAlmostEqual(libseq.metronome_volume, 0.75)
        host.command("transport", "tapTempo")
        self.assertEqual(host.commands.unhandled, [])


    def test_state_from_an_older_library(self):
        """Without getTransportState in the C interface (§9 Z10) the state comes from the
        exported global g_nTransportState (read only, libzynseq is not initialised)."""
        import ctypes
        from zyngine.ctrldev.dbm_zynthian.transport import ZynTransport
        path = zynstubs.UI_DIR / "zynlibs" / "zynseq" / "build" / "libzynseq.so"
        if not path.exists():
            self.skipTest("libzynseq is not built")
        try:
            lib = ctypes.CDLL(str(path))
        except OSError as e:
            self.skipTest(f"libzynseq does not load here: {e}")

        class OldLibseq:
            def __getattr__(self, name):
                if name == "getTransportState":
                    raise AttributeError(name)
                return getattr(lib, name)

        old = ZynTransport(type("zynseq", (), {"libseq": OldLibseq()})())
        self.assertEqual(old.transport_state(), 0)
        self.assertFalse(old.playing)

    def test_a_failing_collector_does_not_stop_the_others(self):
        host = Host()
        host.state.zynseq.libseq.getTempo = None  # not callable: the transport collector fails
        with self.assertLogs("dbm_zynthian", "ERROR"):
            report = host.report()
        self.assertEqual(report["/track/0/name"], "Synth")
        self.assertEqual(report["/device/name"], "Synth A")


class LaunchControlXLDeviceTest(unittest.TestCase):
    """The Launch Control XL's device control in the Track Mix and its transport functions
    (Record Arm held), with the core."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dbm-zynthian-test-")
        self.state = project()
        self.model = ZynthianModel(self.state.chain_manager, zynseq=self.state.zynseq)
        self.midi_out = []
        self.bridge = ZynBridge(self.model, driver.dbm_controller_id, self.temp.name, "zynthian", midi_sink=self.device)
        self.bridge.start()
        self.bridge.wait_for_startup()
        self.bridge.advance(100)

    def tearDown(self):
        self.bridge.close()
        self.temp.cleanup()

    def device(self, data):
        self.midi_out.append(bytes(data))
        if data[:7] == bytes.fromhex("F0002029021177"):
            self.bridge.receive(data)

    def press(self, note):
        self.bridge.send([0x98, note, 127])
        self.bridge.send([0x88, note, 0])

    def test_device_knobs_and_pages(self):
        synth = self.state.synth
        # Device on: the third knob row controls the parameters of the cursor device
        self.press(0x69)
        self.bridge.advance(200)
        self.bridge.send([0xB8, 0x31, 127], 400)
        self.assertEqual(synth.controllers_dict["p10"].value, 127)
        self.bridge.send([0xB8, 0x38, 0], 400)
        self.assertEqual(synth.controllers_dict["p23"].value, 0, "Knob 8: the 4th zctrl of the second screen")
        # Device held + Track Control 2: parameter page 2 = screens 3 and 4
        self.bridge.send([0x98, 0x69, 127])
        self.press(0x4A)
        self.bridge.send([0x88, 0x69, 0], 400)
        self.assertEqual(synth.current_screen_index, 2)
        self.bridge.send([0xB8, 0x31, 0], 400)
        self.assertEqual(synth.controllers_dict["p30"].value, 0)
        self.assertEqual(list(self.bridge.core_errors()), [])
        self.assertNotIn("device", {key.split(" ")[0] for key in self.bridge.commands.unhandled}, self.bridge.commands.unhandled)

    def test_transport_functions(self):
        libseq = self.state.zynseq.libseq
        # Record Arm held + Track Focus 4: tempo +1
        self.bridge.send([0x98, 0x6C, 127])
        self.press(0x2C)
        self.bridge.send([0x88, 0x6C, 0], 400)
        self.assertAlmostEqual(libseq.tempo, 121.0)
        self.assertEqual(list(self.bridge.core_errors()), [])
        self.assertNotIn("tempo ++", self.bridge.commands.unhandled)


if __name__ == "__main__":
    unittest.main()
