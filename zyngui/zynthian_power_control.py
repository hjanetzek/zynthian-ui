# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Powering off and rebooting: how, on the system zynthian runs on. ZynthianOS's zynthian.sh
# powers off when the UI exits with code 0 and reboots with 100 (zynthian_gui_admin); a Nura
# kiosk session restarts zynthian whatever the exit code, so there the session user asks logind
# (systemctl poweroff / reboot; polkit allows it for the active local session); on a desktop
# zynthian doesn't power off the computer.
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
import shutil
import logging
import subprocess

import zynconf

# Installed by postmarketos-ui-zynthian (nura/): the kiosk sessions' shared script
NURA_SESSION_SCRIPT = "/usr/libexec/zynthian/zynthian-session.sh"

POWEROFF = "poweroff"
REBOOT = "reboot"

# UI exit codes zynthian.sh acts on (as zynthian_gui_admin.power_off_confirmed / reboot_confirmed)
EXIT_CODES = {POWEROFF: 0, REBOOT: 100}


def power_method():
    """How to power off / reboot here:
    "desktop": not at all (a desktop computer's session, ZYNTHIAN_DESKTOP=1);
    "logind": `systemctl poweroff|reboot` (Nura kiosk session with systemd);
    "exit_code": exit the UI with EXIT_CODES (ZynthianOS's zynthian.sh does the rest)."""
    if zynconf.desktop_mode:
        return "desktop"
    if os.path.exists(NURA_SESSION_SCRIPT):
        if os.path.isdir("/run/systemd/system") and shutil.which("systemctl"):
            return "logind"
        logging.warning("Nura session without systemd: powering off through the exit code")
    return "exit_code"


def logind_command(action):
    return ["systemctl", "--no-ask-password", action]


def logind_power(action):
    """Ask logind to power off / reboot (blocks until systemctl returns). Returns an error
    message, or None when the job was accepted."""
    try:
        result = subprocess.run(logind_command(action), capture_output=True, text=True, timeout=20)
    except Exception as e:
        return str(e)
    if result.returncode != 0:
        return (result.stderr or result.stdout).strip() or f"systemctl {action} failed ({result.returncode})"
    return None
