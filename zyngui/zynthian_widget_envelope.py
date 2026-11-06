#!/usr/bin/python3
# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Zynthian Widget Class for envelope screen type
#
# Copyright (C) 2015-2024 Fernando Moyano <fernando@zynthian.org>
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
from zyngui.zynthian_widget_data import (envelope_zctrls, envelope_values, envelope_geometry, envelope_hit,
                                         envelope_drag)

# ------------------------------------------------------------------------------
# Zynthian Widget Class for envelope screen type
# ------------------------------------------------------------------------------


class zynthian_widget_envelope(zynthian_widget_base.zynthian_widget_base):

    def __init__(self, parent):
        super().__init__(parent)

        # Take only half height
        self.rows //= 2

        self.widget_canvas = tkinter.Canvas(self,
                                            highlightthickness=0,
                                            relief='flat',
                                            bg=zynthian_gui_config.color_bg)
        self.widget_canvas.grid(sticky='news')

        self.last_envelope_values = []
        self.drag_zctrl = None

        # Create custom GUI elements (position and size set when canvas is grid and size applied)
        self.envelope_outline_color = zynthian_gui_config.color_on
        self.envelope_color = zynthian_gui_config.color_variant(zynthian_gui_config.color_on, -90)
        self.envelope_polygon = self.widget_canvas.create_polygon(0, 0, outline=self.envelope_outline_color, fill=self.envelope_color, width=3)
        self.drag_polygon = self.widget_canvas.create_polygon(0, 0, outline=self.envelope_outline_color, fill=self.envelope_outline_color, width=3, state='hidden')
        # self.release_line = self.widget_canvas.create_line(0, 0, 0, 0,
        # fill=self.envelope_outline_color, state="hidden")
        # self.release_label = self.widget_canvas.create_text(0, 0, text="R", anchor="ne",
        # font=(zynthian_gui_config.font_family, int(1.3*zynthian_gui_config.font_size)),
        # fill=zynthian_gui_config.color_tx, state="hidden")
        self.widget_canvas.bind('<ButtonPress-1>', self.on_canvas_press)
        self.widget_canvas.bind('<B1-Motion>', self.on_canvas_drag)
        self.widget_canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.fade_polarity = 1

        # Margins
        self.m_l, self.m_r, self.m_t, self.m_b = 10, 10, 10, 10
        self.plot_width = self.width - self.m_l - self.m_r
        self.plot_height = self.height - self.m_b - self.m_t


    def on_size(self, event):
        if event.width == self.width and event.height == self.height:
            return
        super().on_size(event)
        self.widget_canvas.grid(row=0, column=0, sticky='news')
        self.last_envelope_values = []
        self.plot_width = self.width - self.m_l - self.m_r
        self.plot_height = self.height - self.m_b - self.m_t
        self.dy = int(0.95 * self.plot_height)
        if self.zctrls:
            self.dx = self.plot_width // len(self.zctrls)
        self.refresh_gui()

    def show(self):
        group = self.processor.get_group_zctrls(self.zyngui_control.screen_info[0])
        self.zctrls, self.fade_polarity = envelope_zctrls(group)
        self.dx = self.plot_width // len(self.zctrls)
        super().show()

    def refresh_gui(self):
        values = envelope_values(self.zctrls)
        if values != self.last_envelope_values or self.drag_zctrl:
            self.last_envelope_values = values
            coords, self.envelope_click_ranges, drag_poly = envelope_geometry(
                self.zctrls, values, self.fade_polarity, self.plot_width, self.plot_height, self.m_l, self.m_b,
                self.drag_zctrl)
            self.widget_canvas.coords(self.envelope_polygon, coords)
            # Highlight dragged section
            if self.drag_zctrl and drag_poly:
                self.widget_canvas.coords(self.drag_polygon, drag_poly)
                self.widget_canvas.itemconfig(self.drag_polygon, state="normal")

    def on_canvas_press(self, event):
        self.last_click = event
        # Identify the envelope phase clicked
        self.drag_zctrl = envelope_hit(self.zctrls, self.envelope_click_ranges, event.x)
        self.envelope_click_value = self.drag_zctrl.value

    def on_canvas_drag(self, event):
        if self.drag_zctrl == None:
            return
        envelope_drag(self.drag_zctrl, self.envelope_click_value, event.x - self.last_click.x,
                      event.y - self.last_click.y, len(self.zctrls), self.plot_width, self.plot_height,
                      self.fade_polarity)

    def on_canvas_release(self, event):
        self.drag_zctrl = None
        self.widget_canvas.itemconfig(self.drag_polygon, state="hidden")

    def get_monitors(self):
        pass

# ------------------------------------------------------------------------------
