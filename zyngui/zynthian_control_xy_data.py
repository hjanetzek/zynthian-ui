# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# X-Y touchpad: UI-independent part of zynthian_gui_control_xy (a controller's value as a
# position 0..1 along an axis and back, logarithmic controllers on a log scale), used by the Tk
# and Qt UIs. The two controllers are state_manager.zctrl_x / zctrl_y.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

import math


def value_fraction(zctrl):
    """The controller's value as a position 0..1"""
    if not zctrl.value_range:
        return 0.0
    if zctrl.is_logarithmic:
        f = math.log10((9 * zctrl.value - (10 * zctrl.value_min - zctrl.value_max)) / zctrl.value_range)
    else:
        f = (zctrl.value - zctrl.value_min) / zctrl.value_range
    return max(0.0, min(1.0, f))


def fraction_value(zctrl, f):
    """The controller value at position f (0..1); an int for integer controllers"""
    f = max(0.0, min(1.0, f))
    if zctrl.is_logarithmic:
        v = (math.pow(10, f) * zctrl.value_range + (10 * zctrl.value_min - zctrl.value_max)) / 9
    else:
        v = zctrl.value_min + f * zctrl.value_range
    return int(round(v)) if zctrl.is_integer else v
