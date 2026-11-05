# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# MIDI learn: UI-independent part of zynthian_gui_control / zynthian_gui_controller /
# zynthian_gui_midi_key_range (how a controller's binding is shown, the CC modes, the note range
# learning steps), used by the Tk and Qt UIs. The learning itself is in the state and chain
# managers (enable_learn_cc, add_midi_learn, ...).
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

import zynautoconnect

# Learning modes of the control screen
MIDI_LEARNING_DISABLED = 0
MIDI_LEARNING_CHAIN = 1     # bound to the chain's MIDI channel (any input device)
MIDI_LEARNING_GLOBAL = 2    # bound to the input device and channel ("absolute")

# CC modes of a learned controller: (label, mode for zctrl.midi_cc_mode_set, reversed, info)
CC_MODES = (
    ("Absolute Mode", 0, False, "Controller sends absolute value:\n0—127"),
    ("Absolute Reverse", 0, True, "Controller sends reversed absolute value:\n127—0"),
    ("Relative Mode 1 (55—63, 64—73)", 1, False, "Down: 55—63\nUp:65—73\nWITH speed-up"),
    ("Relative Mode 2 (118—127, 1—9)", 2, False, "Down: 118—127\nUp:1—9\nWITH speed-up"),
    ("Relative Mode 3 (7—15, 17—24)", 3, False, "Down:7—15\nUp:17—24\nWITH speed-up"),
    ("Relative Mode 4 (0—63, 64—127)", 4, False, "Down:0—63\nUp:64—127\nNO speed-up"),
    ("Learn Relative Mode", -1, False, "Auto-detected from user's actions"),
)


def binding(chain_manager, zctrl):
    """How a controller's MIDI binding is shown: (text, kind) or None. kind: "abs" (device and
    channel: global learn), "chain" (the chain's channel or a fixed one) or "zynstep\""""
    ml = chain_manager.get_midi_learn_from_zctrl(zctrl)
    if not ml:
        return None
    key = ml[0]
    cc = key & 0xff
    chan = (key >> 8) & 0xff
    match ml[1]:
        case "abs":
            return f"{chan + 1}#{cc}", "abs"
        case "chain":
            return (f"{chan + 1}#{cc}" if chan < 16 else f"{cc}"), "chain"
        case "zynstep":
            return f"{cc}", "zynstep"
    return None


def unlearn_label(ml):
    """The options entry that removes a binding (get_midi_learn_from_zctrl(..., abs=True,
    chain=True) result), or None"""
    cc = ml[0] & 0x7f
    chan = (ml[0] >> 8) & 0xff
    text = f"CH{chan + 1}, CC{cc}" if chan < 16 else f"CC{cc}"
    match ml[1]:
        case "abs":
            dev_name = zynautoconnect.get_midi_in_devid((ml[0] >> 16) & 0xff)
            return f"Unlearn [{dev_name}, {text}]"
        case "chain":
            return f"Unlearn [{text}]"
    return None


def cc_mode_label(zctrl):
    """The options entry showing a learned controller's CC mode"""
    match zctrl.midi_cc_mode:
        case -1:
            return "Relative Mode learning..."
        case 0:
            return "Absolute Reverse" if zctrl.range_reversed else "Absolute Mode"
        case mode:
            return f"Relative Mode {mode}"


def set_cc_mode(zctrl, mode, reverse):
    zctrl.midi_cc_mode_set(mode)
    zctrl.range_reversed = reverse


def zynstep_cc(chain_manager, zctrl):
    """The CC number bound to the controller for the step sequencer, or None"""
    ml = chain_manager.get_midi_learn_from_zctrl(zctrl, abs=False, chain=False, zynstep=True)
    return ml[0] & 0x7f if ml else None


def note_range_learn(learn_mode, note, low, high):
    """One note while learning a chain's note range (zynthian_gui_midi_key_range): the first
    note moves the nearer end, the second sets both ends. learn_mode: -1 before the first note,
    else the first note. Returns (learn_mode, low, high, done)"""
    if learn_mode == -1:
        if note < high:
            low = note
        else:
            high = note
        return note, low, high, False
    return learn_mode, min(note, learn_mode), max(note, learn_mode), True
