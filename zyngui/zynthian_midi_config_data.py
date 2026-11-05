# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# MIDI configuration lists (devices, services, chain routing): UI-independent part of
# zynthian_gui_midi_config, used by the Tk and Qt UIs.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

import os
import re
import logging

import zynconf
import zynautoconnect
from zynconf import zynthian_paths
from zyncoder.zyncore import lib_zyncore
from zyngui import zynthian_gui_config

ZMIP_ICON_MODE_ACTIVE = "⇥"  # \u21e5
ZMIP_ICON_MODE_MULTI = "⇶"  # \u21f6
ZMIP_ICON_SEQ_EXCL = "♣"
ZMIP_ICON_MIDI_CLOCK = "⏱"  # \u23F1
#ZMIP_ICON_MIDI_SYS = "♣" # \u1
#ZMIP_ICON_MIDI_SYS_RT = "⌛"  # \u231B
ZMIP_ICON_CTRLDEV_DRIVER = "⌨"  # \u2328


def midi_config_list(sm, chain, midi_input):
    """List rows of the MIDI configuration: admin view (chain None: devices and services) or a
    chain's input or output routing.

    sm : state manager
    chain : chain or None
    midi_input : True for MIDI inputs, False for outputs
    Returns : list of rows [value, index, title, (info, icon)] (zynthian_gui_selector list_data).
        Elements in jack port rows:
        0: Port UID (or service name if service disabled)
        0: For services this is the name of function to start/stop service
        1: ZMIP/ZMOP index on None if not connected
        2: Display text
    """

    list_data = []

    def get_mode_str(idev):
        """Get input mode prefix"""
        mode_str = ""
        if idev is None:
            return mode_str
        if midi_input:
            port = zynautoconnect.devices_in[idev]
            if zynautoconnect.get_midi_in_dev_mode(idev):
                mode_str += ZMIP_ICON_MODE_ACTIVE
            else:
                mode_str += ZMIP_ICON_MODE_MULTI
            if port.aliases[0] not in zynautoconnect.get_zynseq_exclude_ports():
                mode_str += " " + ZMIP_ICON_SEQ_EXCL
            if zynautoconnect.get_ext_clock_zmip() == idev:
                mode_str += " " + ZMIP_ICON_MIDI_CLOCK
            #if lib_zyncore.zmip_get_flag_system(idev):
            #    mode_str += " " + ZMIP_ICON_MIDI_SYS
            #if lib_zyncore.zmip_get_flag_system_rt(idev):
            #    mode_str += " " + ZMIP_ICON_MIDI_SYS_RT
            if idev in sm.ctrldev_manager.drivers:
                mode_str += " " + ZMIP_ICON_CTRLDEV_DRIVER
        if mode_str:
            mode_str += " "
        return mode_str

    def get_info(text="", has_options=True):
        if has_options:
            if chain:
                actions_info = "Bold select for options.\n"
            else:
                actions_info = "Select for options.\n"
        else:
            actions_info = ""
        mode_info = ""
        if midi_input:
            if not chain:
                actions_info += "Push #3 for MIDI OUT.\n"
            if has_options:
                mode_info += f"ICONS KEY:\n"
                mode_info += f"{ZMIP_ICON_MODE_ACTIVE} Active mode\n"
                mode_info += f"{ZMIP_ICON_MODE_MULTI} Multitimbral mode\n"
                mode_info += f"{ZMIP_ICON_SEQ_EXCL} Sequencer capture\n"
                mode_info += f"{ZMIP_ICON_MIDI_CLOCK} MIDI Clock\n"
                #mode_info += f"{ZMIP_ICON_MIDI_SYS} System non-RT\n"
                #mode_info += f"{ZMIP_ICON_MIDI_SYS_RT} System RT\n"
                mode_info += f"{ZMIP_ICON_CTRLDEV_DRIVER} Driver loaded\n"
        else:
            if not chain:
                actions_info += "Push #3 for MIDI IN.\n"
        info = ""
        if text:
            info += text + "\n"
        if mode_info:
            if info:
                info += "\n"
            info += mode_info
        return info + "\n" + actions_info

    def append_port(idev):
        """Add a port to list"""
        if midi_input:
            port = zynautoconnect.devices_in[idev]
            mode = get_mode_str(idev)

            if chain is None:
                list_data.append((port.aliases[0], idev, f"{mode}{port.aliases[1]}", [get_info(), "midi_input.png"]))
            elif not sm.ctrldev_manager.is_input_device_available_to_chains(idev):
                list_data.append((port.aliases[0], idev, f"    {mode}{port.aliases[1]}", [get_info("Captured by driver."), "midi_input.png"]))
            else:
                if lib_zyncore.zmop_get_route_from(chain.zmop_index, idev):
                    list_data.append((port.aliases[0], idev, f"\u2612 {mode}{port.aliases[1]}", [get_info("Connected to chain."), "midi_input.png"]))
                else:
                    list_data.append((port.aliases[0], idev, f"\u2610 {mode}{port.aliases[1]}", [get_info("Disconnected from chain."), "midi_input.png"]))
        else:
            port = zynautoconnect.devices_out[idev]
            if port.aliases[0] in zynautoconnect.get_midi_clock_output_ports():
                name = f"{ZMIP_ICON_MIDI_CLOCK} {port.aliases[1]}"
            else:
                name = port.aliases[1]
            if chain is None:
                list_data.append((port.aliases[0], idev, name, [get_info(), "midi_output.png"]))
            elif port.aliases[0] in chain.midi_out:
                list_data.append((port.aliases[0], idev, f"\u2612 {name}", [get_info("Connected to chain."), "midi_output.png"]))
            else:
                list_data.append((port.aliases[0], idev, f"\u2610 {name}", [get_info("Disconnected to chain."), "midi_output.png"]))

    def append_service(service, name, help_info="", icon="midi_logo.png"):
        try:
            idev = net_devices[name]
        except:
            idev = None
        if zynconf.is_service_active(service):
            mode = get_mode_str(idev)
            list_data.append((f"stop_{service}", idev, f"\u2612 {mode}{name}", [get_info(f"Disable {help_info}", False), icon]))
        else:
            list_data.append((f"start_{service}", idev, f"\u2610 {name}", [get_info(f"Enable {help_info}", False), icon]))

    def atoi(text):
        return int(text) if text.isdigit() else text

    def natural_keys(t):
        return [atoi(c) for c in re.split(r'(\d+)', t[0].lower())]

    # Lists of zmop/zmip indicies
    int_devices = []    # Internal MIDI ports
    usb_devices = []    # USB MIDI ports
    ble_devices = []    # BLE MIDI ports
    aubio_devices = []  # Aubio MIDI ports
    net_devices = {}    # Network MIDI ports, indexed by jack port name
    if midi_input:
        devs = zynautoconnect.devices_in
    else:
        devs = zynautoconnect.devices_out
    for i, dev in enumerate(devs):
        if dev and len(dev.aliases) > 1:
            if dev.aliases[0].startswith("USB:"):
                usb_devices.append((dev.aliases[1], i))
            elif dev.aliases[0].startswith("BLE:"):
                ble_devices.append((dev.aliases[1], i))
            elif dev.aliases[0].startswith("AUBIO:"):
                aubio_devices.append(i)
            elif dev.aliases[0].startswith("NET:"):
                # net_devices[dev.name] = i
                port = devs[i]
                puid, name = zynautoconnect.build_midi_port_name(port)
                net_devices[name] = i
            else:
                int_devices.append(i)

    if chain and midi_input:
        midi_chan = chain.midi_chan + 1
        if midi_chan > 16:
            midi_chan = "ALL"
        list_data.append(("MIDI Channel", None, f"MIDI Channel ({midi_chan})", [get_info("Select the MIDI channel this chain receives.", False), "midi_settings.png"]))
        list_data.append(("Note Range & Transpose", None, "Note Range & Transpose", [get_info("Configure note range and transpose.", False), "note_range.png"]))
        list_data.append(("MIDI CC", None, "MIDI CC",
                               [get_info("Select MIDI CC numbers passed-thru to chain processors. It could interfere with MIDI-learning. Use with caution!", False),
                                "midi_settings.png"]))

    list_data.append((None, None, "INTERNAL DEVICES"))
    nint = len(list_data)

    for i in int_devices:
        append_port(i)

    if midi_input:
        if not chain or zynthian_gui_config.midi_aubionotes_enabled:
            if chain:
                for i in aubio_devices:
                    append_port(i)
            else:
                append_service("aubionotes", "Aubionotes (Audio \u2794 MIDI)",
                               "Aubionotes. Converts audio input to MIDI note on/off commands.", "midi_audio.png")

    # Remove "Internal Devices" title if section is empty
    if len(list_data) == nint:
        list_data.pop()

    if usb_devices:
        list_data.append((None, None, "USB DEVICES"))
        for x in sorted(usb_devices, key=natural_keys):
            append_port(x[1])

    if chain is None or ble_devices:
        list_data.append((None, None, "BLUETOOTH DEVICES"))
        if chain is None:
            append_service("bluetooth", "BLE MIDI", "Bluetooth MIDI.", "midi_bluetooth.png")
        for x in sorted(ble_devices, key=natural_keys):
            append_port(x[1])

    if not chain or net_devices:
        list_data.append((None, None, "NETWORK DEVICES"))
        if chain:
            for i in net_devices.values():
                append_port(i)
        else:
            if os.path.isfile("/usr/local/bin/jacknetumpd"):
                append_service("jacknetumpd", "Network MIDI 2.0",
                               "Network MIDI 2.0. Provides MIDI over an IP connection using Network MIDI 2.0 protocol.", "midi_network.png")

            if os.path.isfile("/usr/local/bin/jackrtpmidid"):
                append_service("jackrtpmidid", "RTP MIDI",
                               "RTP-MIDI. Provides MIDI over an IP connection using RTP-MIDI protocol (AppleMIDI).", "midi_network.png")

            if os.path.isfile("/usr/local/bin/qmidinet"):
                append_service("qmidinet", "QmidiNet",
                               "QmidiNet. Provides MIDI over an IP connection using UDP/IP multicast (ipMIDI).", "midi_network.png")

            if os.path.isfile(f"{zynthian_paths.venv_dir}/bin/touchosc2midi"):
                append_service("touchosc2midi", "TouchOSC",
                               "Interface with Hexler TouchOSC modular control surface.", "midi_network.png")

    a2m_ports = zynautoconnect.get_a2m_ports()
    if midi_input and chain and a2m_ports:
        list_data.append((None, None, "> AUDIO => MIDI"))
        for name, title in a2m_ports:
            if name in chain.midi_in:
                list_data.append(("audio2midi", name, f"\u2612 {title}", [get_info("Connected from chain.", False), "midi_audio.png"]))
            else:
                list_data.append(("audio2midi", name, f"\u2610 {title}", [get_info("Disconnected from chain.", False), "midi_audio.png"]))

    if not midi_input and chain:
        list_data.append((None, None, "> CHAINS"))
        len_check = len(list_data)
        for i, chain_id in enumerate(sm.chain_manager.chains):
            chain = sm.chain_manager.get_chain(chain_id)
            if chain and chain.is_midi() and chain != chain and chain.midi_chan < 16:
                if sm.chain_manager.will_midi_howl(sm.chain_manager.active_chain.chain_id, chain_id):
                    prefix = "∞ "
                else:
                    prefix = ""
                if chain_id in chain.midi_out:
                    list_data.append((chain_id, None, f"\u2612 {prefix}{chain.get_name()}", [get_info("Connected to chain.", False), "midi_output.png"]))
                else:
                    list_data.append((chain_id, None, f"\u2610 {prefix}{chain.get_name()}", [get_info("Disconnected from chain.", False), "midi_output.png"]))
        if len(list_data) == len_check:
            list_data.pop() # Remove section title for empty section

    return list_data


def midi_config_action(sm, chain, midi_input, row):
    """Short select on a row: start/stop a service or toggle a chain route.
    Returns None if done, or the name of what the screen must show instead: "midi_chan",
    "midi_cc", "midi_key_range", "options"."""
    action = row[0]
    wait = 2  # Delay after starting service to allow jack ports to update
    services = {"jacknetumpd": (sm.start_netump, sm.stop_netump),
                "jackrtpmidid": (sm.start_rtpmidi, sm.stop_rtpmidi),
                "qmidinet": (sm.start_qmidinet, sm.stop_qmidinet),
                "touchosc2midi": (sm.start_touchosc2midi, sm.stop_touchosc2midi),
                "aubionotes": (sm.start_aubionotes, sm.stop_aubionotes),
                "bluetooth": (sm.start_bluetooth, sm.stop_bluetooth)}
    if isinstance(action, str) and (action.startswith("start_") or action.startswith("stop_")):
        verb, service = action.split("_", 1)
        if service in services:
            services[service][0 if verb == "start" else 1](wait=wait)
            return None
    if not chain:
        return "options"
    if action == "MIDI Channel":
        return "midi_chan"
    if action == "MIDI CC":
        return "midi_cc"
    if action == "Note Range & Transpose":
        return "midi_key_range"
    if action == "audio2midi":
        chain.toggle_midi_in(row[1])
        return None
    # Route/unroute
    idev = row[1]
    if midi_input:
        if not sm.ctrldev_manager.is_input_device_available_to_chains(idev):
            return None
        lib_zyncore.zmop_set_route_from(chain.zmop_index, idev, not lib_zyncore.zmop_get_route_from(chain.zmop_index, idev))
    else:
        try:
            if idev is not None:
                dev_id = zynautoconnect.get_midi_out_dev(idev).aliases[0]
                chain.toggle_midi_out(dev_id)
            elif isinstance(action, int):
                chain.toggle_midi_out(action)
        except Exception as e:
            logging.error(e)
    return None
