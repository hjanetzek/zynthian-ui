"""Envelope widget geometry (zyngui.zynthian_widget_data.envelope_geometry), shared by the Tk
widget (zynthian_widget_envelope) and the Qt view (zynqt.models.widgets.EnvelopeView).

Upstream draws attack, decay and release as exponential curves since efb40f48 (riban,
2026-10-25: 16 steps, strength 1); the shared module once lost them and drew straight lines."""

import math
from types import SimpleNamespace

import pytest

wd = pytest.importorskip("zyngui.zynthian_widget_data")

W, H, ML, MB = 400, 200, 10, 10
N = 16                      # curve steps
NORM = 1.0 - math.exp(-1.0)


def zctrl(envelope, value, value_range=127, value_min=0):
    return SimpleNamespace(envelope=envelope, value=value, value_range=value_range, value_min=value_min)


def adsr(a=40, d=60, s=80, r=50):
    return [zctrl("attack", a), zctrl("decay", d), zctrl("sustain", s), zctrl("release", r)]


def points(coords):
    return [(coords[i], coords[i + 1]) for i in range(0, len(coords), 2)]


def flat(pts):
    """[(x, y), ...] -> [x, y, ...]: pytest.approx() takes no nested data (lists of points)"""
    return [c for p in pts for c in p]


def curve(p0, p1):
    """Upstream's curve from p0 to p1 without p0"""
    (x0, y0), (x1, y1) = p0, p1
    return [(x0 + (x1 - x0) * i / N, y0 + (y1 - y0) * (1.0 - math.exp(-i / N)) / NORM)
            for i in range(1, N)] + [(x1, y1)]


def geometry(zctrls, drag=None):
    zs, polarity = wd.envelope_zctrls(zctrls)
    return wd.envelope_geometry(zs, wd.envelope_values(zs), polarity, W, H, ML, MB, drag)


def test_adsr_polygon_is_upstreams_curves():
    zs = adsr()
    coords, click_ranges, _ = geometry(zs)
    pts = points(coords)
    dx = W // 4
    dy = int(0.95 * H)
    x0, y0 = ML, MB + H
    x_a = x0 + 40 / 127 * dx
    y_peak = y0 - dy
    x_d = x_a + 60 / 127 * dx
    y_s = y0 - 80 / 127 * dy
    x_r = ML + W - 50 / 127 * dx
    expected = ([(x0, y0)] + curve((x0, y0), (x_a, y_peak)) + curve((x_a, y_peak), (x_d, y_s))
                + [(x_d, y_s), (x_r, y_s)] + curve((x_r, y_s), (ML + W, y0)))
    # sustain level, then the release curve in place of the closing point
    assert len(pts) == 1 + 3 * N + 2
    for (x, y), (ex, ey) in zip(pts, expected):
        assert x == pytest.approx(ex) and y == pytest.approx(ey)
    assert click_ranges == pytest.approx([x_a, x_d, x_r, ML + W])


def test_curves_bend_like_upstream():
    """Attack rises fast, then flattens (exponential, not linear)"""
    coords, _, _ = geometry(adsr())
    pts = points(coords)
    (xs, ys), (xm, ym), (xe, ye) = pts[0], pts[N // 2], pts[N]
    linear_mid = ys + (ye - ys) * (xm - xs) / (xe - xs)
    assert ym < linear_mid - 5      # above the straight line (y grows downwards)


def test_short_phase_is_a_straight_line():
    """Phases narrower than 4 pixels or without a level change get no curve points (upstream)"""
    coords, _, _ = geometry(adsr(a=0, d=60, s=80, r=50))
    pts = points(coords)
    assert pts[1] == pytest.approx((ML, MB + H - int(0.95 * H)))   # attack: one point
    assert len(pts) == 1 + 1 + N + 2 + N


def test_drag_polygons_follow_the_curves():
    zs = adsr()
    coords, _, drag = geometry(zs, drag=zs[0])
    pts = points(coords)
    # attack: start, curve, down to the base line, back
    assert list(drag) == pytest.approx(flat([pts[0]] + pts[1:N + 1] + [(pts[N][0], MB + H), (ML, MB + H)]))
    _, _, drag = geometry(zs, drag=zs[3])
    assert flat(points(drag)[1:N + 1]) == pytest.approx(flat(pts[-N:]))
