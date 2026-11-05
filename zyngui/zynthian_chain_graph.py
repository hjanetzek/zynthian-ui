# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# The chain manager's graph: UI-independent part of zynthian_gui_chain_manager, used by the Tk
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

DST_TYPES = ("MIDI Synth", "Audio Effect", "MIDI Tool", "Special", "midi_key_range", "add_midi_proc",
             "midi_output", "audio_out")
SRC_TYPES = ("MIDI Synth", "Audio Generator", "Audio Effect", "MIDI Tool", "Special", "midi_key_range",
             "midi_input", "add_midi_proc", "audio_in")


def _add_node(nodes, chain_idx, row, title, chain_id, proc="", slot=None, idx=None):
    """Add a node to the graph

    chain_idx: column (chain) of the node
    row: row of the node
    title: title shown
    chain_id: the zynthian chain_id (not necessarily the display position)
    proc: processor object, or a string naming a non-processor node
    """
    while len(nodes) <= chain_idx:
        nodes.append([])
    while len(nodes[chain_idx]) <= row:
        nodes[chain_idx].append([])
    proc_type = proc if isinstance(proc, str) else proc.type
    nodes[chain_idx][row].append({
        "title": title,
        "chain_id": chain_id,
        "proc": proc,
        "slot": slot,  # processor slot
        "idx": idx,  # index of (parallel) processor within slot
        "pos": [chain_idx, row, len(nodes[chain_idx][row])],  # position of node within graph
        "is_dst": proc_type in DST_TYPES,
        "is_src": proc_type in SRC_TYPES
    })


def build_chain_graph(chain_manager):
    """The chains as graph: nodes[chain_idx][row] is the list of (parallel) nodes in that row.
    Rows: chain options, MIDI input, MIDI processors, synths or MIDI output, audio input, audio
    processors, audio output. Returns (nodes, rows): rows is the largest number of rows."""
    nodes = []
    rows = 0
    for chain_idx, chain in enumerate(chain_manager.chains.values()):
        chain_id = chain.chain_id
        row = 0

        # Chain option button
        _add_node(nodes, chain_idx, row, chain.get_name(), chain_id, "chain_options")
        row += 1
        # MIDI input
        if chain.is_midi():
            _add_node(nodes, chain_idx, row, "MIDI Input", chain_id, "midi_input")
            row += 1
        # MIDI processors
        for slot_idx, slot in enumerate(chain.midi_slots):
            for proc_idx, processor in enumerate(slot):
                _add_node(nodes, chain_idx, row, processor.get_name(), chain_id, processor, slot_idx, proc_idx)
            if len(nodes[chain_idx]) > row:
                row += 1
        if chain.synth_slots:
            # Synths
            for slot_idx, slot in enumerate(chain.synth_slots):
                for proc_idx, processor in enumerate(slot):
                    _add_node(nodes, chain_idx, row, processor.get_name(), chain_id, processor, slot_idx, proc_idx)
                if len(nodes[chain_idx]) > row:
                    row += 1
        elif chain.is_midi():
            _add_node(nodes, chain_idx, row, "MIDI Output", chain_id, "midi_output")
            row += 1
        # Audio input
        if chain.audio_thru and chain.zynmixer_proc and chain.zynmixer_proc.eng_code != "MR":
            _add_node(nodes, chain_idx, row, "Audio Input", chain_id, "audio_in")
            row += 1
        # Audio processors
        for slot_idx, slot in enumerate(chain.audio_slots):
            for proc_idx, processor in enumerate(slot):
                _add_node(nodes, chain_idx, row, processor.get_name(), chain_id, processor, slot_idx, proc_idx)
            if len(nodes[chain_idx]) > row:
                row += 1
        # Audio output
        if chain.is_audio():
            _add_node(nodes, chain_idx, row, "Audio Output", chain_id, "audio_out")
            row += 1
        rows = max(rows, row)
    return nodes, rows


def node_kind(node):
    """Colour class of a node: "chain", "midi", "synth", "audio", "special" or "" (other)"""
    proc = node.get("proc")
    if isinstance(proc, str):
        match proc:
            case "chain_options":
                return "chain"
            case "midi_input" | "note_range" | "add_midi_proc" | "midi_output" | "midi_key_range":
                return "midi"
            case "audio_in" | "audio_out":
                return "audio"
        return ""
    match proc.type:
        case "MIDI Input" | "MIDI Output" | "MIDI Tool":
            return "midi"
        case "MIDI Synth" | "Audio Generator":
            return "synth"
        case "Audio Input" | "Audio Output" | "Audio Effect":
            return "audio"
        case "Special":
            return "special"
    return ""
