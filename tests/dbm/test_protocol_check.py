# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian Control Device Driver
#
# DrivenByMoss on zynthian: the protocol check when the drivers load
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

"""The protocol check of dbm_zynthian.import_dbm: a library with another major version or table
hash than the binding (drivenbymoss.protocol) keeps the dbm drivers from loading, with one logged
error, instead of failing later."""

import importlib
import sys
import types
import unittest
from unittest import mock

import zynstubs

zynstubs.install()

import drivenbymoss  # noqa: E402
from drivenbymoss import protocol  # noqa: E402

import zyngine.ctrldev.dbm_zynthian as dbm_zynthian  # noqa: E402

DRIVER = "zyngine.ctrldev.zynthian_ctrldev_dbm_launchpad_x"
# The modules that import dbm_zynthian (zynthian_ctrldev_base must stay: it sets the start method
# of multiprocessing once per process)
DBM_MODULES = ("zyngine.ctrldev.dbm_zynthian", "zyngine.ctrldev.zynthian_ctrldev_base_dbm", "zyngine.ctrldev.zynthian_ctrldev_dbm_")


class ProtocolMismatchTest(unittest.TestCase):

    def test_matching(self):
        self.assertIsNone(dbm_zynthian.protocol_mismatch(1, 0x1234, (1, 7, 0x1234)))

    def test_major(self):
        message = dbm_zynthian.protocol_mismatch(1, 0x1234, (2, 0, 0x1234))
        self.assertIn("protocol version 2.0", message)

    def test_hash(self):
        message = dbm_zynthian.protocol_mismatch(1, 0x1234, (1, 0, 0x99))
        self.assertIn("0000000000000099", message)
        self.assertIn("0000000000001234", message)

    def test_real_library_matches(self):
        """The library the tests run against matches the binding (else nothing below would load)."""
        self.assertIsNone(dbm_zynthian.protocol_mismatch(protocol.VERSION_MAJOR, protocol.HASH, drivenbymoss.protocol_info()))


class CheckProtocolTest(unittest.TestCase):

    def fake_binding(self, info):
        return types.SimpleNamespace(protocol=protocol, protocol_info=lambda: info)

    def test_match_passes(self):
        dbm_zynthian.check_protocol(self.fake_binding((protocol.VERSION_MAJOR, 0, protocol.HASH)))

    def test_mismatch_raises_and_logs_once(self):
        binding = self.fake_binding((protocol.VERSION_MAJOR + 1, 0, protocol.HASH))
        with self.assertLogs(level="ERROR") as logs:
            with self.assertRaises(dbm_zynthian.DbmProtocolError):
                dbm_zynthian.check_protocol(binding)
            with self.assertRaises(ImportError):
                dbm_zynthian.check_protocol(binding)
        self.assertEqual(len(logs.records), 1)
        self.assertIn("the dbm drivers are not loaded", logs.output[0])

    def test_old_package_without_protocol_raises(self):
        # A drivenbymoss package from before the protocol check has no protocol module
        with self.assertLogs(level="ERROR") as logs:
            with self.assertRaises(dbm_zynthian.DbmProtocolError):
                dbm_zynthian.check_protocol(types.SimpleNamespace())
        self.assertIn("too old", logs.output[0])


class DriverImportTest(unittest.TestCase):
    """A driver module doesn't import with a mismatching library: the ctrldev manager logs it and
    skips the driver (update_available_drivers catches the exception)."""

    @staticmethod
    def dbm_modules():
        return [name for name in sys.modules if name.startswith(DBM_MODULES)]

    def setUp(self):
        self.saved = {name: sys.modules[name] for name in self.dbm_modules()}
        for name in self.saved:
            del sys.modules[name]
        self.saved_error = drivenbymoss.__dict__.pop("_zynthian_protocol_error", None)

    def tearDown(self):
        for name in self.dbm_modules():
            del sys.modules[name]
        sys.modules.update(self.saved)
        drivenbymoss.__dict__.pop("_zynthian_protocol_error", None)
        if self.saved_error is not None:
            drivenbymoss._zynthian_protocol_error = self.saved_error

    def test_hash_mismatch_keeps_driver_from_loading(self):
        wrong = (protocol.VERSION_MAJOR, protocol.VERSION_MINOR, protocol.HASH ^ 1)
        with mock.patch.object(drivenbymoss, "protocol_info", lambda: wrong):
            with self.assertLogs(level="ERROR") as logs:
                for _ in range(2):
                    with self.assertRaises(ImportError):
                        importlib.import_module(DRIVER)
        self.assertEqual(len(logs.records), 1)
        self.assertIn("protocol table hash", logs.output[0])
        self.assertNotIn(DRIVER, sys.modules)


if __name__ == "__main__":
    unittest.main()
