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
# (desktop/zynthian_desktop.sh) sources at each UI start, after the session exported its value
# (/etc/default/zynthian): zynthian_envars.sh, or zynthian_custom_config.sh if that sets it (it is
# sourced last, so it wins). "Default" removes the user's value. The launcher keeps the value it
# exported last, though, so for one start a line marked ONCE_MARK sets the session's value again
# (or unsets the variable); the UI removes it when it starts (drop_once_lines()).
VAR = "ZYNTHIAN_QT_THEME"
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
    if name:
        drop_once_lines()
        # Where it is set already and wins: the custom config, else zynthian_envars.sh
        fpath = custom if custom_config_sets_theme() else envars
        zynthian_config.save_config({VAR: name}, fpath=fpath)
        logging.info("Qt theme '%s' saved in %s", name, fpath)
        return
    for fpath in (envars, custom):
        lines = _read_lines(fpath)
        if lines is not None:
            kept = [line for line in lines if not _EXPORT.match(line)
                    and not (ONCE_MARK in line and VAR in line)]
            if kept != lines:
                _write_lines(fpath, kept)
    session = session_theme()
    once = f'export {VAR}="{session}"' if session else f"unset {VAR}"
    lines = _read_lines(envars) or []
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    _write_lines(envars, lines + [f"{once}  {ONCE_MARK}\n"])
    logging.info("Qt theme: the user's choice removed, the session's ('%s') for the next start", session)


def drop_once_lines():
    """Remove the line save_theme("") left for one start (called when the UI starts: the launcher
    has the value by then)"""
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
