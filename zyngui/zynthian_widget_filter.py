#!/usr/bin/python3
# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Zynthian Widget Class for filter screen type
#
# Copyright (C) 2025 Ronald Summers <ronfsum@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
# ******************************************************************************


import math
import tkinter
import logging
#from PIL import Image, ImageDraw, ImageTk

from zyngui import zynthian_gui_config
from zyngui import zynthian_widget_base
from zyngui.zynthian_widget_data import (filter_zctrls, filter_values, filter_curve, filter_drag, FILTER_DB_MIN,
                                         FILTER_DB_MAX, FILTER_DB_TICKS)


class zynthian_widget_filter(zynthian_widget_base.zynthian_widget_base):

    def __init__(self, parent):
        super().__init__(parent)
        self.fg_color = zynthian_gui_config.color_tx
        self.font_small = ("sans", 10)

        # Take only half height
        self.rows //= 2

        self.widget_canvas = tkinter.Canvas(self, highlightthickness=0, relief='flat', bg=zynthian_gui_config.color_bg)
        self.widget_canvas.grid(sticky='news')

        # Theme Colors
        self.fill_color = zynthian_gui_config.color_variant(zynthian_gui_config.color_on, -90)
        self.outline_color = zynthian_gui_config.color_on
        self.grid_color = zynthian_gui_config.color_variant(zynthian_gui_config.color_hl, -60)

        # Persistent Polygon for performance
        self.filter_poly = self.widget_canvas.create_polygon(0, 0, fill=self.fill_color, outline=self.outline_color, width=2)
        #self.bg_image = None

        # XY-Pad Bindings
        self.widget_canvas.bind('<ButtonPress-1>', self.on_canvas_press)
        self.widget_canvas.bind('<B1-Motion>', self.on_canvas_drag)
        self.widget_canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        self.cutoff_param = None
        self.resonance_param = None
        self.last_filter_values = []

        self.click_cutoff_val = 0.5
        self.click_res_val = 0.0
        self.is_dragging = False

        # Vertical Scale Configuration (-48 to +24 dB)
        #self.db_min = -48
        #self.db_max = 24
        #self.db_range = self.db_max - self.db_min
        #self.db_ticks = [24, 12, 0, -24, -48]

        # Vertical Scale Configuration (-24 to +18 dB)
        self.db_min = FILTER_DB_MIN
        self.db_max = FILTER_DB_MAX
        self.db_range = self.db_max - self.db_min
        self.db_ticks = FILTER_DB_TICKS

        # Margins
        #self.m_l, self.m_r, self.m_t, self.m_b = 45, 10, 20, 35
        self.m_l, self.m_r, self.m_t, self.m_b = 10, 10, 10, 10

        self.draw_grid()

    def on_size(self, event):
        if event.width == self.width and event.height == self.height:
            return
        super().on_size(event)
        self.draw_grid()
        #self.bg_image = None
        self.refresh_gui(True)

    def show(self):
        cutoff, resonance = filter_zctrls(self.processor.get_group_zctrls(self.zyngui_control.screen_info[0]))
        if cutoff:
            self.cutoff_param = cutoff
        if resonance:
            self.resonance_param = resonance
        super().show()

    """
    Creates an in-memory RGBA image containing a dashed grid pattern.
    def draw_grid_image(self):
        # 0. Precalculate some geometric values
        maxy = self.height - self.m_b
        maxx = self.width - self.m_r
        gw = maxx - self.m_l
        gh = maxy - self.m_t
        if gw < 10:
            return

        # 1. Create a transparent canvas
        grid_img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(grid_img)

        dash_len = 2
        gap_len = 2
        line_color=(0, 180, 0, 255)

        # 2. dB Grid Lines (horizontal)
        for db in self.db_ticks:
            x = self.m_l
            y = self.m_t + gh * (1.0 - (db - self.db_min) / self.db_range)
            while x < maxx:
                # Calculate the end point of the current dash snippet
                dash_end = min(x + dash_len, maxx)
                draw.line([(x, y), (dash_end, y)], fill=line_color, width=1)
                x += dash_len + gap_len

        # 3. Evenly spaced vertical gridlines (linear spacing)
        num_vlines = 8
        for i in range(num_vlines + 1):
            x = self.m_l + (gw * i / num_vlines)
            y = self.m_t
            while y < maxy:
                # Calculate the end point of the current dash snippet
                dash_end = min(y + dash_len, maxy)
                draw.line([(x, y), (x, dash_end)], fill=line_color, width=1)
                y += dash_len + gap_len

        # Convert to Tkinter PhotoImage
        self.widget_canvas.bg_image_tk = ImageTk.PhotoImage(grid_img)

        # Clear the performance-heavy vector items from the canvas
        self.widget_canvas.delete("all")

        # Plot filter polygon
        self.filter_poly = self.widget_canvas.create_polygon(0, 0, fill=self.fill_color, outline=self.outline_color, width=2)

        # Plot grid as an image with transparency ;-)
        self.bg_image = self.widget_canvas.create_image(0, 0, anchor=tkinter.NW, image=self.widget_canvas.bg_image_tk, tags="bg")
    """

    def draw_grid(self):
        # 0. Precalculate some geometric values
        maxy = self.height - self.m_b
        gw = self.width - self.m_l - self.m_r
        gh = maxy - self.m_t
        if gw < 10:
            return

        # Remove old grid elements
        self.widget_canvas.delete("grid")

        dash = None
        #dash = (2, 2)
        # dB Grid Lines
        for db in self.db_ticks:
            y = self.m_t + gh * (1.0 - (db - self.db_min) / self.db_range)
            self.widget_canvas.create_line(self.m_l, y, self.width - self.m_r, y, fill=self.grid_color, dash=dash, tags="grid")
            #self.widget_canvas.create_text(5, y, text=f"{db} dB", fill=zynthian_gui_config.color_tx, anchor="w", font=("sans", 8), tags="grid")

        # Evenly spaced vertical gridlines (linear spacing)
        num_vlines = 8
        for i in range(num_vlines + 1):
            x = self.m_l + (gw * i / num_vlines)
            self.widget_canvas.create_line(x, self.m_t, x, self.height - self.m_b, fill=self.grid_color, dash=dash, tags="grid")

        # Single axis labels
        """
        self.widget_canvas.create_text(
            10, 80,
            text="dB",
            anchor="nw",
            fill=self.fg_color,
            font=self.font_small,
            tags="grid"
        )
        self.widget_canvas.create_text(
            self.width - 270, self.height - 10,
            text="Hz",
            anchor="se",
            fill=self.fg_color,
            font=self.font_small,
            tags="grid"
        ))
        """

    def refresh_gui(self, force=False):
        filter_vals = list(filter_values(self.cutoff_param, self.resonance_param))
        if not (force and self.is_dragging) and filter_vals == self.last_filter_values:
            return
        self.last_filter_values = filter_vals
        coords = filter_curve(filter_vals[0], filter_vals[1], self.width, self.height, self.m_l, self.m_r, self.m_t,
                              self.m_b)
        if coords:
            self.widget_canvas.coords(self.filter_poly, coords)

    def on_canvas_press(self, event):
        self.last_click = event
        self.is_dragging = True
        if self.cutoff_param:
            self.click_cutoff_val = (self.cutoff_param.value - self.cutoff_param.value_min) / self.cutoff_param.value_range
        if self.resonance_param:
            self.click_res_val = (self.resonance_param.value - self.resonance_param.value_min) / self.resonance_param.value_range

    def on_canvas_drag(self, event):
        """Pure XY-Pad: X=Cutoff, Y=Resonance regardless of start position"""
        if not self.is_dragging: return

        dx = (event.x - self.last_click.x) / self.width
        dy = (event.y - self.last_click.y) / self.height

        filter_drag(self.cutoff_param, self.resonance_param, self.click_cutoff_val, self.click_res_val, dx, dy)

    def on_canvas_release(self, event):
        self.is_dragging = False
