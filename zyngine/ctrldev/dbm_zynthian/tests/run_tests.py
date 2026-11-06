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

"""Runs the tests of the dbm drivers with the stand-ins of zynstubs (the real zyngine package
would import all engines). From the zynthian-ui checkout::

    python3 zyngine/ctrldev/dbm_zynthian/tests/run_tests.py [-v]

The tests with the core need libdrivenbymoss (``$DBM_LIBRARY`` or ``target/debug`` of the
DrivenByMoss checkout next to this one, see zynstubs).
"""

import sys
import unittest
from pathlib import Path

import zynstubs

zynstubs.install()

if __name__ == "__main__":
    tests = unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parent), top_level_dir=str(zynstubs.UI_DIR))
    verbosity = 2 if "-v" in sys.argv else 1
    result = unittest.TextTestRunner(verbosity=verbosity).run(tests)
    sys.exit(0 if result.wasSuccessful() else 1)
