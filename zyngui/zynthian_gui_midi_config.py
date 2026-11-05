#!/usr/bin/python3
# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Zynthian GUI MIDI config Class
#
# Copyright (C) 2015-2026 Fernando Moyano <jofemodo@zynthian.org>
#                         Brian Walton <brian@riban.co.uk>
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

from zynconf import zynthian_paths
import os
import re
import logging
from time import sleep
from threading import Thread
from subprocess import check_output, Popen, PIPE

# Zynthian specific modules
import zynconf
import zynautoconnect
from zyncoder.zyncore import lib_zyncore
from zyngine.ctrldev.zynthian_ctrldev_base import SCROLL_MODE_DISABLED, SCROLL_MODE_FIXED, SCROLL_MODE_GUI_SEL, SCROLL_MODE_GUI_VIEW, SCROLL_MODE_CTRLDEV
from zyngui import zynthian_gui_config
from zyngui.zynthian_gui_selector_info import zynthian_gui_selector_info
from zyngui.zynthian_midi_config_data import (midi_config_list, midi_config_action,
    ZMIP_ICON_MODE_ACTIVE, ZMIP_ICON_MODE_MULTI, ZMIP_ICON_SEQ_EXCL, ZMIP_ICON_MIDI_CLOCK,
    ZMIP_ICON_CTRLDEV_DRIVER)


# ------------------------------------------------------------------------------
# Mini class to allow use of audio_in gui
# ------------------------------------------------------------------------------


class aubio_inputs():
    def __init__(self, state_manager):
        self.state_manager = state_manager
        self.audio_in = state_manager.aubio_in

    def toggle_audio_in(self, input):
        if input in self.audio_in:
            self.audio_in.remove(input)
        else:
            self.audio_in.append(input)
        self.state_manager.aubio_in = self.audio_in
        zynautoconnect.request_audio_connect()

# ------------------------------------------------------------------------------
# Zynthian MIDI config GUI Class
# ------------------------------------------------------------------------------

class zynthian_gui_midi_config(zynthian_gui_selector_info):

    def __init__(self, parent=None, topbar=None):
        self.chain = None      # Chain object
        self.midi_input = True      # True to process MIDI inputs, False for MIDI outputs
        self.thread = None
        super().__init__('MIDI Config', parent=parent, topbar=topbar)

    def build_view(self):
        # Enable background scan for MIDI devices
        self.midi_scan = True
        self.thread = Thread(target=self.process_dynamic_ports, name="MIDI port scan")
        self.thread.start()
        return super().build_view()

    def hide(self):
        if self.shown:
            self.midi_scan = False
            self.thread = None
            super().hide()

    def set_chain(self, chain):
        self.chain = chain
        self.set_select_path()

    def fill_list(self):
        """Populate data list used for display and configuration.
        Different display mode for admin view (no chain) and chain view (i/o routing)
        List of lists, each consisting of elements based on the display mode and entry type.

        Elements in jack port:
        0: Port UID (or service name if service disabled)
        0: For services this is the name of function to start/stop service
        1: ZMIP/ZMOP index on None if not connected
        2: Display text
        """

        self.list_data = midi_config_list(self.zyngui.state_manager, self.chain, self.midi_input)
        super().fill_list()

    def select_action(self, i, t='S'):
        if t == 'S':
            what = midi_config_action(self.zyngui.state_manager, self.chain, self.midi_input, self.list_data[i])
            if what == "midi_chan":
                self.zyngui.screens['midi_chan'].set_mode("SET", self.chain.midi_chan, chan_all=True)
                self.zyngui.show_screen('midi_chan')
                return
            elif what == "midi_cc":
                self.zyngui.screens['midi_cc'].set_chain(self.chain)
                self.zyngui.show_screen('midi_cc')
                return
            elif what == "midi_key_range":
                self.zyngui.screens['midi_key_range'].config(self.chain)
                self.zyngui.show_screen('midi_key_range')
                return
            elif what == "options":
                self.show_options()
                return
        elif t == 'B':
            self.show_options()
            return
        self.update_list()

    def set_mode(self, input):
        self.midi_input = input
        if self.shown:
            self.set_select_path()
            self.update_list()

    def set_mode_input(self):
        self.set_mode(True)

    def set_mode_output(self):
        self.set_mode(False)

    def toggle_mode(self):
        self.set_mode(not self.midi_input)

    def switch(self, i, t):
        if not self.chain:
            if i == 2 and t == 'S':
                self.toggle_mode()
                return True
        return False

    def cuia_v5_zynpot_switch(self, params):
        if not self.chain:
            i = params[0]
            t = params[1].upper()
            if i == 2 and t == 'S':
                self.toggle_mode()
                return True
        return False

    def show_menu(self):
        if self.shown:
            return self.show_options()
        else:
            return False

    def show_options(self):
        try:
            idev = self.list_data[self.index][1]
            if idev is None:
                return False
            options = {}
            if self.midi_input:
                port = zynautoconnect.devices_in[idev]
                screen_title = f"MIDI-IN: {port.aliases[1]}"

                options["Options"] = None
                opt_info = "Toggle input mode.\n\n"
                if zynautoconnect.get_midi_in_dev_mode(idev):
                    if lib_zyncore.get_active_midi_chan():
                        opt_info += f"{ZMIP_ICON_MODE_ACTIVE}: Active chain.\n\nTranslate MIDI channel. Send to chains matching active chain's MIDI channel."
                    else:
                        opt_info += f"{ZMIP_ICON_MODE_ACTIVE}: Active chain.\n\nTranslate MIDI channel. Send to active chain only."
                    options["Input mode (Active chain)"] = ["MODE_MULTI", [opt_info, "midi_input.png"]]
                else:
                    opt_info += f"{ZMIP_ICON_MODE_MULTI}: Multitimbral.\n\nDon't translate MIDI channel. Send to chains matching device's MIDI channel."
                    options["Input mode (Multitimbral)"] = ["MODE_ACTI", [opt_info, "midi_input.png"]]

                opt_info = f"Toggle sequencer capture.\n\n{ZMIP_ICON_SEQ_EXCL}: Sequencer.\n\nUse this input device for live recording from the step sequencer."
                if port.aliases[0] in zynautoconnect.get_zynseq_exclude_ports():
                    options[f"\u2610 Sequencer capture"] = [idev, [opt_info, "midi_input.png"]]
                else:
                    options[f"\u2612 Sequencer capture"] = [idev, [opt_info, "midi_input.png"]]

                opt_info = f"Toggle MIDI clock.\n\n{ZMIP_ICON_MIDI_CLOCK}: MIDI Clock.\n\nSync to MIDI clock from this device.\nThis is an exclusive option that will disable syncing from other devices."
                if zynautoconnect.get_ext_clock_zmip() == idev:
                    options[f"\u2612 MIDI Clock Source"] = ["MIDI_CLOCK/OFF", [opt_info, "midi_input.png"]]
                else:
                    options[f"\u2610 MIDI Clock Source"] = ["MIDI_CLOCK/ON", [opt_info, "midi_input.png"]]

                """
                opt_info = "Route non real-time system messages from this device.\n\n"
                if lib_zyncore.zmip_get_flag_system(idev):
                    title = f"\u2612 {ZMIP_ICON_MIDI_SYS} Non real-time messages"
                    options[title] = ["MIDI_SYS/OFF", [opt_info, "midi_input.png"]]
                else:
                    title = f"\u2610 {ZMIP_ICON_MIDI_SYS} Non real-time messages"
                    options[title] = ["MIDI_SYS/ON", [opt_info, "midi_input.png"]]

                opt_info = "Route real-time system messages from this device.\n\n"
                if lib_zyncore.zmip_get_flag_system_rt(idev):
                    title = f"\u2612 {ZMIP_ICON_MIDI_SYS_RT} Real-time transport messages"
                    options[title] = ["MIDI_SYS_RT/OFF", [opt_info, "midi_input.png"]]
                else:
                    title = f"\u2610 {ZMIP_ICON_MIDI_SYS_RT} Real-time transport messages"
                    options[title] = ["MIDI_SYS_RT/ON", [opt_info, "midi_input.png"]]
                """

                # Reload drivers => Hot reload the driver classes!
                #self.zyngui.state_manager.ctrldev_manager.update_available_drivers(reload_modules=False)
                # Get driver list for the device (dev_id) connected to this slot (idev)
                dev_id = zynautoconnect.get_midi_in_devid(idev)
                available_drivers = self.zyngui.state_manager.ctrldev_manager.available_drivers
                loaded_drivers = self.zyngui.state_manager.ctrldev_manager.drivers
                # Get available drivers for this device ...
                device_drivers = []
                # Specific drivers
                try:
                    device_drivers += available_drivers[dev_id]
                except:
                    pass
                # Generic drivers
                if idev < lib_zyncore.zmip_get_seq_index():
                    try:
                        device_drivers += available_drivers["*"]
                    except:
                        pass
                driver_options = {}
                for i, driver_class in enumerate(device_drivers):
                    driver_name = driver_class.get_driver_name()
                    driver_description = driver_class.get_driver_description()
                    if not driver_description:
                        driver_description = "Device driver integrating UI functions and customized workflow."
                    driver_description = f"{ZMIP_ICON_CTRLDEV_DRIVER}: Driver.\n\n{driver_description}"
                    if idev in loaded_drivers and type(loaded_drivers[idev]) is driver_class:
                        driver_options[f"\u2612 {driver_name}"] = [
                            ["UNLOAD_DRIVER", driver_class.__name__], [driver_description, "midi_input.png"]]
                    else:
                        driver_options[f"\u2610 {driver_name}"] = [
                            ["LOAD_DRIVER", driver_class.__name__], [driver_description, "midi_input.png"]]
                if driver_options:
                    options[f"Drivers {ZMIP_ICON_CTRLDEV_DRIVER}"] = None
                    options.update(driver_options)

            else:
                port = zynautoconnect.devices_out[idev]
                screen_title = f"MIDI-OUT: {port.aliases[1]}"
                options["Options"] = None
                opt_info = "Send MIDI clock to this device."
                if port.aliases[0] in zynautoconnect.get_midi_clock_output_ports():
                    options[f"\u2612 {ZMIP_ICON_MIDI_CLOCK} Send MIDI Clock"] = [idev, [opt_info, "midi_output.png" ]]
                else:
                    options[f"\u2610 {ZMIP_ICON_MIDI_CLOCK} Send MIDI Clock"] = [idev, [opt_info, "midi_output.png" ]]

            options["Advanced"] = None
            if self.list_data[self.index][0].startswith("AUBIO:") or self.list_data[self.index][0].endswith("aubionotes"):
                options["Select aubio inputs"] = ["AUBIO_INPUTS", ["Select audio inputs to be analized and converted to MIDI.", "midi_audio.png"]]
            options[f"Rename port '{port.aliases[0]}'"] = [port, ["Rename the MIDI port.\nClear name to reset to default name.",  "midi_input.png"]]
            # options[f"Reset name to '{zynautoconnect.build_midi_port_name(port)[1]}'"] = port

            self.zyngui.screens['option'].config(screen_title, options, self.menu_cb, False, True, None)
            self.zyngui.show_screen('option')
            return True
        except Exception as e:
            logging.error(e)
            #pass  # Port may have disappeared whilst building menu
        return False

    def menu_cb(self, option, params, click_type):
        try:
            if option.startswith("Rename port"):
                self.zyngui.show_keyboard(self.rename_device, params.aliases[1])
                return
            elif option.startswith("Reset name"):
                zynautoconnect.set_port_friendly_name(params)
            elif option.endswith("Send MIDI Clock"):
                zynautoconnect.toggle_midi_clock_output_zmop(params)
            elif option.endswith("Sequencer capture"):
                zynautoconnect.toggle_zynseq_input_zmop(params)
            elif isinstance(params, list):
                idev = self.list_data[self.index][1]
                if click_type == "B":
                    self.show_controller_options(idev)
                    return
                elif params[0] == "LOAD_DRIVER":
                    #logging.debug(f"LOAD DRIVER FOR {idev}")
                    self.zyngui.state_manager.ctrldev_manager.load_driver(idev, params[1])
                elif params[0] == "UNLOAD_DRIVER":
                    #logging.debug(f"UNLOAD DRIVER FOR {idev}")
                    self.zyngui.state_manager.ctrldev_manager.unload_driver(idev,True)
            elif isinstance(params, str):
                if params == "AUBIO_INPUTS":
                    ain = aubio_inputs(self.zyngui.state_manager)
                    self.zyngui.screens['audio_in'].set_chain(ain)
                    self.zyngui.show_screen('audio_in')
                    return
                elif self.midi_input:
                    idev = self.list_data[self.index][1]
                    match params:
                        case "MODE_ACTI":
                            lib_zyncore.zmip_set_flag_active_chain(idev, True)
                            zynautoconnect.update_midi_in_dev_mode(idev)
                        case "MODE_MULTI":
                            lib_zyncore.zmip_set_flag_active_chain(idev, False)
                            zynautoconnect.update_midi_in_dev_mode(idev)
                        case "MIDI_CLOCK/ON":
                            zynautoconnect.set_ext_clock_zmip(idev)
                        case "MIDI_CLOCK/OFF":
                            zynautoconnect.set_ext_clock_zmip(-1)
                    """
                    case "MIDI_SYS/ON":
                        lib_zyncore.zmip_set_flag_system(idev, True)
                    case "MIDI_SYS/OFF":
                        lib_zyncore.zmip_set_flag_system(idev, False)
                    case "MIDI_SYS_RT/ON":
                        lib_zyncore.zmip_set_flag_system_rt(idev, True)
                    case "MIDI_SYS_RT/OFF":
                        lib_zyncore.zmip_set_flag_system_rt(idev, False)
                    """
            self.show_options()
            self.update_list()
        except Exception as e:
            #logging.error(e)
            pass  # Ports may have changed since menu opened

    def show_controller_options(self, idev):
        """ Show hardware controller options view
        Params:
            idev: Index of controller's MIDI port
        """

        # TODO: Check what modes controller supports
        try:
            options = {}
            # Scroll options
            mode = self.zyngui.state_manager.ctrldev_manager.drivers[idev].get_scroll_mode()
            if mode > 0:
                options["Scroll Modes"] = None
                options["Locked (no scroll)"] = ("scroll_mode", idev, SCROLL_MODE_FIXED)
                options["Follow GUI selection"] = ("scroll_mode", idev, SCROLL_MODE_GUI_SEL)
                options["Follow GUI view"] = ("scroll_mode", idev, SCROLL_MODE_GUI_VIEW)
                options["Driver custom"] = ("scroll_mode", idev, SCROLL_MODE_CTRLDEV)
            if options:
                self.zyngui.screens['option'].config("Controller Options", options, self.controller_options_cb, index=mode+1)
                self.zyngui.show_screen('option')
        except:
            pass

    def controller_options_cb(self, option, params):
        cmd, idev, val = params
        try:
            if cmd == "scroll_mode":
                self.zyngui.state_manager.ctrldev_manager.drivers[idev].set_scroll_mode(cal)
        except:
            logging.warning(f"Failed to set ctrldev option for device {idev}: {cmd}({val}) ")
        self.show_options()

    def process_dynamic_ports(self):
        """Process dynamically added/removed MIDI devices"""

        if self.midi_input:
            last_fingerprint = zynautoconnect.get_hw_src_ports()
        else:
            last_fingerprint = zynautoconnect.get_hw_dst_ports()

        while self.midi_scan:
            if self.midi_input:
                fingerprint = zynautoconnect.get_hw_src_ports()
            else:
                fingerprint = zynautoconnect.get_hw_dst_ports()
            if last_fingerprint != fingerprint:
                last_fingerprint = fingerprint
                self.update_list()

            sleep(2)  # Repeat every 2s

    def rename_device(self, name):
        """Set the friendly name of selected

        name : New friendly name
        """

        if self.midi_input:
            port = zynautoconnect.devices_in[self.list_data[self.index][1]]
        else:
            port = zynautoconnect.devices_out[self.list_data[self.index][1]]
        zynautoconnect.set_port_friendly_name(port, name)
        self.update_list()
        self.zyngui.close_screen("option")

    def set_select_path(self):
        if self.chain:
            if self.midi_input:
                self.select_path.set(f"{self.chain.get_name()}/MIDI Input")
            else:
                self.select_path.set(f"{self.chain.get_name()}/MIDI Output")
        else:
            if self.midi_input:
                self.select_path.set(f"MIDI Input Devices")
            else:
                self.select_path.set(f"MIDI Output Devices")

# ------------------------------------------------------------------------------
