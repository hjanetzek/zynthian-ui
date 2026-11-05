# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Pattern editor: UI-independent part of zynthian_gui_pated_notes / _base (keymaps, scales,
# reading the note events of the selected pattern, new note defaults), used by the Tk and Qt UIs.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

import os
import json
import logging
from xml.dom import minidom

from zynconf import zynthian_paths
from zynlibs.zynseq import zynseq

CONFIG_ROOT = f"{zynthian_paths.data_dir}/zynseq"
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
STEPS_PER_BEAT = [1, 2, 3, 4, 6, 8, 12, 24]


def note_name(note):
    return f"{NOTE_NAMES[note % 12]}{note // 12 - 1}"


def load_scales():
    """The scales of scales.json (list of {"name", "scale"}); empty if it can't be read"""
    try:
        with open(CONFIG_ROOT + "/scales.json") as json_file:
            return json.load(json_file)
    except Exception:
        logging.warning("Unable to open scales.json")
        return []


def get_custom_keymap(chain_manager, channel):
    """A custom keymap for the synth on MIDI channel: [map name, synth processor] if the synth
    has one, [map name, midnam file path] from keymaps.json, or None"""
    synth_proc = chain_manager.get_synth_processor(channel)
    if not synth_proc:
        logging.info(f"MIDI channel {channel} has not synth processors.")
        return None
    # Ask the synth processor for a keymap
    try:
        keymap_name = synth_proc.get_keymap_name()
    except Exception:
        keymap_name = None
    if keymap_name:
        return [keymap_name, synth_proc]
    # Else, try to find a midnam file
    map_name = None
    preset_path = synth_proc.get_presetpath()
    try:
        with open(CONFIG_ROOT + "/keymaps.json") as json_file:
            data = json.load(json_file)
            for pat in data:
                if pat in preset_path:
                    map_name = data[pat]
                    break
        if map_name:
            keymap_fpath = CONFIG_ROOT + f"/{map_name}.midnam"
            if os.path.isfile(keymap_fpath):
                return [map_name, keymap_fpath]
            logging.warning(f"Keymap file {keymap_fpath} doesn't exist.")
    except Exception:
        logging.warning("Unable to load keymaps.json")
    return None


def scale_names(chain_manager, channel):
    """Names of the scales as the Scale menu lists them: index 0 the custom keymap"""
    custom_keymap = get_custom_keymap(chain_manager, channel)
    res = [f"Custom - {custom_keymap[0]}" if custom_keymap else "Custom - None"]
    return res + [scale["name"] for scale in load_scales()]


def load_keymap(chain_manager, channel, scale, tonic):
    """The rows of the pattern grid: (name of scale / map, keymap); keymap: list of
    {"note": MIDI note, "name": key name, "colour": key colour}, name and colour optional.
    scale 0: the synth's custom keymap if there is one; > 1: a scale of scales.json from tonic;
    else chromatic."""
    keymap = []
    # Try to load custom keymap
    if scale == 0:
        map_info = get_custom_keymap(chain_manager, channel)
        if map_info:
            map_name = map_info[0]
            # map_info[1] is the filename of a midnam file
            if isinstance(map_info[1], str) and map_info[1].endswith(".midnam"):
                keymap_fpath = map_info[1]
                logging.info(f"Loading keymap {map_name} for MIDI channel {channel}...")
                try:
                    xml = minidom.parse(keymap_fpath)
                    for note in xml.getElementsByTagName('Note'):
                        try:
                            colour = note.attributes['Colour'].value
                        except Exception:
                            colour = "white"
                        keymap.append({'note': int(note.attributes['Number'].value),
                                       'name': note.attributes['Name'].value,
                                       'colour': colour})
                    return map_name, keymap
                except Exception as e:
                    logging.error(f"Can't load '{keymap_fpath}' => {e}")
            # map[1] is an engine to ask for a custom keymap
            else:
                try:
                    return map_name, map_info[1].get_keymap()
                except Exception:
                    pass

    # Specific scale
    if scale > 1:
        data = load_scales()
        if scale <= len(data):
            scale -= 1  # Offset by -1 because the 0 is used for custom keymap
            for octave in range(0, 9):
                for offset in data[scale]['scale']:
                    note = tonic + offset + octave * 12
                    if note > 127:
                        break
                    keymap.append({"note": note, "name": note_name(note)})
            return data[scale]['name'], keymap

    # Chromatic
    keymap = []
    for note in range(0, 128):
        entry = {"note": note}
        key = note % 12
        entry["colour"] = "black" if key in (1, 3, 6, 8, 10) else "white"
        if key == 0:  # 'C'
            entry["name"] = f"C{note // 12 - 1}"
        keymap.append(entry)
    return "Chromatic", keymap


def note_events(libseq):
    """The note events of the selected pattern: list of (step, note, duration, velocity, offset)"""
    events = []
    evdata = zynseq.event_data()
    index = 0
    while libseq.getEventDataAt(index, evdata) >= 0:
        index += 1
        if evdata.command == zynseq.MIDI_NOTE_ON:
            events.append((evdata.position, evdata.val1_start, evdata.duration, evdata.val2_start, evdata.offset))
    return events


def default_note_evdata(duration=1.0, velocity=100, offset=0.0, stut_speed=0, stut_velfx=0, stut_ramp=0,
                        play_freq=1, stut_freq=1, play_chance=1.0, stut_chance=1.0):
    """Event data for a new note (setNoteData after addNote), with the note-entry values"""
    evdata = zynseq.event_data()
    evdata.set_values(0, offset, duration, 0x90, 0, velocity, 0, 0, stut_speed, stut_velfx, stut_ramp,
                      play_freq, stut_freq, play_chance, stut_chance)
    return evdata
