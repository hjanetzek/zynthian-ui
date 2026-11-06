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

Phase 2 adds the transport (``collect_transport``, only with zynseq) and the cursor device with
its siblings and parameter pages (``collect_device``).

Not reported, so the core keeps its defaults for them: scenes and slots, the clip, markers, the
browser, ``/primary``, ``/drum``, ``/eq``, the arranger position and loop, ``/track/<p>/active``
(zynthian has no deactivated chains), ``/track/hasPrevious|hasNext``, ``/track/pinned``,
``/device/pinned``.
"""

import logging
import math

from dbm_host import Reporter
from dbm_host.reporter import NUM_SIBLINGS

from zyngine.ctrldev.dbm_zynthian.device import PARAMS_PER_PAGE


class ZynReporter(Reporter):

    def __init__(self, daw, banks, clock=lambda: 0.0, features=lambda: []):
        super().__init__(daw, banks, clock, features)
        self.collectors = [
            Reporter.collect_host_features,
            ZynReporter.collect_tracks,
            ZynReporter.collect_effect_tracks,
            ZynReporter.collect_master,
            ZynReporter.collect_project,
            ZynReporter.collect_transport,
            ZynReporter.collect_device,
        ]
        self._counts = {"track": 0, "fxtrack": 0}
        self._failed = set()

    def collect(self):
        """As Reporter.collect, but a collector that fails (a zynthian object in an unexpected
        state, a missing library function) is logged once and skipped: the others still report."""
        self.apply_pending_forgets()
        for collector in self.collectors:
            try:
                collector(self)
            except Exception as e:
                if collector.__name__ not in self._failed:
                    self._failed.add(collector.__name__)
                    logging.getLogger("dbm_zynthian").error("Reporter %s failed: %s", collector.__name__, e)
        return self.take()

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

    def collect_project(self):
        """zynthian has no undo history (only the pattern editor's): nothing to undo or redo."""
        self.put("/project/canUndo", False)
        self.put("/project/canRedo", False)

    def collect_transport(self):
        transport = self.daw.transport
        if transport is None or not transport.available:
            return
        self.put("/play", transport.playing)
        self.put("/tempo", transport.tempo)
        self.put("/numerator", transport.numerator)
        self.put("/denominator", 4)
        self.put("/click", transport.metronome)
        volume = transport.metronome_volume
        self.put("/click/volume", volume)
        self.put("/click/volumeStr", f"{20.0 * math.log10(volume):.1f} dB" if volume > 0 else "-Inf dB")

    def num_param_pages(self):
        return max(0, int(self.banks.setup.get("numParamPages", 8)))

    def collect_device(self):
        """The cursor device, the sibling window and the parameter pages (as the reference
        host's collect_device and collect_pages)."""
        chain = self.daw.devices
        devices = chain.devices()
        device = chain.cursor()
        exists = device is not None
        position = devices.index(device) if exists else -1
        self.put("/device/count", len(devices))
        self.put("/device/exists", exists)
        self.put("/device/position", position)
        self.put("/device/name", device.name if exists else "")
        self.put("/device/bypass", exists and not device.enabled)
        self.put("/device/window", False)
        self.put("/device/expand", False)
        self.put("/device/hasDrumPads", False)
        self.put("/device/hasLayers", False)
        for index in range(NUM_SIBLINGS):
            sibling_position = chain.sibling_offset + index
            sibling = devices[sibling_position] if sibling_position < len(devices) else None
            prefix = f"/device/sibling/{index + 1}/"
            self.put(prefix + "name", sibling.name if sibling is not None else "")
            self.put(prefix + "bypass", sibling is not None and not sibling.enabled)
            self.put(prefix + "position", sibling_position if sibling is not None else -1)
            self.put(prefix + "selected", sibling is not None and sibling_position == position)
        num_pages = self.num_param_pages()
        pages = device.page_names() if exists else []
        used = min(len(pages), num_pages)
        for index in range(num_pages * PARAMS_PER_PAGE):
            prefix = f"/device/param/{index}/"
            parameter = device.parameter(index) if exists and index < used * PARAMS_PER_PAGE else None
            if parameter is not None and parameter.exists:
                self.put(prefix + "name", parameter.name)
                self.put(prefix + "value", parameter.value)
                self.put_parameter_text(prefix + "value/str", parameter)
            else:
                self.put(prefix + "name", "")
                self.put(prefix + "value", 0.0)
                self.put_displayed(prefix + "value/str", "", ["", ""])
            self.put(prefix + "steps", -1)
            self.put(prefix + "modulated", parameter.value if parameter is not None and parameter.exists else 0.0)
        self.put("/device/param/count", used * PARAMS_PER_PAGE)
        for index in range(used):
            self.put(f"/device/page/{index}/name", pages[index])
        self.put("/device/page/count", used)
        self.put("/device/page/selected", device.selected_page if exists else -1)
