# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# MIDI learn: UI-independent part of zynthian_gui_control / zynthian_gui_controller /
# zynthian_gui_midi_key_range (how a controller's binding is shown, the CC modes, the note range
# learning steps), used by the Tk and Qt UIs. The learning itself is in the state and chain
# managers (enable_learn_cc, add_midi_binding, ...).
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

from zyngine.zynthian_chain_manager import ZMIP_STEP_INDEX

# Learning modes of the control screen
MIDI_LEARNING_DISABLED = 0
MIDI_LEARNING_CHAIN = 1     # bound to the chain (and the input device it was learned from)
MIDI_LEARNING_GLOBAL = 2    # global binding (not tied to a chain)

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
    """How a controller's MIDI bindings are shown: (text, kind) or None. kind: "abs" (global
    binding), "chain" (the chain's binding; its channel in the text when it has one) or "automate"
    (only bound for the step sequencer's automation). The text starts with "A:" if the controller
    is also automated, with "\u23fa" while its relative CC mode is being learned."""
    bindings = chain_manager.get_midi_binding_from_zctrl(zctrl)
    if not bindings:
        return None
    automate = ""
    key = None
    kind = "automate"
    for ml in bindings:
        match ml[1]:
            case "automate":
                automate = "A:"
            case "chain":
                key = ml[0]
                kind = "chain"
            case "global":
                key = ml[0]
                kind = "abs"
    if key is None:
        return automate, kind
    cc, chan, zmip, chain_id = chain_manager.unpack_midi_bind_key(key)
    mode = "\u23fa" if zctrl.midi_cc_mode == -1 else ""
    if kind == "chain" and chan >= 16:
        return f"{mode}{automate}{cc}", kind
    return f"{mode}{automate}{chan + 1}#{cc}", kind


def unlearn_label(chain_manager, ml):
    """The options entry that removes a controller's bindings (get_midi_binding_from_zctrl(...,
    filter_automate=False) result, not empty)"""
    cc, chan, zmip, chain_id = chain_manager.unpack_midi_bind_key(ml[0][0])
    text = f"CH{chan + 1}, CC{cc}" if chan < 16 else f"CC{cc}"
    return f"Unlearn [{text}]"


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


def automate_cc(chain_manager, zctrl):
    """The CC number bound to the controller for the step sequencer's automation, or None"""
    ml = chain_manager.get_midi_binding_from_zctrl(zctrl, False, False, True, 1)
    return chain_manager.unpack_midi_bind_key(ml[0][0])[0] if ml else None


def automate_zctrl(chain_manager, chan, cc):
    """The (first) controller automated by a CC of the step sequencer on a MIDI channel, or None"""
    zctrls = chain_manager.midi_cc_binding.get(chain_manager.pack_midi_bind_key(cc, chan, ZMIP_STEP_INDEX, 0xff))
    return zctrls[0] if zctrls else None


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
