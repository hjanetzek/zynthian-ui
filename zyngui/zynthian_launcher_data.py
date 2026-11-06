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


# Phrase menu (zynthian_gui_mixer.phrase_menu): the options of the selected pad's sequence, or of
# the phrase itself (chan = PHRASE_CHANNEL)

def selected_sequence_info(zynseq_obj, chan):
    """State of channel chan's sequence in the selected phrase (the phrase for PHRASE_CHANNEL), or
    None"""
    try:
        phrase = zynseq_obj.state["scenes"][zynseq_obj.scene]["phrases"][zynseq_obj.phrase]
        return phrase if chan == zynseq.PHRASE_CHANNEL else phrase["sequences"][chan]
    except Exception:
        return None


def phrase_title(zynseq_obj, phrase):
    title = zynseq_obj.state["scenes"][zynseq_obj.scene]["phrases"][phrase]["name"]
    return title or f"Phrase {phrase + 1}"


def follow_info(zynseq_obj, phrase):
    """(offset, title) of the follow action to phrase, from the selected phrase"""
    offset = phrase - zynseq_obj.phrase
    match offset:
        case 0:
            title = "NONE"
        case -1:
            title = f"{phrase_title(zynseq_obj, phrase)} (PREV)"
        case 1:
            title = f"{phrase_title(zynseq_obj, phrase)} (NEXT)"
        case _:
            title = f"{phrase_title(zynseq_obj, phrase)} ({offset:+})"
    if offset < 0:
        title = "LOOP from " + title
    elif offset > 1:
        title = "JUMP to " + title
    return offset, title


def follow_choices(zynseq_obj):
    """(offset, title) for each phrase, as the Automate choices"""
    return [follow_info(zynseq_obj, p) for p in range(zynseq_obj.phrases)]


DURATION_LABELS = ["DISABLED", "AUTO", "1 bar"] + [f"{i} bars" for i in range(2, 255)]
LOOP_COUNT_CHOICES = [(0, "∞")] + [(i, f"{i}") for i in range(2, 33)]


def duration_to_index(repeat):
    """Sequence repeat (0 disabled, 255 auto, n bars) => index in DURATION_LABELS"""
    if repeat == 255:
        return 1
    return repeat + 1 if repeat else 0


def phrase_menu_options(zynseq_obj, chan):
    """(title, options) of the phrase menu; options: list of (key, label, value), key None for
    a heading. Keys: duration, automate, loop_count, loops_to_play, tempo, remove_tempo, bpb,
    rename, insert, clone, move, delete. None if there is nothing to show."""
    info = selected_sequence_info(zynseq_obj, chan)
    if not info:
        return None
    options = []
    phrase = zynseq_obj.phrase
    name = info["name"]
    repeat = info["repeat"]
    follow_action = info["followAction"]
    follow_phrase = phrase + info["followParam"]
    title = "Phrase options" + (f": {name}" if name else "")
    if repeat == 0:
        options.append(("duration", "Duration (DISABLED)", repeat))
    else:
        if repeat == 255:
            options.append(("duration", "Duration (AUTO)", repeat))
        else:
            options.append(("duration", f"Duration ({repeat} {'bar' if repeat == 1 else 'bars'})", repeat))
        if follow_action == zynseq.FOLLOW_ACTION_NONE:
            options.append(("automate", "Automate => NONE", 0))
        elif follow_action == zynseq.FOLLOW_ACTION_RELATIVE:
            offset, follow_name = follow_info(zynseq_obj, follow_phrase)
            flags = info["playFlags"]
            options.append(("automate", f"Automate => {follow_name}", offset))
            if follow_phrase < phrase:
                loop_count = info["followRepeat"]
                options.append(("loop_count", f"  Loop count ({loop_count if loop_count else '∞'})", loop_count))
            loop_info = zynseq_obj.get_phrase_loop_info()
            if loop_info:
                if loop_info[2] > 0:
                    if flags:
                        skip_loops = ",".join(str(i + 1) for i in range(loop_info[2]) if not (flags >> i) & 1)
                    else:
                        skip_loops = "ALL"
                    if skip_loops == "":
                        skip_loops = "NONE"
                else:
                    skip_loops = "NONE" if flags & 1 else "ALL"
                options.append(("loops_to_play", f"  Loops to play ({skip_loops})", flags))
        if "tempo" not in info or info["tempo"] == 0.0:
            options.append(("tempo", "Tempo (NONE)", False))
        else:
            options.append(("tempo", f"Tempo ({info['tempo']:.1f})", info["tempo"]))
            options.append(("remove_tempo", "Remove tempo", phrase))
        if "bpb" not in info or not info["bpb"]:
            options.append(("bpb", "Beats per bar (NONE)", 0))
        else:
            options.append(("bpb", f"Beats per bar ({info['bpb']})", info["bpb"]))
    options.append(("rename", f"Rename ({name})" if name else "Rename", name or ""))
    options.append((None, "> MANAGE", None))
    options.append(("insert", "Insert phrase", phrase))
    options.append(("clone", "Clone phrase", phrase))
    if zynseq_obj.phrases > 1:
        options.append(("move", "Move phrase", phrase))
        options.append(("delete", "Delete phrase", phrase))
    return title, options


def loops_to_play_options(zynseq_obj, flags):
    """The loops-to-play toggles: list of (label, (loop index, flags, set)) as the Tk menu"""
    options = []
    loop_info = zynseq_obj.get_phrase_loop_info()
    if loop_info:
        if loop_info[2] > 0:
            val = flags
            for i in range(loop_info[2]):
                if val & 1:
                    options.append((f"☐ {i + 1}", (i, flags, True)))
                else:
                    options.append((f"☒ {i + 1}", (i, flags, False)))
                val >>= 1
        elif loop_info[2] == 0:
            if flags & 1:
                options.append(("☒ Skip Always", (0, flags, True)))
            else:
                options.append(("☐ Skip Always", (0, flags, False)))
    return options


def toggle_play_flag(zynseq_obj, params):
    """Toggle a loops-to-play flag (params from loops_to_play_options); returns the new flags"""
    index, flags, is_set = params
    flags = flags & ~(1 << index) if is_set else flags | (1 << index)
    zynseq_obj.set_sequence_param(zynseq_obj.scene, zynseq_obj.phrase, zynseq.PHRASE_CHANNEL, "playFlags", flags)
    return flags


def set_phrase_value(zynseq_obj, chain_manager, state_manager, chan, symbol, value):
    """Apply a phrase menu value of the selected phrase (as zynthian_gui_mixer's param editor):
    tempo, bpb, duration (index in DURATION_LABELS), automate (follow offset), loop_count"""
    scene = zynseq_obj.scene
    phrase = zynseq_obj.phrase
    if chan is None:
        chan = zynseq.PHRASE_CHANNEL
    match symbol:
        case "tempo":
            zynseq_obj.set_sequence_param(scene, phrase, zynseq.PHRASE_CHANNEL, "tempo", value)
            if "CL" in chain_manager.zyngines:
                # Warp clips in this phrase to match tempo
                state_manager.start_busy("clippy_rewarp_phrase", "Re-warping audio clips...")
                chain_manager.zyngines["CL"].rewarp_phrase(phrase)
                state_manager.end_busy("clippy_rewarp_phrase")
        case "bpb":
            zynseq_obj.libseq.setPhraseBPB(scene, phrase, value)
            zynseq_obj.refresh_state()
        case "duration":
            if value == 1:
                repeat = 255
            elif value > 1:
                repeat = value - 1
            else:
                repeat = 0
            zynseq_obj.set_sequence_param(scene, phrase, chan, "repeat", repeat)
        case "automate":
            if value == 0:
                action, param = zynseq.FOLLOW_ACTION_NONE, 0
            else:
                action, param = zynseq.FOLLOW_ACTION_RELATIVE, value
            zynseq_obj.set_sequence_param(scene, phrase, chan, "followAction", action)
            zynseq_obj.set_sequence_param(scene, phrase, chan, "followParam", param)
            if param < 0:
                # The phrases in the loop follow to the next one
                for p in range(phrase + param, phrase):
                    if zynseq_obj.state["scenes"][scene]["phrases"][p]["followAction"] == zynseq.FOLLOW_ACTION_NONE:
                        zynseq_obj.set_sequence_param(scene, p, zynseq.PHRASE_CHANNEL, "followAction",
                                                      zynseq.FOLLOW_ACTION_RELATIVE)
                        zynseq_obj.set_sequence_param(scene, p, zynseq.PHRASE_CHANNEL, "followParam", 1)
        case "loop_count":
            zynseq_obj.set_sequence_param(scene, phrase, chan, "followRepeat", value)
