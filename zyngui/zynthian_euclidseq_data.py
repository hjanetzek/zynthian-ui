# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Euclidean sequencer widget model: UI-independent part of zynthian_widget_euclidseq (the
# EuclidSeq6 Pure Data patch). Six channels; the state follows the patch's OSC messages
# (/euclid/...), changes are sent back, and on each clock trigger the hits of every channel are
# sent as notes (/euclid/note/<ch>). Used by the Tk and Qt UIs, which draw from the geometry
# functions (unit coordinates, centre 0,0, radius 1, y down).
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

import re
import math
import logging

import pyliblo3 as liblo

MODES = ["polygon", "euclidean", "interval"]
ALLOWED_INTERVALS = list(range(1, 17))

# The 16 step positions of the euclidean view (model coordinates, centre 25, radius 15)
_X16 = [25, 31, 36, 39, 40, 39, 36, 31, 25, 19, 14, 11, 10, 11, 14, 19]
_Y16 = [10, 11, 14, 19, 25, 31, 36, 39, 40, 39, 36, 31, 25, 19, 14, 11]


def _euclidean_patterns(num_steps):
    all_patterns = [[0] * num_steps]
    for hits in range(1, num_steps + 1):
        pattern = [0] * num_steps
        for i in range(num_steps):
            if math.floor(i * hits / num_steps) != math.floor((i - 1) * hits / num_steps):
                pattern[i] = 1
        all_patterns.append(pattern)
    return all_patterns


class EuclidSeqModel:

    def __init__(self, on_change=None):
        self.on_change = on_change   # called after every state change (from the OSC thread too)
        self.channels = 6
        self.max_steps = 16
        self.max_channel_length = 32
        self.max_hits = 32
        self.max_note = 128
        self.hits = [3, 4, 5, 3, 2, 4]
        self.offset = [0, 2, 0, 8, 3, 9]
        self.mute = [False] * self.channels
        self.limit = [16] * self.channels
        self.playing_step = [0] * self.channels
        self.note_numbers = [36, 38, 40, 42, 44, 48]
        self.display_mode = "euclidean"
        self.interval_value = [ALLOWED_INTERVALS[0]] * self.channels
        self.euclidean_patterns = _euclidean_patterns(self.max_steps)
        self.offset_buf = [[False] * self.max_steps for _ in range(self.channels)]
        self.select_ch = 0
        self.processor = None
        self.osc_target = None
        self.update_offset_buffers()

    # Engine connection

    def set_processor(self, processor):
        """Receive the patch's OSC messages through the engine, send to its OSC target"""
        if self.processor != processor:
            self.processor = processor
            if hasattr(processor, 'engine'):
                processor.engine.osc_reset_child_handlers()
                processor.engine.osc_add_child_handler(self.handle_osc_message)
                processor.engine.osc_flush_unhandle_messages()
        if hasattr(processor, 'engine') and self.osc_target != processor.engine.osc_target:
            self.osc_target = processor.engine.osc_target

    def send(self, path, *args):
        if self.osc_target:
            try:
                liblo.send(self.osc_target, path, *args)
            except Exception as e:
                logging.warning(f"euclidseq OSC {path}: {e}")

    def _changed(self):
        if self.on_change:
            self.on_change()

    # OSC from the patch

    def handle_osc_message(self, path, args):
        """Route an OSC message from the patch; True if handled"""
        if path == "/euclid/mode":
            if args and args[0] in MODES:
                self.display_mode = args[0]
                self._changed()
            return True
        if path == "/euclid/ch":
            if args and 0 <= args[0] < self.channels:
                self.select_ch = args[0]
                self._changed()
            return True
        if path == "/euclid/trigger":
            self.handle_trigger(args)
            return True
        match = re.match(r"/euclid/(\w+)_(\d+)", path)
        if match:
            self._handle_channel_param(match.group(1), int(match.group(2)) - 1, args[0])
            return True
        return False

    def _handle_channel_param(self, key, ch, val):
        if not 0 <= ch < self.channels:
            return
        if key == "hits":
            if 0 <= val <= self.max_hits:
                self.hits[ch] = val
            self.update_offset_buffers()
        elif key == "offset":
            if 0 <= val < self.max_steps:
                self.offset[ch] = val
            self.update_offset_buffers()
        elif key == "limit":
            if 0 < val <= self.max_channel_length:
                self.limit[ch] = val
        elif key == "mute":
            self.mute[ch] = bool(val)
        elif key == "note_num":
            if 1 <= val <= self.max_note:
                self.note_numbers[ch] = val
        elif key == "interval_val":
            if val in ALLOWED_INTERVALS:
                self.interval_value[ch] = val
        self._changed()

    def handle_trigger(self, args):
        """A clock step: advance every channel, send the notes of the channels that hit"""
        if not args or args[0] != 1:
            return
        for i in range(self.channels):
            if self.limit[i] > 0:
                self.playing_step[i] = (self.playing_step[i] + 1) % self.limit[i]
        for k in range(self.channels):
            if not self.mute[k] and self.is_hit(k, self.playing_step[k]):
                self.send(f"/euclid/note/{k}", self.note_numbers[k], 100)
        self._changed()

    # Changes from the UI (sent to the patch)

    def adjust_param(self, key, direction):
        """Change the selected channel's length, hits, offset, interval, or the mode, by one"""
        ch = self.select_ch
        path = val = None
        if key == "mode":
            self.display_mode = MODES[(MODES.index(self.display_mode) + direction) % len(MODES)]
            path, val = "/euclid/mode", self.display_mode
        elif key == "length":
            self.limit[ch] = max(1, min(self.limit[ch] + direction, self.max_channel_length))
            path, val = f"/euclid/limit_{ch + 1}", self.limit[ch]
        elif key == "hits":
            self.hits[ch] = max(0, min(self.hits[ch] + direction, self.max_hits))
            self.update_offset_buffers()
            path, val = f"/euclid/hits_{ch + 1}", self.hits[ch]
        elif key == "offset":
            self.offset[ch] = (self.offset[ch] + direction) % self.max_steps
            self.update_offset_buffers()
            path, val = f"/euclid/offset_{ch + 1}", self.offset[ch]
        elif key == "interval" and self.display_mode == "interval":
            i = (ALLOWED_INTERVALS.index(self.interval_value[ch]) + direction) % len(ALLOWED_INTERVALS)
            self.interval_value[ch] = ALLOWED_INTERVALS[i]
            path, val = f"/euclid/interval_val_{ch + 1}", self.interval_value[ch]
        if path is not None:
            self.send(path, val)
        self._changed()

    def toggle_mute(self):
        ch = self.select_ch
        self.mute[ch] = not self.mute[ch]
        self.send(f"/euclid/mute_{ch + 1}", int(self.mute[ch]))
        self._changed()

    def select_channel(self, ch):
        if 0 <= ch < self.channels and ch != self.select_ch:
            self.select_ch = ch
            self.send("/euclid/ch", ch)
            self._changed()

    def nudge_note(self, ch, direction):
        self.note_numbers[ch] = max(1, min(self.note_numbers[ch] + direction, self.max_note))
        self.send(f"/euclid/note_num_{ch + 1}", self.note_numbers[ch])
        self._changed()

    # Patterns

    def update_offset_buffers(self):
        for k in range(self.channels):
            base = self.euclidean_patterns[max(0, min(self.hits[k], self.max_steps))]
            self.offset_buf[k] = [bool(base[(i - self.offset[k]) % self.max_steps]) for i in range(self.max_steps)]

    def get_polygon_vertex_steps(self, k):
        hits, limit, offset = self.hits[k], self.limit[k], self.offset[k]
        if hits <= 0 or limit <= 0:
            return set()
        rotation = (2 * math.pi / self.max_steps) * offset
        angle_per_v = 2 * math.pi / hits
        return {int(round((((angle_per_v * n - math.pi / 2 - rotation) + math.pi / 2) % (2 * math.pi))
                          / (2 * math.pi) * limit)) % limit for n in range(hits)}

    def get_interval_hit_steps(self, k):
        hits, limit, offset, interval = self.hits[k], self.limit[k], self.offset[k], self.interval_value[k]
        if hits <= 0 or limit <= 0:
            return set()
        rotation = (2 * math.pi / self.max_steps) * offset
        angle_per_s = 2 * math.pi / limit
        return {int(round(((((angle_per_s * ((i * interval) % limit)) - math.pi / 2 - rotation) + math.pi / 2)
                           % (2 * math.pi)) / (2 * math.pi) * limit)) % limit for i in range(hits)}

    def is_hit(self, k, step):
        if self.display_mode == "polygon":
            return step in self.get_polygon_vertex_steps(k)
        if self.display_mode == "euclidean":
            return self.offset_buf[k][step % self.max_steps]
        return step in self.get_interval_hit_steps(k)

    # Geometry: unit coordinates (centre 0,0, radius 1, y down)

    @staticmethod
    def _euclidean_xy(step):
        return (_X16[step] - 25) / 15, (_Y16[step] - 25) / 15

    @staticmethod
    def _circle_xy(angle):
        return math.cos(angle), math.sin(angle)

    def step_dots(self, k):
        """Positions of channel k's steps"""
        if self.display_mode == "euclidean":
            return [self._euclidean_xy(j) for j in range(self.max_steps)]
        limit = self.limit[k]
        return [self._circle_xy((2 * math.pi / limit) * j - math.pi / 2) for j in range(limit)] if limit > 0 else []

    def hit_points(self, k):
        """Positions of channel k's hits, in drawing order (a polygon when more than one)"""
        if self.hits[k] <= 0:
            return []
        if self.display_mode == "euclidean":
            return [self._euclidean_xy(m) for m in range(self.max_steps) if self.offset_buf[k][m]]
        rotation = (2 * math.pi / self.max_steps) * self.offset[k]
        if self.display_mode == "polygon":
            angle_v = 2 * math.pi / self.hits[k]
            return [self._circle_xy(angle_v * n - math.pi / 2 - rotation) for n in range(self.hits[k])]
        if self.limit[k] > 0:
            angle_s = 2 * math.pi / self.limit[k]
            return [self._circle_xy(angle_s * ((i * self.interval_value[k]) % self.limit[k]) - math.pi / 2 - rotation)
                    for i in range(self.hits[k])]
        return []

    def play_position(self, k):
        """(x, y, hit) of channel k's current step, None when muted or empty"""
        if self.mute[k] or self.limit[k] <= 0:
            return None
        step = self.playing_step[k]
        if self.display_mode == "euclidean":
            x, y = self._euclidean_xy(step % self.max_steps)
            return x, y, self.offset_buf[k][step % self.max_steps]
        x, y = self._circle_xy((2 * math.pi / self.limit[k]) * step - math.pi / 2)
        return x, y, self.is_hit(k, step)
