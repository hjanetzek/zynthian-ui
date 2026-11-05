#!/usr/bin/python3
# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Zynthian GUI Audio-Out Selector Class
#
# Copyright (C) 2015-2024 Fernando Moyano <jofemodo@zynthian.org>
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

import logging
from time import sleep

# Zynthian specific modules
import zynautoconnect
from zyngine.zynthian_signal_manager import zynsigman
from zyngui.zynthian_gui_selector_info import zynthian_gui_selector_info
from zyngui.zynthian_audio_out_data import audio_out_list

# ------------------------------------------------------------------------------
# Zynthian Audio-Out Selection GUI Class
# ------------------------------------------------------------------------------


class zynthian_gui_audio_out(zynthian_gui_selector_info):

    def __init__(self, parent=None, topbar=None):
        super().__init__('Audio Out', parent=parent, topbar=topbar)

    def build_view(self):
        self.check_ports = 0
        self.playback_ports = zynautoconnect.get_hw_audio_dst_ports()
        return super().build_view()

    def refresh_status(self):
        super().refresh_status()
        self.check_ports += 1
        if self.check_ports > 10:
            self.check_ports = 0
            ports = zynautoconnect.get_hw_audio_dst_ports()
            if self.playback_ports != ports:
                self.playback_ports = ports
                self.fill_list()

    def fill_list(self):
        self.list_data = audio_out_list(self.zyngui.chain_manager, self.playback_ports)
        super().fill_list()

    def select_action(self, i, t='S'):
        if t == 'S':
            self.zyngui.chain_manager.active_chain.toggle_audio_out(self.list_data[i][0])
            self.fill_list()
        elif t == "B":
            if not self.list_data[i][1].startswith("^system:"):
                return
            self.zyngui.state_manager.start_busy("alsa_output", "Getting audio level parameters...")
            sleep(0.1)
            ctrl_list = []
            chans = []
            try:
                a = self.list_data[i][1].replace("$", "").replace("^", "")
                b = a.split("|")
                for c in b:
                    if c.startswith("system:"):
                        chans.append(int(c.split("_")[-1]) - 1)
                zctrls = self.zyngui.state_manager.alsa_mixer_processor.engine.get_controllers_dict()
                for symbol, zctrl in zctrls.items():
                    if zctrl.graph_path[4]:
                        chan = zctrl.graph_path[1]
                    else:
                        chan = zctrl.graph_path[2]
                    if chan in chans:
                        ctrl_list.append(symbol)
                    sleep(0.01)
            except:
                pass
            self.zyngui.state_manager.end_busy("alsa_output")
            if ctrl_list:
                self.zyngui.show_screen("alsa_mixer", params=ctrl_list)

    def set_select_path(self):
        title = "Send Audio to ..."
        try:
            self.select_path.set(f"{self.zyngui.chain_manager.active_chain.get_name()}/{title}")
        except:
            self.select_path.set(title)

# ------------------------------------------------------------------------------
