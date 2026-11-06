# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian Control Device Driver
#
# DrivenByMoss on zynthian: runs the tests without the UI
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

"""Runs the tests of the zynthian drivers with the stand-ins of zynstubs (the real zyngine
package would import all engines). From the zynthian-ui root, with a DrivenByMoss build::

    DBM_PYTHON_DIR=<drivenbymoss-rust>/bindings/python \
    DBM_LIBRARY=<drivenbymoss-rust>/target/debug/libdrivenbymoss.so \
        python3 tests/dbm/run_tests.py [-v]

Without ``$DBM_PYTHON_DIR`` the installed drivenbymoss package is used. They exit with 77
("skipped") if DrivenByMoss isn't found. pytest doesn't collect them (tests/dbm/conftest.py): the
stand-ins replace ``zyngine``; ``./run_tests.sh dbm`` runs this script.
"""

import sys
import unittest
from pathlib import Path

import zynstubs

if __name__ == "__main__":
    missing = zynstubs.missing()
    if missing:
        print(f"{missing}: the tests are skipped")
        sys.exit(77)
    zynstubs.install()
    here = str(Path(__file__).resolve().parent)
    tests = unittest.defaultTestLoader.discover(here, top_level_dir=here)
    verbosity = 2 if "-v" in sys.argv else 1
    result = unittest.TextTestRunner(verbosity=verbosity).run(tests)
    sys.exit(0 if result.wasSuccessful() else 1)
