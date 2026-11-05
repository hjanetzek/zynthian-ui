# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Organelle widget: UI-independent part of zynthian_widget_organelle. Organelle patches (Pure
# Data) draw on a 128x64 OLED through OSC messages (/oled/g...); parse_oled() turns them into
# drawing operations in OLED pixels, OledScene keeps them as a display list (with the menu
# lines and the inverted one), menu_touch_sequence() gives the encoder messages that select a
# menu line. Used by the Tk and Qt UIs.
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

OLED_WIDTH = 128
OLED_HEIGHT = 64

# gCleanln n: the area of text line n (gFillArea arguments)
CLEANLN_FILL = {
    1: [0, 0, 8, 128, 9, 0],
    2: [0, 0, 20, 128, 9, 0],
    3: [0, 0, 32, 128, 9, 0],
    4: [0, 0, 44, 128, 9, 0],
    5: [0, 0, 54, 128, 10, 0]
}

MAX_ITEMS = 4000   # display list limit (patches clear regularly; this only bounds a runaway)


def parse_oled(path, args):
    """An /oled/... OSC message as a drawing operation: dict with "op" and its values in OLED
    pixels (color 1 white, 0 black), or None if not an OLED message / invalid"""
    try:
        match path:
            case "/oled/gClear":
                return {"op": "clear"}
            case "/oled/gFlip":
                return {"op": "flip"}
            case "/oled/gCleanln":
                fill = CLEANLN_FILL.get(int(args[0]))
                if fill is None:
                    logging.error(f"gCleanln received an invalid line number: {args}")
                    return None
                return parse_oled("/oled/gFillArea", fill)
            case "/oled/gSetPixel":
                _, x, y, c = args[:4]
                return {"op": "pixel", "x": int(x), "y": int(y), "color": int(c)}
            case "/oled/gLine":
                _, x1, y1, x2, y2, c = args[:6]
                return {"op": "line", "x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2), "color": int(c)}
            case "/oled/gBox" | "/oled/gFillArea":
                _, x, y, w, h, c = args[:6]
                return {"op": "box" if path == "/oled/gBox" else "fill",
                        "x": int(x), "y": int(y), "w": int(w), "h": int(h), "color": int(c)}
            case "/oled/gCircle" | "/oled/gFilledCircle":
                _, x, y, r, c = args[:5]
                return {"op": "circle" if path == "/oled/gCircle" else "fcircle",
                        "x": int(x), "y": int(y), "r": int(r), "color": int(c)}
            case "/oled/gPrintln":
                _, x, y, size, c = args[:5]
                text = " ".join(map(str, args[5:])).strip()
                if not text:
                    return None
                try:
                    size = int(size)
                except Exception:
                    size = 8
                return {"op": "text", "x": int(x), "y": int(y) - 1, "size": size, "color": int(c), "text": text}
            case "/oled/ginvertLine":
                return {"op": "invert_line", "page": int(args[0])}
            case "/oled/gInvertArea":
                _, x, y, w, h = args[:5]
                return {"op": "invert_area", "x": int(x), "y": int(y), "w": int(w), "h": int(h)}
    except Exception as e:
        logging.error(f"Organelle OSC {path} {args}: {e}")
    return None


class OledScene:
    """The OLED as a display list: items in drawing order; a text replaces the previous text
    at the same position; texts at x <= 10 are menu lines (by y); one of them inverted."""

    def __init__(self):
        self.clear()

    def clear(self):
        self.items = []
        self.menu_lines = set()   # y of the menu lines
        self.page = 0             # inverted menu line (index into the sorted menu lines)
        self.inverted = None      # y of the inverted menu line, or None

    def apply(self, op):
        """Apply a parse_oled() operation; True if the display changed"""
        kind = op["op"]
        if kind == "clear":
            self.clear()
        elif kind == "flip":
            return False
        elif kind == "text":
            self.items = [i for i in self.items if not (i["op"] == "text" and i["x"] == op["x"] and i["y"] == op["y"])]
            self.items.append(op)
            if op["x"] <= 10:
                self.menu_lines.add(op["y"])
        elif kind == "invert_line":
            self.set_page(op["page"])
        else:
            self.items.append(op)
        if len(self.items) > MAX_ITEMS:
            del self.items[:len(self.items) - MAX_ITEMS]
        return True

    def sorted_menu_lines(self):
        return sorted(self.menu_lines)

    def set_page(self, page):
        self.page = page
        lines = self.sorted_menu_lines()
        self.inverted = lines[max(0, min(page, len(lines) - 1))] if lines else None

    def menu_index(self, y):
        """Index of the menu line drawn at OLED row y (between its top and the next line's), or
        None"""
        lines = self.sorted_menu_lines()
        best = None
        for i, ly in enumerate(lines):
            if y >= ly - 2:
                best = i
        return best


def menu_touch_sequence(current_index, target_index, step_ms=50):
    """The encoder messages that move the patch's menu from current_index to target_index and
    select it (zynthian_widget_organelle.on_text_touch): list of (delay ms, path, value)"""
    seq = []
    diff = target_index - current_index
    path = "/enc_down" if diff > 0 else "/enc_up"
    for i in range(abs(diff)):
        seq.append((step_ms * i, path, 1))
        seq.append((step_ms * i + step_ms, path, 0))
    total = abs(diff) * step_ms + 100
    seq.append((total, "/enc_sel", 1))
    seq.append((total + 100, "/enc_sel", 0))
    return seq
