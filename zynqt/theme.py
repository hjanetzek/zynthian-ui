"""The Qt UI's theme (ZYNTHIAN_QT_THEME) as QML file selectors.

zynqt/qml/ itself is the default theme, tk (zynthian's Tk UI). Each other theme is a directory
zynqt/qml/+<name>/ whose files replace those of the same name (QQmlFileSelector); the engine gets
the theme's selectors in priority order. A theme builds on the base, or on another theme's
directory (BASES): galactica and enterprise build on classic, so their selectors are
[name, "classic"] and Qt looks for X.qml in +name/, then +classic/, then zynqt/qml/."""

import logging
import os

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
