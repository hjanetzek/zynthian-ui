# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Admin settings that are simple toggles: UI-independent part of zynthian_gui_admin, used by the
# Tk and Qt UIs.
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
