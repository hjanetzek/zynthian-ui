#!/usr/bin/python3
# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Zynthian Widget Class GxGraphicEQ (11 bands)
# It could be easily extended to support GxBarkGraphicEQ (24 bands).
#
# Copyright (C) 2015-2026 Fernando Moyano <jofemodo@zynthian.org>
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

import tkinter
import logging

# Zynthian specific modules
from zyngui import zynthian_gui_config
from zyngui import zynthian_widget_base
from zyngui.zynthian_widget_data import gx_eq_bands, gx_eq_levels, gx_eq_drag

# ------------------------------------------------------------------------------
# Zynthian Widget Class for "GxGraphicEQ" (11 band Graphic EQ)
# ------------------------------------------------------------------------------


class zynthian_widget_GxGraphicEQ(zynthian_widget_base.zynthian_widget_base):

    def __init__(self, parent):
        super().__init__(parent)

        # Plot related arrays
        self.n_bands = 0
        self.band_freqs = []
        self.band_labels = []
        self.mon_bars = []
        self.mon_ticks = []
        self.mon_labels = []

        # Geometry vars - set accurately by sizer
        self.bar_width = 1
        self.tick_height = 1
        self.padx = 1
        self.font_labels = ("monoid", 8)

        self.widget_canvas = tkinter.Canvas(self,
                                            bd=0,
                                            highlightthickness=0,
                                            relief='flat',
                                            bg=zynthian_gui_config.color_bg)
        self.widget_canvas.grid(sticky='news')
        self.widget_canvas.bind('<ButtonPress-1>', self.on_canvas_press)
        self.widget_canvas.bind('<B1-Motion>', self.on_canvas_drag)
        self.widget_canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

    def create_gui(self):
        # Clean canvas
        self.widget_canvas.delete()
        # Create custom GUI elements: bars & ticks
        for i in range(self.n_bands):
            self.mon_bars.append(self.widget_canvas.create_rectangle(
                0, 0, 0, 0, fill=zynthian_gui_config.color_hl))
            self.mon_ticks.append(self.widget_canvas.create_rectangle(
                0, 0, 0, 0, fill=zynthian_gui_config.color_on))
            self.mon_labels.append(self.widget_canvas.create_text(
                0, 0,
                fill=zynthian_gui_config.color_tx,
                text=self.band_labels[i],
                angle=90,
                anchor="w",
                font=self.font_labels))
        # Plot dotted line at Gain 0
        y = self.height - int(30 * self.height / 52)
        self.hline_zero = self.widget_canvas.create_line(0, y, self.width, y,
                                                         fill=zynthian_gui_config.color_tx_off,
                                                         dash=[4, 4])

    def on_size(self, event):
        if event.width == self.width and event.height == self.height:
            return
        super().on_size(event)
        self.widget_canvas.configure(width=self.width, height=self.height)
        self.update_geometry()

    def set_processor(self, processor):
        super().set_processor(processor)
        bands = gx_eq_bands(processor)
        if not bands:
            return
        self.band_freqs, self.band_labels = bands
        self.n_bands = len(self.band_freqs)
        self.create_gui()
        self.update_geometry()

    def update_geometry(self):
        if self.n_bands == 0:
            return
        # Geometry vars
        if self.wide:
            w = self.width
        else:
            w = self.width + 2
        self.bar_width = int(w / self.n_bands)
        self.tick_height = int(self.height / 80)
        self.padx = int((w % self.n_bands) / 2)
        self.font_labels_size = int(0.3 * self.bar_width)
        self.font_labels = ("monoid", self.font_labels_size)
        fpad = self.font_labels_size // 4
        x = self.padx + self.bar_width // 2
        # Update labels
        for i in range(self.n_bands):
            self.widget_canvas.itemconfig(self.mon_labels[i], font=self.font_labels)
            self.widget_canvas.coords(self.mon_labels[i], x, self.height - fpad)
            x += self.bar_width
        # Updated dotted line at Gain 0
        y = self.height - int(30 * self.height / 52)
        self.widget_canvas.coords(self.hline_zero, 0, y, self.width, y)

    def refresh_gui(self):
        x0 = self.padx
        x1 = x0 + self.bar_width
        for i, (bar0, bar1, tick) in enumerate(gx_eq_levels(self.processor, self.monitors, self.n_bands)):
            bar_y0 = self.height - int(bar0 * self.height)
            bar_y1 = self.height - int(bar1 * self.height)
            tick_y0 = self.height - int(tick * self.height)
            tick_y1 = tick_y0 - self.tick_height
            self.widget_canvas.coords(self.mon_bars[i], x0 + 2, bar_y0, x1 - 2, bar_y1)
            self.widget_canvas.coords(self.mon_ticks[i], x0, tick_y0, x1, tick_y1)
            x0 = x1
            x1 += self.bar_width

    def on_canvas_press(self, event):
        self.on_canvas_drag(event)

    def on_canvas_drag(self, event):
        n = (event.x + self.bar_width // 2) // self.bar_width
        gx_eq_drag(self.processor, n - 1, (self.height - event.y) / self.height)

    def on_canvas_release(self, event):
        pass

# ------------------------------------------------------------------------------
