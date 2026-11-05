# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# What a launcher pad shows: UI-independent part of zynthian_gui_mixer's launcher pads, used by
# the Tk and Qt UIs.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

import copy
import logging

from zyngui import zynthian_gui_config
from zynlibs.zynseq import zynseq


def pattern_length_text(beats, bpb):
    """Length of a pattern as bars and extra beats, e.g. "2", "1 + 2♩", "3♩" """
    if not bpb:
        bpb = 4
    bars = beats // bpb if bpb > 1 else 0
    extra_beats = beats % bpb
    beats_text = f"{extra_beats}♩" if extra_beats else ""
    bars_text = f"{bars}" if bars else ""
    if bars and extra_beats:
        return f"{bars_text} + {beats_text}"
    return bars_text + beats_text


def pad_sequence_state(zynseq_obj, chain, phrase):
    """The zynseq state of chain's sequence in phrase (the phrase's own state for the main
    chain); raises an exception for chains without sequence"""
    state_phrase = zynseq_obj.state["scenes"][zynseq_obj.scene]["phrases"][phrase]
    if chain.chain_id == 0:
        return state_phrase
    if chain.midi_chan is None or chain.midi_chan > 31:
        raise ValueError("chain without sequence")
    return state_phrase["sequences"][chain.midi_chan]


def _clippy_value(chain, symbol):
    try:
        return chain.get_clippy_processor().controllers_dict[symbol].get_value()
    except Exception:
        return None


def pad_info(zynseq_obj, chain, phrase, text_color, moving_phrase=False):
    """What the launcher pad of chain in phrase shows, as a dict:

    title, color (background), text_color, mode_text, mode_color, timesig_text, tempo_text,
    state_text and state_color (play state), state (the sequence state, copied: compare it to
    redraw only on change), loops (main chain only: list of (part, top colour, bottom colour,
    text) for the phrase loops this phrase is in; part: "top" (top half and the repeat count),
    "bottom" (bottom half) or "both").
    text_color: the colour of the texts of enabled pads (the mixer's legend text colour)."""
    cfg = zynthian_gui_config
    info = {"title": "", "color": cfg.PAD_COLOUR_DISABLED, "text_color": cfg.PAD_COLOUR_STATE_DISABLED,
            "mode_text": "", "mode_color": cfg.PAD_COLOUR_STATE_DISABLED, "timesig_text": "",
            "tempo_text": "", "state_text": "", "state_color": cfg.PAD_COLOUR_STATE_DISABLED,
            "state": None, "loops": []}
    try:
        state_phrase = zynseq_obj.state["scenes"][zynseq_obj.scene]["phrases"][phrase]
        state_seq = pad_sequence_state(zynseq_obj, chain, phrase)
        info["state"] = copy.copy(state_seq)
        mode_text = ""
        timesig_text = ""
        tempo_text = ""
        color_mode = color_text = text_color

        name = state_seq["name"]
        if not name:
            # No name assigned: a default one
            if chain.chain_id == 0:
                name = f"{phrase + 1}"
            else:
                name = f"{zynseq.CHANNEL_CHARS[chain.midi_chan]}{phrase + 1}"

        disabled = state_seq["repeat"] == 0
        empty = False

        if moving_phrase and phrase == zynseq_obj.phrase:
            if phrase == 0:
                title = f"⇓ {name[:6]}"
            elif phrase == zynseq_obj.phrases - 1:
                title = f"⇑ {name[:6]}"
            else:
                title = f"⇕ {name[:6]}"
        else:
            title = name[:7]

        if chain.chain_id:
            # Chain launcher
            if state_seq["group"] < 16:
                # Zynstep pattern
                try:
                    timesig_text = pattern_length_text(state_seq["nBeats"], state_phrase["bpb"])
                    empty = state_seq.get("nEvents", 0) == 0
                except Exception as e:
                    logging.error(e)
                    disabled = True
            else:
                # Clippy (audio clip)
                if _clippy_value(chain, f"file {phrase + 1}"):
                    beats = _clippy_value(chain, f"beats {phrase + 1}")
                    timesig_text = str(beats // 4) if beats is not None else "1"
                else:
                    empty = True
            if state_seq["repeat"] == 1:
                mode_text = "↦"
            elif state_seq["repeat"] == 255:
                mode_text = "↻"
            elif state_seq["repeat"] > 1:
                mode_text = "x" + str(state_seq["repeat"])
            if empty:
                color = cfg.PAD_COLOUR_EMPTY
            else:
                color = cfg.LAUNCHER_COLOUR[state_seq["group"]]["rgb"]
        else:
            # Phrase launcher (main chain)
            color = cfg.PAD_COLOUR_PHRASE
            loop_info = zynseq_obj.get_phrase_loop_info_all(phrase)
            if loop_info:
                for i, linfo in enumerate(reversed(loop_info)):
                    if i == 0:
                        c1 = c2 = "#5050FF"
                    elif i == 1:
                        c1 = c2 = "#40C040"
                    else:
                        logging.warning(f"Loop at level {i} not displayable!")
                        continue
                    if state_seq["followAction"] == zynseq.FOLLOW_ACTION_NONE:
                        c2 = "#" + "".join(f"{int(int(c1[j:j + 2], 16) * 0.85):02x}" for j in (1, 3, 5))
                    if linfo[0] == phrase:
                        repeat = state_seq["followRepeat"]
                        info["loops"].append(("top", c1, c2, f"{repeat}" if repeat else "∞"))
                    elif linfo[0] - linfo[1] == phrase:
                        info["loops"].append(("bottom", c1, c2, ""))
                    else:
                        info["loops"].append(("both", c1, c2, ""))
            # Duration in bars (255 = auto)
            try:
                if state_seq["repeat"] != 255 and state_seq["repeat"] > 0:
                    mode_text = f"{state_seq['repeat']}"
            except Exception:
                pass
            # Flow
            match state_seq["followAction"]:
                case zynseq.FOLLOW_ACTION_NONE:
                    mode_text += "↻"
                case zynseq.FOLLOW_ACTION_RELATIVE:
                    offset = state_seq["followParam"]
                    if offset < 0:
                        mode_text += "↑"
                    elif offset == 0:
                        mode_text += "↻"
                    elif offset == 1:
                        mode_text += "↓"
                    else:
                        mode_text += f"↓{offset}"
            try:
                if state_seq["bpb"]:
                    timesig_text = f"{state_seq['bpb']}/4"
            except Exception:
                pass
            if state_seq.get("tempo"):
                tempo_text = f"{state_seq['tempo']:.1f}"

        if disabled:
            color = cfg.PAD_COLOUR_DISABLED
            color_mode = color_text = color_state = cfg.PAD_COLOUR_STATE_DISABLED
            state_text = ""
        else:
            match state_seq["state"]:
                case zynseq.SEQ_PLAYING:
                    color_state, state_text = cfg.PAD_COLOUR_PLAYING, "▶"
                case zynseq.SEQ_STARTING:
                    color_state, state_text = cfg.PAD_COLOUR_STARTING, "▶"
                case zynseq.SEQ_STOPPING | zynseq.SEQ_STOPPING_SYNC | zynseq.SEQ_CHILD_STOPPING:
                    color_state, state_text = cfg.PAD_COLOUR_STOPPING, "▶"
                case zynseq.SEQ_CHILD_PLAYING:
                    color_state, state_text = cfg.PAD_COLOUR_STOPPED, "▶"
                case zynseq.SEQ_STOPPED:
                    color_state, state_text = cfg.PAD_COLOUR_STOPPED, "⏹"
                case _:
                    color_mode = color_text = color_state = cfg.PAD_COLOUR_STATE_DISABLED
                    state_text = "?"
        info.update({"title": title, "color": color, "text_color": color_text, "mode_text": mode_text,
                     "mode_color": color_mode, "timesig_text": timesig_text, "tempo_text": tempo_text,
                     "state_text": state_text, "state_color": color_state})
    except Exception:
        info["loops"] = []
    return info


def pad_channel(chain):
    """zynseq channel of chain's launcher pads (32: the main chain's phrase launchers), or None"""
    midi_chan = chain.midi_chan if chain.chain_id else zynseq.PHRASE_CHANNEL
    if midi_chan is None or midi_chan > zynseq.PHRASE_CHANNEL:
        return None
    return midi_chan


def toggle_pad(zynseq_obj, chain, phrase):
    """Start or stop chain's sequence in phrase (the phrase itself for the main chain)"""
    chan = pad_channel(chain)
    if chan is not None:
        zynseq_obj.libseq.togglePlayState(zynseq_obj.scene, phrase, chan)
