# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Wiring layout: MIDI set-up of the custom switches, Zynaptik CV in/out and Zyntof sensors, and
# reloading the wiring configuration (webconf's RELOAD_WIRING_LAYOUT). UI-independent part of
# zynthian_gui, used by the Tk and Qt UIs.
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
from zyncoder.zyncore import lib_zyncore
from zyngui import zynthian_gui_config


def wiring_midi_setup(current_chan=None):
    """Initialize custom switches, analog I/O, TOF sensors, etc.

    current_chan: MIDI channel for the events configured without a channel (the active chain's)
    """
    #logging.info("CUSTOM I/O SETUP...")

    # Configure Custom Switches
    for i, event in enumerate(zynthian_gui_config.custom_switch_midi_events):
        # logging.debug(f"\tSWITCH MIDI EVENT {i} => {event}")
        if event is not None:
            swi = 4 + i
            if event['type'] >= 0xF8:
                lib_zyncore.setup_zynswitch_midi(swi, event['type'], 0, 0, 0)
                logging.info(f"MIDI ZYNSWITCH {swi}: SYS-RT {event['type']}")
            else:
                if event['chan'] is not None:
                    midi_chan = event['chan']
                else:
                    midi_chan = current_chan

                if midi_chan is not None:
                    lib_zyncore.setup_zynswitch_midi(swi, event['type'], midi_chan, event['num'], event['val'])
                    logging.info(f"MIDI ZYNSWITCH {swi}: {event['type']} CH#{midi_chan}, {event['num']}, {event['val']}")
                else:
                    lib_zyncore.setup_zynswitch_midi(swi, 0, 0, 0, 0)
                    logging.info(f"MIDI ZYNSWITCH {swi}: DISABLED!")

    # Configure Zynaptik Analog Inputs (CV-IN)
    for i, event in enumerate(zynthian_gui_config.zynaptik_ad_midi_events):
        # logging.debug(f"\tCV-IN MIDI EVENT {i} => {event}")
        if event is not None:
            if event['chan'] is not None:
                midi_chan = event['chan']
            else:
                midi_chan = current_chan

            if midi_chan is not None:
                lib_zyncore.setup_zynaptik_cvin(i, event['type'], midi_chan, event['num'])
                logging.info(f"ZYNAPTIK CV-IN {i}: {event['type']} CH#{midi_chan}, {event['num']}")
            else:
                lib_zyncore.disable_zynaptik_cvin(i)
                logging.info(f"ZYNAPTIK CV-IN {i}: DISABLED!")

    # Configure Zynaptik Analog Outputs (CV-OUT)
    for i, event in enumerate(zynthian_gui_config.zynaptik_da_midi_events):
        # logging.debug(f"\tCV-OUT MIDI EVENT {i} => {event}")
        if event is not None:
            if event['chan'] is not None:
                midi_chan = event['chan']
            else:
                midi_chan = current_chan

            if midi_chan is not None:
                lib_zyncore.setup_zynaptik_cvout(i, event['type'], midi_chan, event['num'])
                logging.info(f"ZYNAPTIK CV-OUT {i}: {event['type']} CH#{midi_chan}, {event['num']}")
            else:
                lib_zyncore.disable_zynaptik_cvout(i)
                logging.info(f"ZYNAPTIK CV-OUT {i}: DISABLED!")

    # Configure Zyntof Inputs (Distance Sensor)
    for i, event in enumerate(zynthian_gui_config.zyntof_midi_events):
        if event is not None:
            if event['chan'] is not None:
                midi_chan = event['chan']
            else:
                midi_chan = current_chan

            if midi_chan is not None:
                lib_zyncore.setup_zyntof(i, event['type'], midi_chan, event['num'])
                logging.info(f"ZYNTOF {i}: {event['type']} CH#{midi_chan}, {event['num']}")
            else:
                lib_zyncore.disable_zyntof(i)
                logging.info(f"ZYNTOF {i}: DISABLED!")


def reload_wiring_layout(current_chan=None):
    """Re-read the configuration and set up the wiring layout's switches and sensors again"""
    try:
        zynconf.load_config()
        zynthian_gui_config.config_custom_switches()
        zynthian_gui_config.config_zynaptik()
        zynthian_gui_config.config_zyntof()
        wiring_midi_setup(current_chan)
    except Exception as e:
        logging.error("ERROR configuring wiring: {}".format(e))
