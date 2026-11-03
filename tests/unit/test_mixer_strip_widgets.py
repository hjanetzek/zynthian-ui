"""Tk mixer strips built without audio mixer widgets (zynthian_gui_mixer_strip.has_mixer_widgets).

A strip built while its chain had no mixer processor yet (e.g. while a snapshot loads) has no
fader, balance, toggle, mute or DPM items; the draw methods must skip them until the strip is
rebuilt. Upstream since 6a149c4a sets fader_overlay = None before building those widgets, which
made our hasattr() check always true (the draw methods then used items that don't exist)."""

from types import SimpleNamespace

import pytest

mixer = pytest.importorskip("zyngui.zynthian_gui_mixer")


class FailingCanvas:
    def __getattr__(self, name):
        raise AssertionError(f"canvas.{name} called on a strip without mixer widgets")


def strip_without_mixer_widgets():
    strip = object.__new__(mixer.zynthian_gui_mixer_strip)
    strip.fader_overlay = None     # as __init__ leaves it when the chain had no mixer processor
    strip.canvas = FailingCanvas()
    # The chain got its mixer processor after the strip was built
    ctrl = SimpleNamespace(value=0.5, name="solo")
    proc = SimpleNamespace(controllers_dict={"balance": ctrl, "level": ctrl, "mute": ctrl, "solo": ctrl},
                           eng_code="MI")
    strip.chain = SimpleNamespace(zynmixer_proc=proc, chain_id=1)
    return strip


def test_strip_without_mixer_widgets():
    assert not strip_without_mixer_widgets().has_mixer_widgets()


@pytest.mark.parametrize("method", ["draw_balance", "draw_level", "draw_toggle", "draw_mute", "get_dpm_script"])
def test_draw_methods_skip_missing_widgets(method):
    getattr(strip_without_mixer_widgets(), method)()


def test_strip_with_mixer_widgets():
    strip = object.__new__(mixer.zynthian_gui_mixer_strip)
    strip.fader_overlay = 42
    assert strip.has_mixer_widgets()
