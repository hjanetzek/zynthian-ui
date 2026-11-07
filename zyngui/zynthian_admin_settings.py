# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Admin settings: UI-independent part of zynthian_gui_admin (toggles, value settings and the
# hotplug audio options), used by the Tk and Qt UIs.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

import logging

import zynconf
import zynautoconnect
from zyncoder.zyncore import lib_zyncore
from zyngui import zynthian_gui_config


def last_state_action(state_manager):
    """Save the state for the next start (restore last state enabled), else delete the saved one"""
    if zynthian_gui_config.restore_last_state:
        state_manager.save_last_state_snapshot()
    else:
        state_manager.delete_last_state_snapshot()


def toggle_prog_change_zs3():
    if zynthian_gui_config.midi_prog_change_zs3:
        logging.info("ZS3 Program Change OFF")
        zynthian_gui_config.midi_prog_change_zs3 = False
    else:
        logging.info("ZS3 Program Change ON")
        zynthian_gui_config.midi_prog_change_zs3 = True

    # Save config
    zynconf.update_midi_profile({
        "ZYNTHIAN_MIDI_PROG_CHANGE_ZS3": str(int(zynthian_gui_config.midi_prog_change_zs3))
    })


def toggle_bank_change():
    if zynthian_gui_config.midi_bank_change:
        logging.info("MIDI Bank Change OFF")
        zynthian_gui_config.midi_bank_change = False
    else:
        logging.info("MIDI Bank Change ON")
        zynthian_gui_config.midi_bank_change = True

    # Save config
    zynconf.update_midi_profile({
        "ZYNTHIAN_MIDI_BANK_CHANGE": str(int(zynthian_gui_config.midi_bank_change))
    })


def toggle_active_midi_channel():
    if lib_zyncore.get_active_midi_chan():
        logging.info("Active MIDI channel OFF")
        zynthian_gui_config.active_midi_channel = False
    else:
        logging.info("Active MIDI channel ON")
        zynthian_gui_config.active_midi_channel = True

    lib_zyncore.set_active_midi_chan(
        zynthian_gui_config.active_midi_channel)

    # Save config
    zynconf.update_midi_profile({
        "ZYNTHIAN_MIDI_ACTIVE_CHANNEL": str(int(zynthian_gui_config.active_midi_channel))
    })


def toggle_usbmidi_by_port():
    if zynthian_gui_config.midi_usb_by_port:
        logging.info("MIDI-USB devices by port OFF")
        zynthian_gui_config.midi_usb_by_port = False
    else:
        logging.info("MIDI-USB devices by port ON")
        zynthian_gui_config.midi_usb_by_port = True

    zynautoconnect.update_hw_midi_ports(True)

    # Save config
    zynconf.update_midi_profile({
        "ZYNTHIAN_MIDI_USB_BY_PORT": str(int(zynthian_gui_config.midi_usb_by_port))
    })


def toggle_snapshot_mixer_settings():
    if zynthian_gui_config.snapshot_mixer_settings:
        logging.info("Mixer Settings on Snapshots OFF")
        zynthian_gui_config.snapshot_mixer_settings = False
    else:
        logging.info("Mixer Settings on Snapshots ON")
        zynthian_gui_config.snapshot_mixer_settings = True

    # Update Config
    zynconf.save_config({
        "ZYNTHIAN_UI_SNAPSHOT_MIXER_SETTINGS": str(int(zynthian_gui_config.snapshot_mixer_settings))
    })


def toggle_dpm():
    zynthian_gui_config.enable_dpm = not zynthian_gui_config.enable_dpm


def toggle_preset_preload():
    if zynthian_gui_config.preset_preload:
        logging.info("Preset Preload OFF")
        zynthian_gui_config.preset_preload = False
    else:
        logging.info("Preset Preload ON")
        zynthian_gui_config.preset_preload = True

    # Save config
    zynconf.save_config({"ZYNTHIAN_UI_PRESET_PRELOAD": str(int(zynthian_gui_config.preset_preload))})


# Settings with a value. Each saves the config; the UI redraws what depends on it.

MIXER_TOGGLES = ["solo", "pfl", "mono", "phase", "ms", "record"]


def pfl_output_labels():
    """Choices for the PFL output: None, each hardware playback port and each pair"""
    ports = zynautoconnect.get_hw_audio_dst_ports()
    labels = ["None"]
    for i in range(0, len(ports) - 1, 2):
        try:
            name1 = ports[i].aliases[0]
            name2 = ports[i + 1].aliases[0]
        except Exception:
            name1 = ports[i].name
            name2 = ports[i + 1].name
        labels.append(f"{i + 1} ({name1})")
        labels.append(f"{i + 2} ({name2})")
        labels.append(f"{i + 1}+{i + 2} ({name1}+{name2})")
    return labels


def _port_label(port):
    try:
        return port.aliases[0]
    except Exception:
        return port.name


def main_output_choices():
    """Choices for the main mix bus output: (label, value); value "" is the default (the first two
    hardware outputs), else the port names joined by "|" (ZYNTHIAN_AUDIO_MAIN_OUTPUT)"""
    ports = zynautoconnect.get_hw_audio_dst_ports()
    choices = [("Default (first two outputs)", "")]
    for i in range(0, len(ports) - 1, 2):
        choices.append((f"{i + 1}+{i + 2} ({_port_label(ports[i])} + {_port_label(ports[i + 1])})",
                        f"{ports[i].name}|{ports[i + 1].name}"))
    return choices


def main_output_label():
    """The current main output setting as shown"""
    value = zynthian_gui_config.main_output
    if not value:
        return "Default"
    for label, v in main_output_choices():
        if v == value:
            return label.split(" ")[0]
    return value.replace("|", " + ") + " (missing: using the default)"


def set_main_output(value):
    zynthian_gui_config.main_output = value
    zynconf.save_config({"ZYNTHIAN_AUDIO_MAIN_OUTPUT": value})
    zynautoconnect.request_audio_connect(True)


def set_pfl_output(label):
    zynthian_gui_config.pfl_output = label
    zynconf.save_config({"ZYNTHIAN_PFL_OUTPUT": label})
    zynautoconnect.request_audio_connect(True)


def set_visible_mixer_strips(value):
    zynthian_gui_config.visible_mixer_strips = value
    zynconf.save_config({"ZYNTHIAN_UI_VISIBLE_MIXER_STRIPS": str(value)})


def set_visible_launchers(value):
    zynthian_gui_config.visible_launchers = value
    zynconf.save_config({"ZYNTHIAN_UI_VISIBLE_LAUNCHERS": str(value)})


def set_mixer_toggle(symbol):
    zynthian_gui_config.mixer_toggle = symbol
    zynconf.save_config({"ZYNTHIAN_UI_MIXER_TOGGLE": symbol})


def set_chanpress_cc(value, state_manager):
    """Channel pressure (mono aftertouch) => CC value; 0: none"""
    zynthian_gui_config.midi_chanpress_cc = value
    state_manager.init_midi_filter()
    zynconf.update_midi_profile({"ZYNTHIAN_MIDI_CHANPRESS_CC": str(int(value))})


# Hotplug USB audio (alsa_in/alsa_out clients)

def _check(flag):
    return "\u2612" if flag else "\u2610"


def hotplug_options():
    """The hotplug audio menu: list of (label, action, device, info); action None for a heading"""
    options = []
    if not zynthian_gui_config.hotplug_audio_enabled:
        return [("\u2610 Hotplug Audio", "enable_hotplug", None, "Toggle USB hotplug audio enable.")]
    options.append(("\u2612 Hotplug Audio", "disable_hotplug", None, "Toggle USB hotplug audio enable."))
    options.append(("Input Devices", None, None, None))
    for device in zynautoconnect.get_alsa_audio_devices(False, "hotplug"):
        on = device not in zynthian_gui_config.disabled_audio_in
        options.append((f"{_check(on)} {device} in", "disable_input" if on else "enable_input",
                        device, "Toggle enable USB input audio device."))
    options.append(("Output Devices", None, None, None))
    devices = zynautoconnect.get_alsa_audio_devices(True, "hotplug")
    for device in devices:
        on = device not in zynthian_gui_config.disabled_audio_out
        options.append((f"{_check(on)} {device} out", "disable_output" if on else "enable_output",
                        device, "Toggle enable USB audio output device."))
    if not devices:
        options.append(("No available soundcard outputs - check ZynVoice", "tts", None,
                        "No free audio outputs. Select to navigate to ZynVoice config."))
    return options


def hotplug_apply(action, device, state_manager):
    """Run a hotplug menu action (except "tts", which the UI handles)"""
    messages = {"enable_hotplug": "Enabling hotplug audio", "disable_hotplug": "Disabling hotplug audio",
                "enable_input": f"Enabling {device} in", "disable_input": f"Disabling {device} in",
                "enable_output": f"Enabling {device} out", "disable_output": f"Disabling {device} out"}
    if action not in messages:
        return
    zynautoconnect.pause()
    state_manager.start_busy("hotplug", messages[action])
    try:
        match action:
            case "enable_hotplug":
                zynautoconnect.enable_hotplug()
            case "disable_hotplug":
                zynautoconnect.disable_hotplug()
            case "enable_input" | "disable_input":
                zynautoconnect.enable_audio_input_device(device, action == "enable_input")
            case "enable_output" | "disable_output":
                zynautoconnect.enable_audio_output_device(device, action == "enable_output")
    finally:
        state_manager.end_busy("hotplug")
        zynautoconnect.resume()
