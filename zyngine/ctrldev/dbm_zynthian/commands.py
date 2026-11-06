# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian Control Device Driver
#
# DrivenByMoss on zynthian: executes the core's commands on zynthian
#
# Copyright (C) 2026 Hannes Janetzek
#
# ******************************************************************************
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
# ******************************************************************************

"""The core's commands on zynthian (doc/HOST_BRIDGE_GUIDE.md §4.1, §4.3, §4.4).

``ZynCommandHandler`` reuses the reference host's ``CommandHandler`` for the parsing of the
commands (the value suffixes ``/inc``, ``/reset``, ``/immediately``), the dispatch per
processor, the report again after a value command and the log of unhandled commands
(``Not handled yet: …``, once per command), with zynthian's handlers instead of the simulated
DAW's. The host features are those of the registered handlers.

Handled (phase 1): ``refresh``, ``bank``, ``track <p>/…`` and ``fxtrack <p>/…`` (select,
volume, pan, mute, solo, solo/toggle, recarm, name, send/<s>/volume), ``track
selectPrevious|selectNext``, ``master …``. Everything else is logged as not handled, e.g. the
transport, scenes and slots, devices, ``send/<s>/active`` (zynthian's sends have no switch).
"""

import logging
from collections import deque

from dbm_host import CommandHandler
from dbm_host.commands import parse_index

logger = logging.getLogger("dbm_zynthian")

# The last commands kept in ``log`` (for tests and debugging; the reference host keeps all)
LOG_SIZE = 200

TRACK_FEATURES = ("valueInc", "valueReset", "immediately", "soloToggle")


class ZynCommandHandler(CommandHandler):

    def __init__(self, daw, banks, reporter, clock=lambda: 0.0):
        super().__init__(daw, banks, reporter, clock)
        # Only zynthian's handlers and their features
        self.handlers = {}
        self.features = set()
        self.log = deque(maxlen=LOG_SIZE)
        self.register("refresh", self._refresh)
        self.register("bank", self._bank)
        self.register("track", self._track, TRACK_FEATURES)
        self.register("fxtrack", self._fx_track)
        self.register("master", self._master)

    def configure(self):
        """No clip launcher navigator and no step grids yet (phase 3)."""
        self.navigator = None
        self.note_grids = []
        self.reporter.note_grids = []

    def set_value(self, parameter, cmd):
        """No undo history in zynthian."""
        self._apply_value(parameter, cmd)

    # Tracks

    def _track(self, cmd):
        c = cmd.command
        if c == "indicate":
            return True  # No clip launcher (phase 3)
        if c in ("selectPrevious", "selectNext"):
            self.select_neighbour(-1 if c == "selectPrevious" else 1)
            return True
        parts = cmd.parts
        tracks = self.daw.track_list(self.banks.full_flat_track_list)
        position = parse_index(parts[0]) if parts else -1
        if not 0 <= position < len(tracks) or len(parts) < 2:
            return False
        return self.track_command(tracks[position], parts[1:], cmd)

    def _fx_track(self, cmd):
        if cmd.command == "indicate":
            return True
        parts = cmd.parts
        tracks = self.daw.effect_tracks()
        position = parse_index(parts[0]) if parts else -1
        if not 0 <= position < len(tracks) or len(parts) < 2:
            return False
        return self.track_command(tracks[position], parts[1:], cmd)

    def _master(self, cmd):
        master = self.daw.master()
        if master is None:
            return False
        return self.channel_command(master, cmd.parts, cmd)

    def select_neighbour(self, direction):
        tracks = self.daw.track_list(self.banks.full_flat_track_list)
        selected = next((position for position, track in enumerate(tracks) if track.selected), -1)
        position = selected + direction
        if selected >= 0 and 0 <= position < len(tracks):
            tracks[position].select()

    def track_command(self, track, sub, cmd):
        if sub == ["recarm"]:
            track.set_arm(cmd.flag)
            return True
        if sub[0] == "send":
            return self.send_command(track, sub[1:], cmd)
        return self.channel_command(track, sub, cmd)

    def channel_command(self, channel, sub, cmd):
        if not sub:
            return False
        name = sub[0]
        if sub == ["select"]:
            if cmd.flag:
                channel.select()
        elif sub == ["name"]:
            if cmd.text is None:
                return False
            channel.rename(cmd.text)
        elif not channel.has_mixer and name in ("mute", "solo", "volume", "pan"):
            logger.debug("No mixer strip for %s %s", cmd.processor, cmd.full_command)
        elif sub == ["mute"]:
            channel.set_mute(cmd.flag)
        elif sub == ["solo"]:
            channel.set_solo(cmd.flag)
        elif sub == ["solo", "toggle"]:
            channel.toggle_solo()
        elif name in ("volume", "pan"):
            return self.value_command(channel.volume if name == "volume" else channel.pan, sub[1:], cmd)
        else:
            return False
        return True

    def send_command(self, track, sub, cmd):
        """``send/<s>/volume[/touch|/indicate]``; ``send/<s>/active`` is not handled (no switch)."""
        sends = track.sends
        index = parse_index(sub[0]) if sub else -1
        if not 0 <= index < min(len(sends), self.banks.num_sends) or len(sub) < 2:
            return False
        if sub[1] == "volume":
            return self.value_command(sends[index].volume, sub[2:], cmd)
        return False
