# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian Control Device Driver
#
# DrivenByMoss on zynthian: reports zynthian's state to the core
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

"""The reports of zynthian's model to the core (doc/HOST_BRIDGE_GUIDE.md §2, §3.3).

``ZynReporter`` reuses the change tracking of the reference host's ``Reporter`` (the last text
per address, dumps after ``refresh``, the report again 300 ms after a value command) with its
own collectors: the host features, the tracks, the effect tracks and the master. All items are
reported with their absolute positions (§6 rule 4); ``/track/offset`` turns on the core's host
paging, ``/host/features`` lists the command forms of ``ZynCommandHandler``.

Not reported (phase 1), so the core keeps its defaults for them: the transport, scenes and
slots, devices and parameters, the clip, markers, the browser, ``/track/<p>/active`` (zynthian
has no deactivated chains), ``/track/hasPrevious|hasNext`` and ``/track/pinned``.
"""

from dbm_host import Reporter


class ZynReporter(Reporter):

    def __init__(self, daw, banks, clock=lambda: 0.0, features=lambda: []):
        super().__init__(daw, banks, clock, features)
        self.collectors = [
            Reporter.collect_host_features,
            ZynReporter.collect_tracks,
            ZynReporter.collect_effect_tracks,
            ZynReporter.collect_master,
        ]
        self._counts = {"track": 0, "fxtrack": 0}

    # The parts of a channel

    def collect_channel(self, prefix, channel):
        self.put(prefix + "name", channel.name)
        self.put(prefix + "color", channel.color)
        self.put(prefix + "mute", channel.mute)
        self.put(prefix + "solo", channel.solo)
        self.put(prefix + "volume", channel.volume.value)
        self.put_parameter_text(prefix + "volume/str", channel.volume)
        self.put(prefix + "pan", channel.pan.value)
        self.put_parameter_text(prefix + "pan/str", channel.pan)

    def collect_vu(self, prefix, channel):
        left, right = channel.vu()
        self.put(prefix + "vuleft", left)
        self.put(prefix + "vuright", right)
        self.put(prefix + "vu", (left + right) / 2.0)

    def collect_track_flags(self, prefix, track):
        self.put(prefix + "recarm", track.arm)
        self.put(prefix + "canHoldNotes", track.can_hold_notes)
        self.put(prefix + "canHoldAudio", track.can_hold_audio)

    def collect_removed(self, bank, count):
        """Positions which no longer exist (a chain was removed) are reported as not existing."""
        for position in range(count, self._counts[bank]):
            self.put(f"/{bank}/{position}/exists", 0)
        self._counts[bank] = count

    # The collectors

    def collect_tracks(self):
        tracks = self.daw.track_list(self.banks.full_flat_track_list)
        selected = next((position for position, track in enumerate(tracks) if track.selected), -1)
        self.put("/track/offset", self.banks.track_offset)
        # A deselection outside of the list (the selected track was removed)
        if self._last_selected != selected and self._last_selected >= len(tracks):
            self.put(f"/track/{self._last_selected}/select", False)
        self._last_selected = selected
        for position, track in enumerate(tracks):
            prefix = f"/track/{position}/"
            self.put(prefix + "exists", 1)
            self.put(prefix + "number", position)
            self.put(prefix + "type", track.type_name)
            if position != selected:
                self.put(prefix + "select", False)
            self.collect_track_flags(prefix, track)
            self.collect_vu(prefix, track)
            self.collect_channel(prefix, track)
            self.collect_sends(prefix, track, with_color=True)
        self.collect_removed("track", len(tracks))
        self.put("/track/count", len(tracks))
        if selected >= 0:
            self.put(f"/track/{selected}/select", True)

    def collect_effect_tracks(self):
        tracks = self.daw.effect_tracks()
        self.put("/fxtrack/offset", self.banks.fx_track_offset)
        for position, track in enumerate(tracks):
            prefix = f"/fxtrack/{position}/"
            self.put(prefix + "exists", 1)
            self.put(prefix + "number", position)
            self.put(prefix + "type", track.type_name)
            self.put(prefix + "select", track.selected)
            self.collect_track_flags(prefix, track)
            self.collect_channel(prefix, track)
            self.collect_sends(prefix, track, with_color=False)
        self.collect_removed("fxtrack", len(tracks))
        self.put("/fxtrack/count", len(tracks))

    def collect_master(self):
        master = self.daw.master()
        if master is None:
            return
        self.put("/master/select", master.selected)
        self.collect_vu("/master/", master)
        self.collect_channel("/master/", master)
