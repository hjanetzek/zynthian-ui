# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian Control Device Driver
#
# DrivenByMoss on zynthian: the Launch Control XL conformance scenarios of phase 1
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

"""tests/conformance/launchcontrol_xl/track_mix.toml against the model adapter (conformance.py):
the six mixer scenarios of phase 1 compare the same as Java on Bitwig, apart from the listed
differences of zynthian's model (auto-arm, takeover catch, no scenes or transport yet). Skipped
without the DrivenByMoss checkout or the Bitwig profile of the setup."""

import unittest

from zyngine.ctrldev.dbm_zynthian.tests import zynstubs

zynstubs.install()

try:
    from zyngine.ctrldev.dbm_zynthian.tests import conformance
    from conformance.fixture import SETUPS
    AVAILABLE = SETUPS["launchcontrol_xl"].profile_dir.is_dir()
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, "needs the DrivenByMoss checkout and the profile of the launchcontrol_xl setup")
class TrackMixConformanceTest(unittest.TestCase):

    def test_phase_1_scenarios(self):
        result = conformance.run_file("launchcontrol_xl", "track_mix", phase=1)
        report = result.report(verbose=True)
        self.assertEqual(len(result.judged), 6, report)
        self.assertTrue(result.ok, report)
        self.assertEqual(result.core_errors, [], report)
        # The OSC steps and commands of the scenarios not judged in phase 1
        self.assertTrue(set(result.unknown_osc) <= {"/device/page/1/selected", "/click", "/tempo/raw"}, report)
        self.assertTrue(all(key.split(" ")[0] in ("transport", "tempo", "project") for key in result.unhandled), report)


if __name__ == "__main__":
    unittest.main()
