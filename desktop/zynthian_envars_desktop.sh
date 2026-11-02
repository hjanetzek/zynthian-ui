#!/bin/bash
#******************************************************************************
# ZYNTHIAN PROJECT: Zynthian Environment Vars, desktop Linux variant
#
# Template for $ZYNTHIAN_CONFIG_DIR/zynthian_envars.sh on a desktop (or Nura)
# install. Copied once by desktop/setup_desktop.sh; the UI edits the copy.
#
# Unlike zynthian-sys/scripts/zynthian_envars.sh it does not set the directory
# variables: desktop/zynthian_desktop.sh exports them before sourcing this file.
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
# ****************************************************************************

# Kit config
export ZYNTHIAN_KIT_VERSION="Desktop"

# System Config
export BOOTLOG="0"
export ZYNTHIAN_CUSTOM_BOOT_CMDLINE=""
export ZYNTHIAN_CUSTOM_CONFIG=""
export ZYNTHIAN_OVERCLOCKING="None"
export ZYNTHIAN_LIMIT_USB_SPEED="0"
export ZYNTHIAN_DISABLE_OTG="1"
export ZYNTHIAN_WIFI_MODE="off"

#Audio Config
# JACK is provided by the desktop (pipewire-jack); there is no jackd to configure.
export SOUNDCARD_NAME="Desktop"
export SOUNDCARD_CONFIG=""
export SOUNDCARD_MIXER=""
export JACKD_OPTIONS=""
export ZYNTHIAN_DISABLE_RBPI_AUDIO="1"
export ZYNTHIAN_RBPI_HEADPHONES="0"

#Display Config
export DISPLAY_NAME="Desktop window"
export DISPLAY_CONFIG=""
export DISPLAY_WIDTH="1024"
export DISPLAY_HEIGHT="600"
export DISPLAY_ROTATION="None"
export FRAMEBUFFER=""
export DISPLAY_KERNEL_OPTIONS=""

#Wiring Config
# No GPIO: zyncore is built with the wiringPi stand-in, navigation is by
# touch, mouse and keyboard.
export ZYNTHIAN_WIRING_LAYOUT="DUMMIES"
export ZYNTHIAN_WIRING_ENCODER_A=""
export ZYNTHIAN_WIRING_ENCODER_B=""
export ZYNTHIAN_WIRING_SWITCHES=""
export ZYNTHIAN_WIRING_MCP23017_I2C_ADDRESS=""
export ZYNTHIAN_WIRING_MCP23017_INTA_PIN=""
export ZYNTHIAN_WIRING_MCP23017_INTB_PIN=""

#UI Config
export ZYNTHIAN_UI_COLOR_BG="#000000"
export ZYNTHIAN_UI_COLOR_TX="#ffffff"
export ZYNTHIAN_UI_COLOR_ON="#ff0000"
export ZYNTHIAN_UI_COLOR_PANEL_BG="#3a424d"
export ZYNTHIAN_UI_FONT_FAMILY="Audiowide"
export ZYNTHIAN_UI_FONT_SIZE="16"
export ZYNTHIAN_UI_ENABLE_CURSOR="1"
export ZYNTHIAN_UI_TOUCH_WIDGETS="0"
export ZYNTHIAN_UI_TOUCH_NAVIGATION="1"
export ZYNTHIAN_UI_RESTORE_LAST_STATE="1"
export ZYNTHIAN_UI_SNAPSHOT_MIXER_SETTINGS="1"
export ZYNTHIAN_UI_SWITCH_BOLD_MS="300"
export ZYNTHIAN_UI_SWITCH_LONG_MS="2000"
export ZYNTHIAN_UI_SHOW_CPU_STATUS="0"
export ZYNTHIAN_UI_VISIBLE_MIXER_STRIPS="0"
export ZYNTHIAN_UI_MULTICHANNEL_RECORDER="1"
export ZYNTHIAN_UI_POWER_SAVE_MINUTES="0"
export ZYNTHIAN_VNCSERVER_ENABLED="0"

# MIDI Options
export ZYNTHIAN_MIDI_PLAY_LOOP="1"

# MIDI system configuration
export ZYNTHIAN_SCRIPT_MIDI_PROFILE="$ZYNTHIAN_CONFIG_DIR/midi-profiles/default.sh"
export ZYNTHIAN_USB_MIDI_BY_PORT="0"

# Extra features
export ZYNTHIAN_AUBIONOTES_OPTIONS="-O complex -t 0.5 -s -88  -p yinfft -l 0.5"

# Directory Paths
# Set by desktop/zynthian_desktop.sh, see there.
