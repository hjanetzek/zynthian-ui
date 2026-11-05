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


# Plugin widgets (engine.custom_gui_fpath: zynthian_widget_<name>.py)

PLUGIN_WIDGETS = ("spectr30", "tunaone", "GxGraphicEQ", "nam", "aidax", "chord_analyzer", "tempo", "inet_radio",
                  "euclidseq", "organelle", "sooperlooper")


def plugin_widget(processor):
    """Name of a processor's plugin widget (zynthian_widget_<name>.py) if it has one of
    PLUGIN_WIDGETS, else None"""
    gui = getattr(processor.engine, "custom_gui_fpath", None) if processor else None
    if not gui:
        return None
    name = gui.rsplit("/", 1)[-1]
    if name.startswith("zynthian_widget_") and name.endswith(".py"):
        name = name[len("zynthian_widget_"):-3]
        return name if name in PLUGIN_WIDGETS else None
    return None


# 1/3 octave spectrum (x42 spectr30, zynthian_widget_spectr30)

SPECTRUM_FREQS = [25, 31, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800,
                  1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000]
SPECTRUM_LABELS = ["25", "31.5", "40", "50", "63", "80", "100", "125", "160", "200", "250", "315", "400", "500",
                   "630", "800", "1K", "1.25K", "1.6K", "2K", "2.5K", "3.15K", "4K", "5K", "6.3K", "8K", "10K",
                   "12.5K", "16K", "20K"]


def spectrum_levels(processor, monitors):
    """Per band (level, peak), as fractions of the height (scaled by the UIgain controller)"""
    try:
        scale = (12.0 + processor.controllers_dict['UIgain'].value) / 12.0
    except Exception:
        scale = 1.0
    levels = []
    for freq in SPECTRUM_FREQS:
        try:
            bar = scale * (100 + monitors[f"band{freq}"]) / 100
        except Exception:
            bar = 0.0
        try:
            tick = scale * (100 + monitors[f"max{freq}"]) / 100
        except Exception:
            tick = 0.0
        levels.append((bar, tick))
    return levels


# Guitarix graphic EQs (zynthian_widget_GxGraphicEQ): gains -30..+22 dB over the height

GX_EQ_BANDS = {
    "http://guitarix.sourceforge.net/plugins/gx_graphiceq_#_graphiceq_": (
        [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000, 20000],
        [">31Hz", "62Hz", "125Hz", "250Hz", "500Hz", "1KHz", "2KHz", "4KHz", "8KHz", "16KHz", "<20KHz"]),
    "http://guitarix.sourceforge.net/plugins/gx_barkgraphiceq_#_barkgraphiceq_": (
        [50, 150, 250, 350, 450, 570, 700, 840, 1000, 1170, 1370, 1600, 1850, 2150, 2500, 2900, 3400,
         4000, 4800, 5800, 7000, 8500, 10500, 13500],
        ["50Hz", "150Hz", "250Hz", "350Hz", "450Hz", "570Hz", "700Hz", "840Hz", "1K", "1.17K", "1.37K", "1.6K",
         "1.85K", "2.15K", "2.5K", "2.9K", "3.4K", "4K", "4.8K", "5.8K", "7K", "8.5K", "10.5K", "13.5K"]),
}
GX_ZERO = 30 / 52   # height fraction of the 0 dB line


def gx_eq_bands(processor):
    """(freqs, labels) of a Guitarix graphic EQ, or None"""
    return GX_EQ_BANDS.get(getattr(processor.engine, "plugin_url", None))


def gx_eq_levels(processor, monitors, n_bands):
    """Per band (bar bottom, bar top, gain tick), as height fractions from the bottom"""
    levels = []
    for i in range(n_bands):
        try:
            val = monitors[f"V{i + 1}"]
            if n_bands == 24:
                bar = (GX_ZERO, (30 + val) / 52)   # -40.0 <= val <= 4.0
            else:
                bar = (0.0, val)                   # 0 <= val <= 1.0
        except Exception:
            bar = (0.0, 0.0)
        try:
            tick = (30 + processor.controllers_dict[f"G{i + 1}"].value) / 52
        except Exception:
            tick = 0.0
        levels.append((bar[0], bar[1], tick))
    return levels


def gx_eq_drag(processor, band, height_fraction):
    """Set band's gain (0-based) from a touch at height_fraction (0 bottom, 1 top)"""
    try:
        zctrl = processor.controllers_dict[f"G{band + 1}"]
    except KeyError:
        return
    zctrl.set_value(int(52 * height_fraction) - 30)


# Tuner (x42 tuna, zynthian_widget_tunaone)

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def tuner_color(cent):
    try:
        acent = abs(cent)
        if acent > 25:
            cr, cg = 255, 0
        elif acent > 10:
            cr, cg = 255, int((25 - acent) * 255 / 15)
        else:
            cr, cg = int(acent * 255 / 40), 255
        return "#%02x%02x%02x" % (cr, cg, 0)
    except Exception:
        return "#00FF00"


def tuner_state(monitors):
    """(note name, cents, colour) while there is a signal, else None"""
    if 'freq_out' not in monitors or monitors.get('rms', -100) <= -50.0:
        return None
    try:
        note = f"{NOTE_NAMES[int(monitors['note'])]}{int(monitors['octave'])}"
    except Exception:
        note = "??"
    cent = monitors.get('cent', 0) or 0
    return note, cent, tuner_color(cent)


# Chord analyzer (dusk chord analyzer, zynthian_widget_chord_analyzer)

CHORD_ROOTS = ["-", "C", "C#/Db", "D", "D#/Eb", "E", "F", "F#/Gb", "G", "G#/Ab", "A", "A#/Bb", "B"]
CHORD_QUALITIES = ["-", "maj", "m", "dim", "aug", "7", "maj7", "m7", "mMaj7", "dim7", "m7b5", "aug7", "augMaj7",
                   "sus2", "sus4", "7sus4", "add9", "add11", "6", "m6", "maj9", "m9", "9", "maj11", "m11", "11",
                   "maj13", "m13", "13", "5", "7b5", "7#5", "7b9", "7#9"]
CHORD_INVERSIONS = ["-", "Root", "1st", "2nd", "3rd", "4th", "5th", "6th", "Slash"]


def chord_texts(monitors):
    """(chord text, bass text) of the detected chord, or None"""
    for prefix, root, quality, inversion, bass in (
            ("", "detected_root", "detected_quality", "detected_inversion", "detected_bass"),
            ("chord_analyzer_", "detectedRoot", "detectedQuality", "detectedInversion", "detectedBass"),
            ("chord_analyzer_midi_", "detectedRoot", "detectedQuality", "detectedInversion", "detectedBass")):
        if prefix + root in monitors:
            try:
                r, q = int(monitors[prefix + root]), int(monitors[prefix + quality])
                i, b = int(monitors[prefix + inversion]), int(monitors[prefix + bass])
                return (f"{CHORD_ROOTS[r]} {CHORD_QUALITIES[q]}   ({CHORD_INVERSIONS[i]})",
                        f"Bass {CHORD_ROOTS[b]}")
            except Exception:
                return None
    return None


# aidax (rt-neural loader, zynthian_widget_aidax): input/output meters falling by 10 % per refresh

def meter_fall(level, value):
    """New displayed level: jumps up to value, else falls 10 %"""
    if value >= level:
        return value
    return max(0.9 * level, 0) if level else level
