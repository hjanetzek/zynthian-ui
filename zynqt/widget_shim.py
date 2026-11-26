"""Third-party zynthian widgets (Tk code: zyngui:widget bundles, user widgets) in the Qt UI through
the widget shim, an external package (zynthian-widgets-qt: a tkinter stand-in painted by Qt).
ZYNTHIAN_QT_WIDGET_SHIM is the directory that holds its zynthian_widgets_qt package. Unset, or if
it fails to load, such widgets show the "can't show" note as before.

The shim gets the chain control's widget slot: ChainControl asks it for pages whose processor
has a widget without a Qt view (widgetType "tk"), and passes it the refresh, knobs, switches
and CUIAs first, as zynthian_gui_control does with its widgets."""

import logging
import os
import sys

ENV = "ZYNTHIAN_QT_WIDGET_SHIM"

_hook = None
_tried = False


def hook():
    """The shim's hook module (zynthian_widgets_qt.qt.hook), None without it"""
    global _hook, _tried
    if _tried:
        return _hook
    _tried = True
    path = os.environ.get(ENV, "").strip()
    if not path:
        return None
    path = os.path.expanduser(path)
    if path not in sys.path:
        sys.path.insert(0, path)
    try:
        from zynthian_widgets_qt.qt import hook as h
        _hook = h
        logging.info(f"Widget shim from {path} (API {getattr(h, 'API_VERSION', '?')})")
    except Exception as e:
        logging.exception(f"Can't load the widget shim from {path}: {e}")
    return _hook


def register_qml():
    """Before the QML engine loads"""
    h = hook()
    if h is not None:
        try:
            h.register_qml()
        except Exception as e:
            logging.exception(f"Widget shim QML types: {e}")


def create_view(chain_control):
    """The shim's view for a ChainControl, None without the shim"""
    h = hook()
    if h is None:
        return None
    try:
        return h.create_view(chain_control)
    except Exception as e:
        logging.exception(f"Widget shim view: {e}")
        return None
