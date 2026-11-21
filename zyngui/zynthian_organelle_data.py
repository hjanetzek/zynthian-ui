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


# The kits' knobs and switches (zynthian_widget_organelle: zynpot_cb, switch, switch_select_mode,
# switch_aux, cuia_arrow_up/down, update_wsleds)

def kit_switches(check_wiring_layout, touch_navigation=False):
    """(select mode switch, AUX switch, select mode LED, AUX LED) of the kit's wiring layout
    (check_wiring_layout: zynthian_gui_config's); None where the kit has none (touch: the
    on-screen AUX button and encoder instead).

    - V5: F3 (19) select mode, F4 (23) AUX, their LEDs (as the Tk widget).
    - The touch keypad (touch_navigation: zynthian_gui_config.touch_navigation): the same, as
      the keypad sends the V5 switch numbers on any layout (zynthian_gui_config remaps the
      wiring; the Tk mixer and pattern editor take the V5 numbers for it too).
    - Z2: 15 and 16 (as the Tk widget).
    - V4-type kits (MCP23017 layouts: ZynScreen, Zynaptik, ...): S3 (6) select mode, S4 (7)
      AUX, as V5's F3 / F4 (the Tk pattern editor's block / CC keys are S3 / S4 too). The Tk
      widget's "MCP23017_ZYN" (5, 4) matches no layout (check_wiring_layout compares the start,
      case sensitive): Tk has no V4 mapping."""
    if touch_navigation or check_wiring_layout(["V5"]):
        return 19, 23, 12, 13
    if check_wiring_layout(["Z2"]):
        return 15, 16, 13, 14
    if check_wiring_layout(["MCP23017"]):
        return 6, 7, None, None
    return None, None, None, None


class OrganelleKeys:
    """The Organelle's encoder and AUX button on a kit's knobs and switches, as the Tk widget: a
    switch toggles a menu *select mode* (entering it scrolls the menu once, leaving it selects),
    in which knob 3 and the up/down arrows scroll the patch's menu and switch 3 selects (and
    ends the mode); the AUX switch is the AUX button (the long press is off while it is held).

    pulse(path, ms): send path 1, then 0 after ms; send(path, value); on_select_mode(bool): show
    the selector instead of the fourth controller (Tk) or not; autolong(bool): the switches'
    long press while held on / off."""

    def __init__(self, pulse, send, on_select_mode, autolong, switches=(None, None, None, None)):
        self.pulse = pulse
        self.send = send
        self.on_select_mode = on_select_mode
        self.autolong = autolong
        self.switch_selmode, self.switch_aux, self.led_selmode, self.led_aux = switches
        self.selector = True   # the preset's organelle_selector option
        self.select_mode = False
        self.aux_pushed = False

    def set_select_mode(self, on):
        if on != self.select_mode:
            self.select_mode = on
            self.on_select_mode(on)

    def zynpot(self, i, d):
        """Knob i turned by d; True if it scrolled the menu"""
        if self.select_mode and self.selector and i == 3 and d:
            self.pulse("/enc_down" if d > 0 else "/enc_up", 50)
            return True
        return False

    def arrow(self, d):
        """Arrow up (-1) / down (1); True if it scrolled the menu (select mode)"""
        if self.select_mode:
            self.zynpot(3, d)
            return True
        return False

    def switch(self, i, t):
        """Switch i pushed (P) or released after a short (S), bold (B) or long (L) press; True if
        handled"""
        if self.selector and self.select_mode and i == 3:
            if t == "S":
                self.pulse("/enc_sel", 100)
                self.set_select_mode(False)
                return True
            return False
        if self.selector and self.switch_selmode is not None and i == self.switch_selmode:
            if t in ("S", "B"):
                self.toggle_select_mode()
            return True
        if self.switch_aux is not None and i == self.switch_aux:
            pushed = t == "P"
            if pushed != self.aux_pushed:
                self.aux_pushed = pushed
                self.autolong(not pushed)
                self.send("/aux", 1 if pushed else 0)
            return True
        return False

    def select(self):
        """The SEL key (SELECT_ACTION) or the on-screen SEL button: in select mode the menu entry
        is selected and the mode ends, as switch 3 (on V4 kits the SEL switch); True if taken"""
        return self.switch(3, "S")

    def labels(self):
        """{switch: label} of the switches taken (the touch keypad's F-key labels)"""
        out = {}
        if self.selector and self.switch_selmode is not None:
            out[self.switch_selmode] = "SELECT" if self.select_mode else "MENU"
        if self.switch_aux is not None:
            out[self.switch_aux] = "AUX"
        return out

    def toggle_select_mode(self):
        if self.select_mode:
            self.set_select_mode(False)
            self.pulse("/enc_sel", 100)
        else:
            self.set_select_mode(True)
            self.pulse("/enc_down", 50)

    def reset(self):
        """Leave select mode and release AUX (the widget hidden or another processor)"""
        self.set_select_mode(False)
        if self.aux_pushed:
            self.aux_pushed = False
            self.autolong(True)
            self.send("/aux", 0)

    def update_wsleds(self, wsl, leds):
        """The kit's LEDs (wsl: the LED driver's API, leds: the screen's custom LED indices)"""
        if self.led_selmode is not None and self.selector:
            if self.select_mode:
                wsl.blink(leds[self.led_selmode], wsl.wscolor_active2)
            else:
                wsl.set_led(leds[self.led_selmode], wsl.wscolor_active2)
        if self.led_aux is not None:
            wsl.set_led(leds[self.led_aux], wsl.wscolor_green if self.aux_pushed else wsl.wscolor_active2)
