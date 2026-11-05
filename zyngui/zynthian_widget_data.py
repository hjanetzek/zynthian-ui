# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Engine widgets: UI-independent part of zynthian_gui_control's widget selection and of the
# envelope and filter widgets (their geometry and drag behaviour), used by the Tk and Qt UIs.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

import math

AUDIO_FILE_TYPES = {"wav", "aiff", "flac", "mp3", "ogg"}


def screen_type(zctrls):
    """Widget type of a controller page (zynthian_gui_control.get_screen_type): (type, zctrl),
    type "envelope", "filter", "audio_file" (zctrl: its file controller) or None"""
    for zctrl in zctrls:
        if zctrl is None:
            continue
        if hasattr(zctrl, "envelope"):
            return "envelope", None
        if hasattr(zctrl, "filter"):
            return "filter", None
        if zctrl.is_path and zctrl.path_file_types and (set(zctrl.path_file_types) & AUDIO_FILE_TYPES):
            return "audio_file", zctrl
    return None, None


# Envelope (zynthian_widget_envelope)

ENVELOPE_PHASES = ["delay", "attack", "hold", "decay", "sustain", "fade", "release"]


def envelope_zctrls(group_zctrls):
    """The envelope controllers of a controller group, in phase order, and the fade polarity
    (-1 when fade can be negative)"""
    by_phase = {}
    for zctrl in group_zctrls:
        try:
            by_phase[zctrl.envelope] = zctrl
        except AttributeError:
            pass
    zctrls = [by_phase[phase] for phase in ENVELOPE_PHASES if phase in by_phase]
    fade_polarity = -1 if "fade" in by_phase and by_phase["fade"].value_min < 0 else 1
    return zctrls, fade_polarity


def envelope_values(zctrls):
    return [zctrl.value / zctrl.value_range for zctrl in zctrls]


def envelope_geometry(zctrls, values, fade_polarity, plot_width, plot_height, m_l, m_b, drag_zctrl=None):
    """The envelope shape: (polygon coords [x0, y0, x1, y1, ...], click ranges (x where each
    phase ends, for envelope_hit), the dragged phase's polygon or None). values: envelope_values."""
    dx = plot_width // max(1, len(zctrls))
    dy = int(0.95 * plot_height)
    y_sustain = plot_height // 2
    x_release = plot_width
    rv_fade = None
    for zctrl, rv in zip(zctrls, values):
        match zctrl.envelope:
            case "sustain":
                y_sustain = plot_height - rv * dy
            case "release":
                x_release = plot_width - rv * dx
            case "fade":
                rv_fade = rv
    if rv_fade is None:
        y_fade = y_sustain
    else:
        kf = 1.0 - 0.5 * (fade_polarity - 1) + fade_polarity * rv_fade
        y_fade = plot_height - kf * (plot_height - y_sustain) / 2

    y_sustain += m_b
    y_fade += m_b
    x_release += m_l
    x = x0 = m_l
    y = y0 = m_b + plot_height
    x1 = x0 + plot_width
    coords = [x0, y0]
    click_ranges = []
    drag_poly = None
    for zctrl, rv in zip(zctrls, values):
        match zctrl.envelope:
            case "release":
                x = x1 - rv * dx
                drag_window = [x, y, x1, y0, x, y0]
                click_ranges.append(x)
                if coords[-2] == x1:
                    coords[-2] = x   # Fix fade if it exists
            case "sustain":
                y = y0 - rv * dy
                drag_window = [x, y0, x, y, x_release, y_fade, x_release, y0]
            case "fade":
                y_offset = y + (y0 - y) / 2
                drag_window = [x, y, x, y_offset]
                click_ranges.append(x + (x_release - x) * 0.75)
                x = x_release
                y = y_fade
                drag_window += [x, y_offset, x, y]
            case _:
                _x = x
                drag_window = [x, y]
                x += rv * dx
                if zctrl.envelope == "attack":
                    y = y0 - dy
                elif zctrl.envelope == "decay":
                    y = y_sustain
                drag_window += [x, y, x, y0, _x, y0]
                click_ranges.append(x)
        coords += [x, y]
        if drag_zctrl is zctrl:
            drag_poly = drag_window
    x = m_l + plot_width
    coords += [x, y0]
    click_ranges.append(x)
    return coords, click_ranges, drag_poly


def envelope_hit(zctrls, click_ranges, x):
    """The envelope controller of the phase at x (pressing near a phase's end selects it)"""
    for i in range(len(click_ranges) - 1):
        # Allow selection of last phase, near end of penultimate phase
        if i == len(click_ranges) - 2:
            limit = click_ranges[i] - (click_ranges[i] - click_ranges[i - 1]) / 4
        else:
            limit = click_ranges[i] + (click_ranges[i + 1] - click_ranges[i]) / 4
        if x < limit:
            return zctrls[i]
    return zctrls[-1] if zctrls else None


def envelope_drag(zctrl, click_value, dx_px, dy_px, n_phases, plot_width, plot_height, fade_polarity):
    """Set the dragged phase's controller from the drag distance since the press"""
    dx = dx_px / max(1, plot_width // max(1, n_phases))
    dy = dy_px / max(1, int(0.95 * plot_height))
    match zctrl.envelope:
        case "release":
            dval = -zctrl.value_range * dx
        case "sustain":
            dval = -zctrl.value_range * dy
        case "fade":
            dval = -fade_polarity * zctrl.value_range * dy
        case _:
            dval = zctrl.value_range * dx
    zctrl.set_value(click_value + dval)


# Filter (zynthian_widget_filter)

FILTER_DB_MIN = -32
FILTER_DB_MAX = 16
FILTER_DB_TICKS = [16, 8, 0, -8, -16, -24, -32]


def filter_zctrls(group_zctrls):
    """(cutoff, resonance) controllers of a controller group, None if missing"""
    cutoff = resonance = None
    for zctrl in group_zctrls:
        f = getattr(zctrl, "filter", None)
        if f == "cutoffFrequency":
            cutoff = zctrl
        elif f == "resonance":
            resonance = zctrl
    return cutoff, resonance


def filter_values(cutoff, resonance):
    """Cutoff and resonance normalized to 0..1"""
    norm_cutoff = (cutoff.value - cutoff.value_min) / cutoff.value_range if cutoff else 0.5
    norm_res = (resonance.value - resonance.value_min) / resonance.value_range if resonance else 0.0
    return norm_cutoff, norm_res


def filter_db_y(db, m_t, gh):
    return m_t + gh * (1.0 - (db - FILTER_DB_MIN) / (FILTER_DB_MAX - FILTER_DB_MIN))


def filter_curve(norm_cutoff, norm_res, width, height, m_l, m_r, m_t, m_b):
    """Polygon coords of the filter response (a low pass with a resonance peak, 20 Hz..20 kHz
    on a log scale, FILTER_DB_MIN..FILTER_DB_MAX), one point per horizontal pixel; None if too
    small"""
    db_range = FILTER_DB_MAX - FILTER_DB_MIN
    maxy = height - m_b
    gw = width - m_l - m_r
    gh = maxy - m_t
    if gw < 10:
        return None
    closed = False
    coords = [m_l, maxy]
    display_cutoff = 20.0 * (20000.0 / 20.0) ** norm_cutoff
    for px_offset in range(int(gw) + 1):
        freq = 20.0 * (20000.0 / 20.0) ** (px_offset / gw)
        f_ratio = freq / max(1.0, display_cutoff)
        resp = 1.0 / math.sqrt(1.0 + math.pow(f_ratio, 8))
        db_val = 20.0 * math.log10(resp + 1e-10)  # Base is ~ -3dB at cutoff
        if norm_res > 0:
            peak = math.exp(-pow(math.log(f_ratio + 1e-10), 2) / 0.05)
            db_val += norm_res * 12.0 * peak
        coords.append(m_l + px_offset)
        py = m_t + int(gh * (1.0 - (db_val - FILTER_DB_MIN) / db_range))
        if py < maxy:
            coords.append(max(m_t, py))
        else:
            coords.append(max(m_t, maxy))
            closed = True
            break
    if not closed:
        # Close polygon when the slope crosses 0 beyond the display area
        coords += [width - m_r, maxy]
    return coords


def filter_drag(cutoff, resonance, click_cutoff, click_res, dx_rel, dy_rel):
    """XY pad: x cutoff, y resonance (up increases), relative to the values at the press;
    dx_rel, dy_rel: drag distance as fractions of the widget size"""
    if cutoff:
        x = max(0.0, min(1.0, click_cutoff + dx_rel))
        cutoff.set_value(cutoff.value_min + x * cutoff.value_range)
    if resonance:
        y = max(0.0, min(1.0, click_res - dy_rel))
        resonance.set_value(resonance.value_min + y * resonance.value_range)
