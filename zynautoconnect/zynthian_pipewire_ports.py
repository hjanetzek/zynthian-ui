# -*- coding: utf-8 -*-
# ********************************************************************
# ZYNTHIAN PROJECT: Zynthian Autoconnector
#
# Names of the MIDI ports of PipeWire's ALSA bridge (pipewire-jack)
#
# Copyright (C) 2026 Hannes Janetzek
#
# ********************************************************************
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ********************************************************************

# With jackd, the hardware MIDI ports carry the ALSA names in their aliases
# ("in-hw-<card>-..."), from which build_midi_port_name makes the uid
# "USB:<bus path>/<card name> IN <n>". The part after "/" is the device ID that
# the controller drivers (ctrldev) list in dev_ids, and dev_in_2_dev_out finds
# the output of an input by its uid with "IN" replaced by "OUT".
#
# PipeWire's JACK ports have no aliases by default (jack.fill-aliases = false),
# and its ALSA MIDI bridge names them "Midi-Bridge:<client>:<port> (capture)"
# and "... (playback)", e.g. "Midi-Bridge:Scarlett 18i20 USB: MIDI 1 (capture)".
# Without a "/" in the uid there is no device ID: no driver matches, and the
# output port of a device is not found.
#
# This module builds uids of the same form for these ports, so the device IDs
# are those of ZynthianOS:
#   "PW:<client>/<client> IN <n>" for a capture port (MIDI from the device),
#   "PW:<client>/<client> OUT <n>" for a playback port (MIDI to the device),
# with <n> the 1-based index of the port among the client's ports of the same
# direction. Input and output differ only in IN/OUT, as dev_in_2_dev_out needs.
#
# It has no dependencies, so it can be tested without JACK.

PIPEWIRE_MIDI_BRIDGE = "Midi-Bridge:"
CAPTURE_SUFFIX = " (capture)"
PLAYBACK_SUFFIX = " (playback)"


def is_pipewire_midi_port(port_name):
    """True if port_name is a port of PipeWire's ALSA MIDI bridge"""

    return port_name.startswith(PIPEWIRE_MIDI_BRIDGE)


def split_pipewire_midi_port(port_name):
    """Split the name of a PipeWire MIDI bridge port

    port_name : Full JACK port name, e.g. "Midi-Bridge:Launch Control XL: MIDI 1 (capture)"
    returns : Tuple (client, port, is_capture), e.g. ("Launch Control XL", "MIDI 1", True),
              or None if it is not such a port
    """

    if not is_pipewire_midi_port(port_name):
        return None
    name = port_name[len(PIPEWIRE_MIDI_BRIDGE):]
    if name.endswith(CAPTURE_SUFFIX):
        is_capture = True
        name = name[:-len(CAPTURE_SUFFIX)]
    elif name.endswith(PLAYBACK_SUFFIX):
        is_capture = False
        name = name[:-len(PLAYBACK_SUFFIX)]
    else:
        return None
    client, sep, port = name.partition(":")
    if not sep:
        return None
    return client.strip(), port.strip(), is_capture


def pipewire_midi_port_name(port_name, sibling_names=None):
    """Get uid and friendly name of a PipeWire MIDI bridge port

    port_name : Full JACK port name
    sibling_names : Full names of all ports of the bridge with the same direction, in JACK's
                    order (None or empty: the port is the client's only one)
    returns : Tuple (uid, name) or None if it is not such a port
    """

    parts = split_pipewire_midi_port(port_name)
    if parts is None:
        return None
    client, port, is_capture = parts
    # The ports of the same client and direction, in JACK's order
    same = []
    for name in sibling_names or []:
        sibling = split_pipewire_midi_port(name)
        if sibling and sibling[0] == client and sibling[2] == is_capture and name not in same:
            same.append(name)
    if port_name not in same:
        same.append(port_name)
    index = same.index(port_name) + 1
    direction = "IN" if is_capture else "OUT"
    uid = f"PW:{client}/{client} {direction} {index}"
    if len(same) > 1:
        name = f"{client} {index}"
    else:
        name = client
    return uid, name


def dev_out_uid(uid_in):
    """The uid of the output port of the device whose input port has the uid uid_in

    Replaces only the direction of the device ID ("<name> IN <n>" -> "<name> OUT <n>"),
    not every "IN" of the name (an "APC MINI IN 1" stays an APC MINI).
    returns : The output uid or None if uid_in has no direction
    """

    head, sep, tail = uid_in.rpartition(" IN ")
    if not sep:
        return None
    return f"{head} OUT {tail}"
