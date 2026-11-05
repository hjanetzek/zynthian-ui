# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Pattern editor: Standard MIDI File import and export (UI-independent part of
# zynthian_gui_pated_base), used by the Tk and Qt UIs.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

import logging
import os

from zynconf import zynthian_paths
from zynlibs.zynsmf import zynsmf
from zyngui.zynthian_pated_data import note_events

SMF_EXPORT_DIR = f"{zynthian_paths.my_data_dir}/files/Midi/patterns"
PATTERNS_DIR = f"{zynthian_paths.my_data_dir}/files/Patterns"

# List of GM instruments
GM_INSTRUMENTS = {
    # Piano
    0: "Acoustic Grand Piano",
    1: "Bright Acoustic Piano",
    2: "Electric Grand Piano",
    3: "Honky-tonk Piano",
    4: "Electric Piano 1",
    5: "Electric Piano 2",
    6: "Harpsichord",
    7: "Clavinet",
    # Chromatic Percussion:
    9: "Celesta",
    10: "Glockenspiel",
    11: "Music Box",
    12: "Vibraphone",
    13: "Marimba",
    14: "Xylophone",
    15: "Tubular Bells",
    16: "Dulcimer",
    # Organ:
    17: "Drawbar Organ",
    18: "Percussive Organ",
    19: "Rock Organ",
    20: "Church Organ",
    21: "Reed Organ",
    22: "Accordion",
    23: "Harmonica",
    24: "Tango Accordion",
    # Guitar:
    25: "Acoustic Guitar (nylon)",
    26: "Acoustic Guitar (steel)",
    27: "Electric Guitar (jazz)",
    28: "Electric Guitar (clean)",
    29: "Electric Guitar (muted)",
    30: "Overdriven Guitar",
    31: "Distortion Guitar",
    32: "Guitar harmonics",
    # Bass:
    33: "Acoustic Bass",
    34: "Electric Bass (finger)",
    35: "Electric Bass (pick)",
    36: "Fretless Bass",
    37: "Slap Bass 1",
    38: "Slap Bass 2",
    39: "Synth Bass 1",
    40: "Synth Bass 2",
    # Strings:
    41: "Violin",
    42: "Viola",
    43: "Cello",
    44: "Contrabass",
    45: "Tremolo Strings",
    46: "Pizzicato Strings",
    47: "Orchestral Harp",
    48: "Timpani",
    49: "String Ensemble 1",
    50: "String Ensemble 2",
    51: "Synth Strings 1",
    52: "Synth Strings 2",
    53: "Choir Aahs",
    54: "Voice Oohs",
    55: "Synth Voice",
    56: "Orchestra Hit",
    # Brass:
    57: "Trumpet",
    58: "Trombone",
    59: "Tuba",
    60: "Muted Trumpet",
    61: "French Horn",
    62: "Brass Section",
    63: "Synth Brass 1",
    64: "Synth Brass 2",
    # Reed:
    65: "Soprano Sax",
    66: "Alto Sax",
    67: "Tenor Sax",
    68: "Baritone Sax",
    69: "Oboe",
    70: "English Horn",
    71: "Bassoon",
    72: "Clarinet",
    # Pipe:
    73: "Piccolo",
    74: "Flute",
    75: "Recorder",
    76: "Pan Flute",
    77: "Blown Bottle",
    78: "Shakuhachi",
    79: "Whistle",
    80: "Ocarina",
    # Synth Lead:
    81: "Lead 1 (square)",
    82: "Lead 2 (sawtooth)",
    83: "Lead 3 (calliope)",
    84: "Lead 4 (chiff)",
    85: "Lead 5 (charang)",
    86: "Lead 6 (voice)",
    87: "Lead 7 (fifths)",
    88: "Lead 8 (bass + lead)",
    # Synth Pad:
    89: "Pad 1 (new age)",
    90: "Pad 2 (warm)",
    91: "Pad 3 (polysynth)",
    92: "Pad 4 (choir)",
    93: "Pad 5 (bowed)",
    94: "Pad 6 (metallic)",
    95: "Pad 7 (halo)",
    96: "Pad 8 (sweep)",
    # Synth Effects:
    97: "FX 1 (rain)",
    98: "FX 2 (soundtrack)",
    99: "FX 3 (crystal)",
    100: "FX 4 (atmosphere)",
    101: "FX 5 (brightness)",
    102: "FX 6 (goblins)",
    103: "FX 7 (echoes)",
    104: "FX 8 (sci-fi)",
    # Ethnic:
    105: "Sitar",
    106: "Banjo",
    107: "Shamisen",
    108: "Koto",
    109: "Kalimba",
    110: "Bag pipe",
    111: "Fiddle",
    112: "Shanai",
    # Percussive:
    113: "Tinkle Bell",
    114: "Agogo",
    115: "Steel Drums",
    116: "Woodblock",
    117: "Taiko Drum",
    118: "Melodic Tom",
    119: "Synth Drum",
    # Sound effects:
    120: "Reverse Cymbal",
    121: "Guitar Fret Noise",
    122: "Breath Noise",
    123: "Seashore",
    124: "Bird Tweet",
    125: "Telephone Ring",
    126: "Helicopter",
    127: "Applause",
    128: "Gunshot"
}

GM2_DRUMKITS = {
    0: "Standard Kit",
    8: "Room Kit",
    16: "Power Kit",
    24: "Electronic Kit",
    25: "TR-808 Kit",
    32: "Jazz Kit",
    40: "Brush Kit",
    48: "Orchestra Kit",
    56: "Sound FX Kit"
}


def _load(fpath):
    """A loaded SMF handle, or None (logged) if unreadable or empty; remove it with libsmf.removeSmf"""
    smf = zynsmf.libsmf.addSmf()
    if not zynsmf.load(smf, fpath):
        logging.error(f"Failed to load SMF file '{fpath}'")
        zynsmf.libsmf.removeSmf(smf)
        return None
    if zynsmf.libsmf.getEvents(smf, -1) == 0:
        logging.warning(f"Empty SMF file '{fpath}'")
        zynsmf.libsmf.removeSmf(smf)
        return None
    return smf


def _midi_events(smf):
    """(time in ticks, code (status >> 4), channel) of the file's MIDI events, in time order; the
    file's position is at the event, for its values"""
    zynsmf.libsmf.setPosition(smf, 0)
    while zynsmf.libsmf.getEvent(smf, True):
        if zynsmf.libsmf.getEventType() == zynsmf.EVENT_TYPE_MIDI:
            status = zynsmf.libsmf.getEventStatus()
            yield zynsmf.libsmf.getEventTime(), (status & 0xf0) >> 4, status & 0x0f


def program_label(chan, program):
    """The instrument of a channel from its program change (GM; channel 10 drum kits)"""
    if chan == 9:
        kit = GM2_DRUMKITS.get(program) if program is not None else None
        return f"Drums & Perc ({kit})" if kit else "Drums & Perc"
    if program is not None:
        return GM_INSTRUMENTS.get(program, "???")
    return "???"


def analyze_smf(fpath, bpb):
    """The channels of a MIDI file with notes or CCs, and its length in bars (from the first bar
    with events to the last note, rounded up beyond 10 % of a bar):
    ([(channel 0..15, "CH n: instrument"), ...], n_bars), or None if unreadable or empty"""
    smf = _load(fpath)
    if smf is None:
        return None
    try:
        ticks_per_bar = bpb * zynsmf.libsmf.getTicksPerQuarterNote(smf)
        start_time = end_time = None
        counts = [0] * 16
        programs = [None] * 16
        for evtime, code, chan in _midi_events(smf):
            if code in (0x8, 0x9, 0xB):
                counts[chan] += 1
                if start_time is None:
                    start_time = (evtime // ticks_per_bar) * ticks_per_bar
                if code in (0x8, 0x9):
                    end_time = evtime
            elif code == 0xC:
                # The last program change of each channel
                programs[chan] = zynsmf.libsmf.getEventValue1()
    finally:
        zynsmf.libsmf.removeSmf(smf)
    n_bars = 0
    if start_time is not None and end_time is not None:
        dtime = end_time - start_time
        n_bars = dtime // ticks_per_bar
        if dtime and (dtime % ticks_per_bar) / dtime > 0.1:
            n_bars += 1
    channels = [(chan, f"CH {chan + 1}: {program_label(chan, programs[chan])}")
                for chan in range(16) if counts[chan]]
    logging.info(f"SMF '{fpath}': channels {channels}, {n_bars} bars")
    return channels, max(1, n_bars)


def import_smf(libseq, fpath, midi_chan, bpb):
    """Notes and CCs of midi_chan in a MIDI file into the selected pattern, replacing its notes:
    from the file's first bar with events, as far as the pattern is long. Returns the number of
    notes, or None if the file can't be read"""
    smf = _load(fpath)
    if smf is None:
        return None
    try:
        ticks_per_beat = zynsmf.libsmf.getTicksPerQuarterNote(smf)
        ticks_per_bar = bpb * ticks_per_beat
        steps_per_beat = libseq.getStepsPerBeat()
        ticks_per_step = ticks_per_beat / steps_per_beat
        ticks_in_pattern = ticks_per_beat * libseq.getSteps() / steps_per_beat
        libseq.clearNotes()
        start_time = None
        note_on = [None] * 128      # [time, velocity] of a sounding note, for its duration
        n_notes = 0
        for evtime, code, chan in _midi_events(smf):
            if chan != midi_chan or code not in (0x8, 0x9, 0xB):
                continue
            if start_time is None:
                start_time = (evtime // ticks_per_bar) * ticks_per_bar
            elif evtime > start_time + ticks_in_pattern:
                break
            value1 = zynsmf.libsmf.getEventValue1()
            value2 = zynsmf.libsmf.getEventValue2()
            if code == 0xB:
                step = int((evtime - start_time) / ticks_per_step)
                libseq.addControl(step, value1, value2, value2, 1, 0)
            elif code == 0x9 and value2:
                note_on[value1] = [evtime, value2]
            elif note_on[value1]:
                on_time, velocity = note_on[value1]
                fstep = (on_time - start_time) / ticks_per_step
                step = int(fstep)
                libseq.addNote(step, value1, velocity, (evtime - on_time) / ticks_per_step, fstep - step)
                note_on[value1] = None
                n_notes += 1
        return n_notes
    finally:
        zynsmf.libsmf.removeSmf(smf)


def export_smf(libseq, fpath, channel):
    """The selected pattern's notes (with their offsets) as a MIDI file on channel, with the
    current tempo"""
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    smf = zynsmf.libsmf.addSmf()
    try:
        zynsmf.libsmf.addTempo(smf, 0, libseq.getTempo())
        ticks_per_step = zynsmf.libsmf.getTicksPerQuarterNote(smf) / libseq.getStepsPerBeat()
        for ev in note_events(libseq):
            zynsmf.libsmf.addNote(smf, 0, int((ev.position + ev.offset) * ticks_per_step),
                                  max(1, int(ev.duration * ticks_per_step)), channel, ev.val1_start, ev.val2_start)
        zynsmf.libsmf.setEndOfTrack(smf, 0, int(libseq.getSteps() * ticks_per_step))
        return zynsmf.save(smf, fpath)
    finally:
        zynsmf.libsmf.removeSmf(smf)
