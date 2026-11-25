#!/usr/bin/python3
# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Controller settings: the settings of the controller drivers which have their own (the
# DrivenByMoss drivers), independent of the UI toolkit (docs/controller-settings.md)
#
# Copyright (C) 2026 Hannes Janetzek
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

"""The settings of controller drivers, for a settings screen of any UI.

A driver has settings when it has these three (duck-typed; any thread may call them):

    get_settings()             the settings, a list of dicts (see below); empty while the
                               controller doesn't run. The list is the driver's: don't change it.
    set_setting(id, value)     set a setting (value: str; a signal: any value presses it). The
                               driver applies it on its own thread; True if it took it.
    settings_revision          an int which changes whenever the list changes (the UI's own
                               changes, the controller's, visibility and enabled states)

A setting is a dict with
    id        int
    scope     "global" (kept by the controller) or "document" (in the snapshot)
    kind      "enum", "integer", "boolean", "text", "signal" or "action"
    category  the group it belongs to
    label     its name
    default   the default value (str)
    value     the current value (str; booleans "true" / "false")
    extra     an enum's options, an integer's minimum and maximum, a signal's button text
    visible   False: not shown
    enabled   False: shown greyed out, not changeable

The functions here turn that into what a screen lists (drivers, categories, settings) and the
values to set; the screens (zynqt/screens/controller_settings.py) only show them.
"""

# The kinds a screen shows (action: not yet, it needs a host action list)
SHOWN_KINDS = ("enum", "integer", "boolean", "text", "signal")


def has_settings(driver):
    return (callable(getattr(driver, "get_settings", None)) and callable(getattr(driver, "set_setting", None))
            and hasattr(driver, "settings_revision"))


def settings_drivers(ctrldev_manager):
    """The loaded drivers with settings, in the manager's order (MIDI devices, then HID)"""
    if ctrldev_manager is None:
        return []
    drivers = list(getattr(ctrldev_manager, "drivers", {}).values())
    drivers += list(getattr(ctrldev_manager, "hid_drivers", {}).values())
    return [d for d in drivers if has_settings(d)]


def driver_title(driver):
    """The driver's name (zynthian_ctrldev_base.get_driver_name), else its class name"""
    try:
        name = driver.get_driver_name()
        if name:
            return str(name)
    except Exception:
        pass
    return type(driver).__name__


def driver_settings(driver):
    """The driver's settings (a list; empty if it has none or fails)"""
    try:
        return list(driver.get_settings() or [])
    except Exception:
        return []


def revision(driver):
    try:
        return driver.settings_revision
    except Exception:
        return None


def is_shown(setting):
    return setting.get("visible", True) and setting.get("kind") in SHOWN_KINDS


def is_enabled(setting):
    return bool(setting.get("enabled", True))


def categories(settings):
    """The categories with shown settings, in the order of their first setting"""
    result = []
    for s in settings:
        if is_shown(s) and s.get("category", "") not in result:
            result.append(s.get("category", ""))
    return result


def category_settings(settings, category):
    return [s for s in settings if is_shown(s) and s.get("category", "") == category]


def find(settings, setting_id):
    return next((s for s in settings if s.get("id") == setting_id), None)


# Values

def enum_options(setting):
    return list(setting.get("extra") or [])


def int_range(setting):
    """(min, max) of an integer setting; without them 0..127 widened to hold the value"""
    extra = setting.get("extra") or []
    vmin = _int(extra[0], None) if len(extra) > 0 else None
    vmax = _int(extra[1], None) if len(extra) > 1 else None
    value = int_value(setting)
    if vmin is None:
        vmin = min(0, value)
    if vmax is None or vmax < vmin:
        vmax = max(vmin, 127, value)
    return vmin, vmax


def int_value(setting):
    return _int(setting.get("value"), _int(setting.get("default"), 0))


def clamp_int(setting, value):
    vmin, vmax = int_range(setting)
    return max(vmin, min(vmax, int(value)))


def bool_value(setting):
    return str(setting.get("value", "")).strip().lower() in ("true", "1", "on", "yes")


def bool_text(on):
    """A boolean as the core takes it"""
    return "true" if on else "false"


def signal_text(setting):
    """A signal's button text, else its label"""
    extra = setting.get("extra") or []
    text = extra[0].strip() if extra and isinstance(extra[0], str) else ""
    return text or label(setting)


def label(setting):
    """The setting's label; a signal without one: its button text (extra), as Bitwig shows it"""
    text = str(setting.get("label", "")).strip()
    if not text and setting.get("kind") == "signal":
        text = str(setting.get("extra", "") or "").strip()
    return text or f"Setting {setting.get('id')}"


def value_text(setting):
    """The value as a list shows it"""
    kind = setting.get("kind")
    if kind == "boolean":
        return "On" if bool_value(setting) else "Off"
    if kind == "integer":
        return str(int_value(setting))
    if kind == "signal":
        return signal_text(setting)
    return str(setting.get("value", ""))


def info_text(setting):
    """An info text: what it is, its default, where it is kept"""
    kind = setting.get("kind")
    lines = []
    if kind == "enum":
        lines.append(f"{label(setting)}: {value_text(setting)}")
    elif kind == "integer":
        vmin, vmax = int_range(setting)
        lines.append(f"{label(setting)}: {value_text(setting)} ({vmin} to {vmax})")
    elif kind == "boolean":
        lines.append(f"{label(setting)}: {value_text(setting)}")
    elif kind == "text":
        lines.append(f"{label(setting)}: {setting.get('value', '')}")
    elif kind == "signal":
        lines.append(f"Press to {signal_text(setting).lower()}." if signal_text(setting) != label(setting)
                     else f"{label(setting)}: press to run it.")
    default = setting.get("default", "")
    if kind not in ("signal", "action") and default != "":
        shown = ("On" if str(default).lower() == "true" else "Off") if kind == "boolean" else default
        lines.append(f"Default: {shown}")
    if setting.get("scope") == "document":
        lines.append("Saved with the snapshot.")
    else:
        lines.append("Kept by the controller.")
    if not is_enabled(setting):
        lines.append("Not available in the current mode of the controller.")
    return "\n".join(lines)


def apply(driver, setting, value):
    """Set a setting on its driver: value as the core takes it (str); a signal ignores it"""
    if setting.get("kind") == "signal":
        value = ""
    elif setting.get("kind") == "boolean" and isinstance(value, bool):
        value = bool_text(value)
    elif setting.get("kind") == "integer":
        value = str(clamp_int(setting, value))
    try:
        return driver.set_setting(setting["id"], str(value)) is not False
    except Exception:
        return False


def _int(value, default):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        try:
            return int(float(str(value).strip()))
        except (TypeError, ValueError):
            return default
