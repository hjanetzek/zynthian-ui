"""Third-party zynthian widgets (Tk code: zyngui:widget bundles, user widgets) in the Qt UI through
the widget shim of an external package, zynwidgets (declarations drawn natively, and a tkinter
stand-in painted by Qt for Tk widgets). ZYNTHIAN_QT_WIDGET_SHIM is the directory that holds its
zynwidgets package (or the older zynthian_widgets_qt). Unset, or if it fails to load, such widgets
show the "can't show" note as before.

The shim gets the chain control's widget slot: ChainControl asks it for pages whose processor
has a widget without a Qt view (widgetType "tk"), and passes it the refresh, knobs, switches
and CUIAs first, as zynthian_gui_control does with its widgets."""

import importlib
import logging
import os
import sys

ENV = "ZYNTHIAN_QT_WIDGET_SHIM"

_hook = None
_tried = False


def hook():
    """The shim's hook module (zynwidgets.hook, or zynthian_widgets_qt.qt.hook), None without it"""
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
    for name in ("zynwidgets.hook", "zynthian_widgets_qt.qt.hook"):
        try:
            h = importlib.import_module(name)
        except ModuleNotFoundError as e:
            if e.name and name.startswith(e.name):
                continue
            logging.exception(f"Can't load the widget shim from {path}: {e}")
            break
        except Exception as e:
            logging.exception(f"Can't load the widget shim from {path}: {e}")
            break
        _hook = h
        logging.info(f"Widget shim {name} from {path} (API {getattr(h, 'API_VERSION', '?')})")
        break
    else:
        logging.error(f"No widget shim (zynwidgets) in {path}")
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
