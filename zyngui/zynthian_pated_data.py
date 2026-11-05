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

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19, 21, 23],
    "minor": [0, 2, 3, 5, 7, 8, 10, 12, 14, 15, 17, 19, 20, 22]
}

CHORD_MODES = [
    "Single note",
    "Chord",
    "Diatonic triads, major key",
    "Diatonic 7ths, major key",
    "Diatonic triads, minor key",
    "Diatonic 7ths, minor key"
]

CHORDS = [
    # Triads
    ["Major", [0, 4, 7]],
    ["Minor", [0, 3, 7]],
    ["Diminished", [0, 3, 6]],
    ["Augmented", [0, 4, 8]],
    # Seventh chords
    ["Major 7th", [0, 4, 7, 11]],  # (maj7)
    ["Minor 7th", [0, 3, 7, 10]],  # (m7)
    ["Dominant 7th", [0, 4, 7, 10]],  # (7)
    ["Half-Diminished 7th", [0, 3, 6, 10]],  # (m7♭5)
    ["Diminished 7th", [0, 3, 6, 9]],  # (dim7)
    ["Minor-Major 7th", [0, 3, 7, 11]],  # (m(maj7))
    ["Augmented Major 7th", [0, 4, 8, 11]],  # (+maj7)
    ["Augmented 7th", [0, 4, 8, 10]],  # (+7)
    # Extended chords
    ["Major 9th", [0, 4, 7, 11, 14]],  # (maj9)
    ["Dominant 9th", [0, 4, 7, 10, 14]],  # (9)
    ["Minor 9th", [0, 3, 7, 10, 14]],  # (m9)
    ["Minor-Major 9th", [0, 3, 7, 11, 14]],  # (m(maj9))
    ["Dominant 11th", [0, 4, 7, 10, 14, 17]],  # (11)
    ["Minor 11th", [0, 3, 7, 10, 14, 17]],  # (m11)
    ["Dominant 13th", [0, 4, 7, 10, 14, 17, 21]],  # (13)
    ["Minor 13th", [0, 3, 7, 10, 14, 17, 21]],  # (m13)
    # Suspended chords
    ["Suspended 2nd", [0, 2, 7]],  # (sus2)
    ["Suspended 4th", [0, 5, 7]],  # (sus4)
    ["7sus4", [0, 5, 7, 10]],
    # Add chords
    ["Add9", [0, 4, 7, 14]],
    ["Minor Add9", [0, 3, 7, 14]],  # (madd9)
    # 6th chords
    ["Major 6th", [0, 4, 7, 9]],  # (6)
    ["Minor 6th", [0, 3, 7, 9]],  # (m6)
    # Altered 7th chords
    ["Half-Diminished Dominant", [0, 4, 6, 10]]  # (7♭5)
]


def diatonic_chord(chord_mode, tonic, trigger_note):
    """Intervals of the diatonic chord on trigger_note (chord modes 2..5), [] if the note is not
    in the key"""
    match chord_mode:
        case 2 | 3:
            scale_template = SCALES["major"]
        case 4 | 5:
            scale_template = SCALES["minor"]
        case _:
            return []
    chord_len = 4 if chord_mode in [3, 5] else 3
    scale_offset = trigger_note % 12 + tonic
    if scale_offset not in scale_template:
        return []  # Trigger note not in diatonic scale
    note_offset = scale_template.index(scale_offset)
    return [scale_template[note_offset + 2 * i] - scale_template[note_offset] for i in range(chord_len)]


def chord_intervals(chord_mode, chord_type, tonic, note):
    """Intervals of the notes entered for note: [0] single note, the chord type's, or the
    diatonic chord's"""
    match chord_mode:
        case 0:
            return [0]
        case 1:
            return CHORDS[chord_type][1]
        case _:
            return diatonic_chord(chord_mode, tonic, note)


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
    """The note events of the selected pattern: list of event_data (copies)"""
    events = []
    evdata = zynseq.event_data()
    index = 0
    while libseq.getEventDataAt(index, evdata) >= 0:
        index += 1
        if evdata.command == zynseq.MIDI_NOTE_ON:
            events.append(zynseq.event_data.from_buffer_copy(evdata))
    return events


def default_note_evdata(duration=1.0, velocity=100, offset=0.0, stut_speed=0, stut_velfx=0, stut_ramp=0,
                        play_freq=1, stut_freq=1, play_chance=1.0, stut_chance=1.0):
    """Event data for a new note (setNoteData after addNote), with the note-entry values"""
    evdata = zynseq.event_data()
    evdata.set_values(0, offset, duration, 0x90, 0, velocity, 0, 0, stut_speed, stut_velfx, stut_ramp,
                      play_freq, stut_freq, play_chance, stut_chance)
    return evdata


# Per-note settings besides velocity and duration (zynthian_gui_pated_notes' edit parameters)

STUT_VFX_OPTIONS = ("FLAT", "FADE-IN", "FADE-OUT")
STUT_RMP_OPTIONS = ("NONE", "SPEED-UP", "SPEED-DOWN")
PLAY_FREQ_OPTIONS = ("NEVER", "ALWAYS", "PLAY/2", "SKIP/2", "PLAY/3", "SKIP/3", "PLAY/4", "SKIP/4", "PLAY/5",
                     "SKIP/5", "PLAY/6", "SKIP/6", "PLAY/7", "SKIP/7", "PLAY/8", "SKIP/8")
STUT_FREQ_OPTIONS = ("NEVER", "ALWAYS", "STUT/2", "SKIP/2", "STUT/3", "SKIP/3", "STUT/4", "SKIP/4", "STUT/5",
                     "SKIP/5", "STUT/6", "SKIP/6", "STUT/7", "SKIP/7", "STUT/8", "SKIP/8")

# key: the event_data field and default_note_evdata argument; kind: "percent" (0..1, edited as
# min..max %), "int" (min..max) or "options" (index into labels); setter: the libseq function
NOTE_PARAMS = (
    {"key": "offset", "name": "Offset", "kind": "percent", "min": 0, "max": 99, "setter": "setNoteOffset"},
    {"key": "stut_speed", "name": "Stutter speed", "kind": "int", "min": 0, "max": 32,
     "setter": "setNoteStutterSpeed"},
    {"key": "stut_velfx", "name": "Stutter velocity", "kind": "options", "labels": STUT_VFX_OPTIONS,
     "setter": "setNoteStutterVelfx"},
    {"key": "stut_ramp", "name": "Stutter ramp", "kind": "options", "labels": STUT_RMP_OPTIONS,
     "setter": "setNoteStutterRamp"},
    {"key": "play_freq", "name": "Play frequency", "kind": "options", "labels": PLAY_FREQ_OPTIONS,
     "setter": "setNotePlayFreq"},
    {"key": "play_chance", "name": "Play chance", "kind": "percent", "min": 0, "max": 100,
     "setter": "setNotePlayChance"},
    {"key": "stut_freq", "name": "Stutter frequency", "kind": "options", "labels": STUT_FREQ_OPTIONS,
     "setter": "setNoteStutterFreq"},
    {"key": "stut_chance", "name": "Stutter chance", "kind": "percent", "min": 0, "max": 100,
     "setter": "setNoteStutterChance"},
)

NOTE_PARAM_DEFAULTS = {"offset": 0.0, "stut_speed": 0, "stut_velfx": 0, "stut_ramp": 0, "play_freq": 1,
                       "play_chance": 1.0, "stut_freq": 1, "stut_chance": 1.0}


def note_param_text(param, value):
    """A NOTE_PARAMS value as shown, e.g. "25%", "4" or "FADE-IN"."""
    if param["kind"] == "percent":
        return f"{round(100 * value)}%"
    if param["kind"] == "options":
        labels = param["labels"]
        return labels[value] if 0 <= value < len(labels) else str(value)
    return str(value)


def set_note_param(libseq, step, note, param, value):
    """Set a NOTE_PARAMS value (stored form: 0..1 for percent) of the note at step"""
    getattr(libseq, param["setter"])(step, note, value)


def note_muted(evdata):
    """True if the note never plays (drawn faded)"""
    return evdata.play_freq == 0 or evdata.play_chance == 0


def stutter_muted(evdata):
    return evdata.stut_freq == 0 or evdata.stut_chance == 0


def note_label(evdata):
    """The text on a note: its play frequency or chance, else its stutter's; "" for none"""
    if evdata.play_freq > 1:
        return PLAY_FREQ_OPTIONS[evdata.play_freq]
    if evdata.play_chance < 1.0:
        return f"{round(100 * evdata.play_chance)}%"
    if evdata.stut_speed > 0:
        if evdata.stut_freq > 1:
            return STUT_FREQ_OPTIONS[evdata.stut_freq]
        if evdata.stut_chance < 1.0:
            return f"{round(100 * evdata.stut_chance)}%"
    return ""
