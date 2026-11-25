"""zynautoconnect.route_zynseq_record_inputs(): which MIDI inputs reach zynseq's record input
(zmop_step = ZynMidiRouter:step_out => zynseq:input)."""

from types import SimpleNamespace

import pytest

from zynautoconnect import zynthian_autoconnect as zac
from zyngine.zynthian_chain_manager import ZMIP_UI_INDEX

ZMOP_STEP = 17


def port(alias):
    return SimpleNamespace(aliases=[alias])


@pytest.fixture
def routes(zyncore, monkeypatch):
    monkeypatch.setattr(zac, "lib_zyncore", zyncore)
    monkeypatch.setattr(zac, "state_manager", SimpleNamespace(
        get_zmop_step_index=lambda: ZMOP_STEP, get_zmip_ui_index=lambda: ZMIP_UI_INDEX))
    monkeypatch.setattr(zac, "max_num_devs", 4)
    monkeypatch.setattr(zac, "devices_in", [port("Keys"), None, port("Pads"), None])
    monkeypatch.setattr(zac, "zynseq_input_exclude_ports", ["Pads"])

    def run():
        zyncore.reset_fake()
        zac.route_zynseq_record_inputs()
        return zyncore.calls_to("zmop_set_route_from")
    return run


def test_devices_are_routed_unless_excluded(routes):
    calls = routes()
    assert (ZMOP_STEP, 0, 1) in calls
    assert (ZMOP_STEP, 2, 0) in calls
    assert not [c for c in calls if c[1] in (1, 3)]


def test_notes_played_through_the_ui_zmip_are_recorded(routes):
    """ctrldev drivers that unroute their device and play the notes with ui_send_note_on (e.g.
    DrivenByMoss) and the websocket keyboard: ZMIP_FAKE_UI, routed by init_zyncore to the chain
    zmops only."""
    assert ZMIP_UI_INDEX == 28  # ZMIP_FAKE_UI in zynmidirouter.h
    assert (ZMOP_STEP, ZMIP_UI_INDEX, 1) in routes()
