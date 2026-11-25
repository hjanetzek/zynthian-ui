"""The Qt UI's theme (ZYNTHIAN_QT_THEME) as QML file selectors.

zynqt/qml/ itself is the default theme, tk (zynthian's Tk UI). Each other theme is a directory
zynqt/qml/+<name>/ whose files replace those of the same name (QQmlFileSelector); the engine gets
the theme's selectors in priority order. A theme builds on the base, or on another theme's
directory (BASES): galactica and enterprise build on classic, so their selectors are
[name, "classic"] and Qt looks for X.qml in +name/, then +classic/, then zynqt/qml/."""

import logging
import os
import re
import subprocess

DEFAULT = "tk"
# The theme each theme builds on (absent: the base, tk; v4, the V4 kits' 480x320 layout, is on tk:
# its selectors are just ["v4"])
BASES = {"galactica": "classic", "enterprise": "classic"}


def theme_selectors(name, qml_dir):
    """The theme's name (DEFAULT for an empty or unknown one) and its file selectors, the
    theme's own first"""
    name = (name or "").strip() or DEFAULT
    if name != DEFAULT and not os.path.isdir(os.path.join(qml_dir, "+" + name)):
        logging.warning("Unknown Qt theme '%s' (no %s/+%s): using %s", name, qml_dir, name, DEFAULT)
        name = DEFAULT
    selectors = []
    theme = name
    while theme != DEFAULT and theme not in selectors:
        selectors.append(theme)
        theme = BASES.get(theme, DEFAULT)
    return name, selectors


# What a theme looks like, for the Admin menu's theme list (a theme without an entry gets a
# generic text)
DESCRIPTIONS = {
    "tk": "The look of zynthian's Tk UI: its colours and sizes (ZYNTHIAN_UI_COLOR_*, font size and "
          "scale).",
    "classic": "The Qt port's first look: black, slate-blue plates, red selection, blue keys.",
    "galactica": "A battlestar console: gun-metal plates with clipped corners, amber text.",
    "enterprise": "A starship console: pill keys in orange, blue-gray and violet, a curved frame.",
    "v4": "The V4 kits' 480x320 screen with two knobs on each side: Tk's V4 layout, no on-screen "
          "keypad.",
}


def available_themes(qml_dir):
    """The themes there are: the base (DEFAULT), then each zynqt/qml/+<name>/ with a Theme.qml"""
    names = sorted(entry[1:] for entry in os.listdir(qml_dir)
                   if entry.startswith("+") and os.path.isfile(os.path.join(qml_dir, entry, "Theme.qml")))
    return [DEFAULT] + [n for n in names if n != DEFAULT]


# The user's choice (Admin > Theme) is ZYNTHIAN_QT_THEME in zynthian's config, which the launcher
# (desktop/zynthian_desktop.sh) sources at each UI start, in that start's subshell, after the
# session exported its value (/etc/default/zynthian): zynthian_envars.sh, or
# zynthian_custom_config.sh if that sets it (it is sourced last, so it wins). "Default" removes the
# user's value: the next start (RESTART_UI) has the session's again.
VAR = "ZYNTHIAN_QT_THEME"
# Until 2026-11-25 (when the launcher kept the variables it had exported), "Default" wrote a line
# with this mark that set the session's value for one start; the UI removed it when it started.
# drop_once_lines() still removes such a line left in a config (chosen before an upgrade, no start
# since): it would set the theme of that day for good. To go in a later cycle
ONCE_MARK = "# zynthian: Admin > Theme > Default, for one start"
SESSION_DEFAULTS = "/etc/default/zynthian"
_EXPORT = re.compile(r"^\s*export\s+" + VAR + r"=")


def _config_files():
    from zynconf import zynthian_config
    return (zynthian_config.config_fpath,
            os.path.join(zynthian_config.config_dir, "zynthian_custom_config.sh"))


def _read_lines(fpath):
    try:
        with open(fpath) as f:
            return f.readlines()
    except OSError:
        return None


def _write_lines(fpath, lines):
    with open(fpath, "w") as f:
        f.writelines(lines)
        f.flush()
        os.fsync(f.fileno())


def _user_lines(lines):
    return [line for line in lines or [] if _EXPORT.match(line) and ONCE_MARK not in line]


def custom_config_sets_theme():
    """zynthian_custom_config.sh exports the theme itself (the Admin choice is then saved there)"""
    return bool(_user_lines(_read_lines(_config_files()[1])))


def user_theme():
    """The theme the user chose (the value in zynthian's config), "" for none (default)"""
    value = ""
    for fpath in _config_files():   # the launcher's order: the last one wins
        for line in _user_lines(_read_lines(fpath)):
            value = line.split("=", 1)[1].split("#", 1)[0].strip().strip("\"'")
    return value


def session_theme():
    """The theme the session sets (/etc/default/zynthian: the kit's), "" for none"""
    if not os.path.isfile(SESSION_DEFAULTS):
        return ""
    try:
        return subprocess.run(["/bin/sh", "-c", f'unset {VAR}; . "$1" >/dev/null 2>&1; printf %s "${VAR}"',
                               "sh", SESSION_DEFAULTS],
                              capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError) as err:
        logging.warning("Can't read %s: %s", SESSION_DEFAULTS, err)
        return ""


def save_theme(name):
    """Save the user's theme for the next UI start; "" for the default (the session's theme)"""
    from zynconf import zynthian_config
    envars, custom = _config_files()
    drop_once_lines()
    if name:
        # Where it is set already and wins: the custom config, else zynthian_envars.sh
        fpath = custom if custom_config_sets_theme() else envars
        zynthian_config.save_config({VAR: name}, fpath=fpath)
        logging.info("Qt theme '%s' saved in %s", name, fpath)
        return
    for fpath in (envars, custom):
        lines = _read_lines(fpath)
        if lines is not None:
            kept = [line for line in lines if not _EXPORT.match(line)]
            if kept != lines:
                _write_lines(fpath, kept)
    logging.info("Qt theme: the user's choice removed, the session's ('%s') from the next start",
                 session_theme())


def drop_once_lines():
    """Remove a line the old "Default" left for one start (ONCE_MARK; called when the UI starts
    and by save_theme())"""
    try:
        envars = _config_files()[0]
    except Exception as err:
        logging.warning("No zynthian config: %s", err)
        return
    lines = _read_lines(envars)
    if lines:
        kept = [line for line in lines if ONCE_MARK not in line]
        if kept != lines:
            _write_lines(envars, kept)
