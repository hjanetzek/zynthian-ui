# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian Control Device Driver
#
# DrivenByMoss on zynthian: the model adapter of the dbm drivers
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

"""DrivenByMoss (https://github.com/git-moss/DrivenByMoss, the Rust port's C ABI) as zynthian
controller drivers: the core runs the controller, zynthian is its DAW.

The parts (see doc/ZYNTHIAN_PLAN.md of the DrivenByMoss port):

- ``model``: zynthian's chains, mixer strips and sends as the core's tracks, effect tracks and
  master (``ZynthianModel``).
- ``reporter``: reports the model to the core, change-only (``ZynReporter``).
- ``commands``: executes the core's commands on zynthian (``ZynCommandHandler``).
- ``bridge``: the loop of one controller (``ZynBridge``), on the reference host's ``Bridge``.

The driver base class is ``zyngine/ctrldev/zynthian_ctrldev_base_dbm.py``.

The drivers are part of zynthian-ui (``zyngine/ctrldev``); the core, the binding, the reference
host and the protocol are DrivenByMoss' (https://github.com/hjanetzek/drivenbymoss-rust).

This package needs the Python packages of DrivenByMoss, ``drivenbymoss`` (the binding) and
``dbm_host`` (the reference host), and the native library ``libdrivenbymoss.so``.
``import_dbm`` finds them: on the Python path, else in ``$DBM_PYTHON_DIR`` (development: the
``bindings/python`` of a DrivenByMoss checkout), else in ``/usr/share/drivenbymoss/python`` (the
drivenbymoss package). The binding loads the library from ``$DBM_LIBRARY``, which defaults to
``/usr/lib/drivenbymoss/libdrivenbymoss.so`` (the package) if that exists.

``import_dbm`` then compares the protocol of the binding (``drivenbymoss.protocol``: major version
and table hash) with the library's (``dbm_protocol_info``). On a mismatch it logs an error and
raises ``DbmProtocolError`` (an ``ImportError``): the ctrldev manager then doesn't load the dbm
drivers.
"""

import logging
import os
import sys

DEFAULT_PYTHON_DIR = "/usr/share/drivenbymoss/python"
DEFAULT_LIBRARY = "/usr/lib/drivenbymoss/libdrivenbymoss.so"


class DbmProtocolError(ImportError):
    """The binding and the native library speak different protocols."""


def protocol_mismatch(binding_major, binding_hash, library_info):
    """The error message if the library's (major, minor, hash) doesn't match the binding, else None."""
    major, minor, hash_ = library_info
    if major != binding_major:
        return f"protocol version {major}.{minor}, the binding (drivenbymoss.protocol) has {binding_major}"
    if hash_ != binding_hash:
        return f"protocol table hash {hash_:016x}, the binding (drivenbymoss.protocol) has {binding_hash:016x}"
    return None


def check_protocol(drivenbymoss):
    """Raise DbmProtocolError (logged once per process) if the library doesn't match the binding."""
    # The result is kept on the binding module: a failed import of this package is not cached
    # and every dbm driver module tries it again
    error = getattr(drivenbymoss, "_zynthian_protocol_error", None)
    if error is None:
        protocol = getattr(drivenbymoss, "protocol", None)
        if protocol is None or not hasattr(drivenbymoss, "protocol_info"):
            # A DrivenByMoss package from before the protocol check (no drivenbymoss.protocol)
            mismatch = "no protocol information: the drivenbymoss package is too old"
        else:
            mismatch = protocol_mismatch(protocol.VERSION_MAJOR, protocol.HASH, drivenbymoss.protocol_info())
        error = ""
        if mismatch:
            library = os.environ.get("DBM_LIBRARY", "libdrivenbymoss")
            error = (f"DrivenByMoss: the library {library} has {mismatch}: the dbm drivers are not "
                     f"loaded (install matching drivenbymoss packages, or set DBM_LIBRARY and DBM_PYTHON_DIR "
                     f"to one build)")
            logging.error(error)
        drivenbymoss._zynthian_protocol_error = error
    if error:
        raise DbmProtocolError(error)


def import_dbm():
    """Make the DrivenByMoss packages importable and check the protocol; returns the binding module."""

    try:
        import drivenbymoss
        import dbm_host
    except ImportError:
        for path in (os.environ.get("DBM_PYTHON_DIR"), DEFAULT_PYTHON_DIR):
            if path and os.path.isdir(path) and path not in sys.path:
                sys.path.append(path)
        import drivenbymoss
        import dbm_host
    if not os.environ.get("DBM_LIBRARY") and os.path.isfile(DEFAULT_LIBRARY):
        os.environ["DBM_LIBRARY"] = DEFAULT_LIBRARY
    check_protocol(drivenbymoss)
    return drivenbymoss


import_dbm()
