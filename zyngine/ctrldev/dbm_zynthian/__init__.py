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

This package needs the Python packages of DrivenByMoss, ``drivenbymoss`` (the binding) and
``dbm_host`` (the reference host), and the native library ``libdrivenbymoss.so``.
``import_dbm`` finds them: on the Python path, else in ``$DBM_PYTHON_DIR``, else in
``/usr/share/drivenbymoss/python`` (the package). The binding finds the library through
``$DBM_LIBRARY``; ``/usr/lib/drivenbymoss/libdrivenbymoss.so`` is set as the default.
"""

import os
import sys

DEFAULT_PYTHON_DIR = "/usr/share/drivenbymoss/python"
DEFAULT_LIBRARY = "/usr/lib/drivenbymoss/libdrivenbymoss.so"


def import_dbm():
    """Make the DrivenByMoss packages importable; returns the binding module."""

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
    return drivenbymoss


import_dbm()
