# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# SooperLooper widget: UI-independent part of zynthian_widget_sooperlooper (loop rows and
# button states from the engine's monitors, the actions sent to SooperLooper), used by the Tk
# and Qt UIs.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

import pyliblo3 as liblo

from zyngine.zynthian_engine_sooperlooper import (
    zynthian_engine_sooperlooper, SL_STATE_RECORDING, SL_STATE_OVERDUBBING, SL_STATE_MULTIPLYING,
    SL_STATE_INSERTING, SL_STATE_REPLACING, SL_STATE_DELAYING, SL_STATE_SUBSTITUTING, SL_STATE_OFF,
    SL_STATE_MUTED, SL_STATE_PAUSED, SL_STATE_OFF_MUTED, SL_STATE_PLAYING_ONCE, SL_STATE_REC_STARTING,
    SL_STATE_REC_STOPPING)

MAX_LOOPS = zynthian_engine_sooperlooper.MAX_LOOPS
BUTTONS = ['record', 'overdub', 'multiply', 'replace', 'substitute', 'insert', 'undo', 'redo', 'trigger',
           'oneshot', 'reverse', 'pause']
SLIDERS = ['rec_thresh', 'wet', 'dry', 'feedback']   # controllers set by dragging

# The button lit by a state (steady) and by a pending state (flashing)
_STATE_BUTTON = {SL_STATE_RECORDING: 'record', SL_STATE_OVERDUBBING: 'overdub', SL_STATE_MULTIPLYING: 'multiply',
                 SL_STATE_INSERTING: 'insert', SL_STATE_REPLACING: 'replace', SL_STATE_PLAYING_ONCE: 'oneshot',
                 SL_STATE_SUBSTITUTING: 'substitute', SL_STATE_PAUSED: 'pause'}
_RECORD_STATES = (SL_STATE_RECORDING, SL_STATE_OVERDUBBING, SL_STATE_MULTIPLYING, SL_STATE_INSERTING,
                  SL_STATE_REPLACING, SL_STATE_DELAYING, SL_STATE_SUBSTITUTING)
_OFF_STATES = (SL_STATE_OFF, SL_STATE_MUTED, SL_STATE_PAUSED, SL_STATE_OFF_MUTED)
_MUTE_STATES = (SL_STATE_MUTED, SL_STATE_OFF_MUTED)


def osc_url(processor):
    return f"osc.udp://localhost:{processor.engine.SL_PORT}"


def loop_kind(state, waiting):
    """Colour class of a loop row: "pending", "record", "off" or "play\""""
    if waiting or state in (1, 3):
        return "pending"
    if state in _RECORD_STATES:
        return "record"
    if state in _OFF_STATES:
        return "off"
    return "play"


def loop_rows(monitors):
    """Per loop: dict pos, len, state (name), kind (loop_kind), mute ("on", "flash" or "off")"""
    rows = []
    for loop in range(int(monitors.get('loop_count', 0))):
        pos = monitors.get(f'loop_pos_{loop}', 0)
        length = monitors.get(f'loop_len_{loop}', 0)
        state = monitors.get(f'state_{loop}', 0)
        next_state = monitors.get(f'next_state_{loop}', -1)
        waiting = monitors.get(f'waiting_{loop}', 0)
        if waiting and (next_state in _MUTE_STATES or state in _MUTE_STATES):
            mute = "flash"
        elif state in _MUTE_STATES:
            mute = "on"
        else:
            mute = "off"
        try:
            name = zynthian_engine_sooperlooper.SL_STATES[state]['name']
        except Exception:
            name = ""
        rows.append({"pos": pos, "len": length, "state": name, "kind": loop_kind(state, waiting), "mute": mute})
    return rows


def active_button(monitors):
    """(button lit by the selected loop's state or None, True if flashing: a pending change)"""
    state = monitors.get('state', 0)
    next_state = monitors.get('next_state', -1)
    waiting = monitors.get('waiting', 0)
    if waiting or state in (SL_STATE_REC_STARTING, SL_STATE_REC_STOPPING):
        if state in (SL_STATE_REC_STARTING, SL_STATE_RECORDING, SL_STATE_REC_STOPPING) or next_state == SL_STATE_RECORDING:
            return 'record', True
        for s, btn in _STATE_BUTTON.items():
            if state == s or next_state == s:
                return btn, True
        return None, False
    return _STATE_BUTTON.get(state), False


# Actions

def select_loop(processor, loop):
    liblo.send(osc_url(processor), '/set', ('s', 'selected_loop_num'), ('f', loop))


def toggle_mute(processor, loop):
    liblo.send(osc_url(processor), f'/sl/{loop}/hit', ('s', 'mute'))


def add_loop(processor):
    liblo.send(osc_url(processor), '/loop_add', ('i', 2), ('f', 30), ('i', 0))


def remove_loop(processor, loop):
    liblo.send(osc_url(processor), '/loop_del', ('i', loop))


def press_button(processor, btn):
    """A button of BUTTONS: undo/redo on all loops, the others toggle their controller (of the
    selected loop where the engine has one per loop)"""
    if btn in ('undo', 'redo'):
        liblo.send(osc_url(processor), '/sl/-3/hit', ('s', btn))
        return
    if processor.controllers_dict["selected_loop_cc"].value == 0 and btn in processor.engine.SL_LOOP_SEL_PARAM:
        btn += f":{processor.engine.selected_loop}"
    processor.controllers_dict[btn].toggle()
