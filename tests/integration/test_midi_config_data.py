"""MIDI configuration lists (zyngui.zynthian_midi_config_data.midi_config_list), shared by the Tk
screen (zynthian_gui_midi_config) and the Qt routing screens (zynqt.screens.routing).

The MIDI output routing list of a chain shows the other MIDI chains it can feed: those on one
channel and, as upstream's Tk screen does, those on all channels (midi_chan 0xffff). The shared
module once left the all-channel chains out."""

from types import SimpleNamespace

import pytest

mcd = pytest.importorskip("zyngui.zynthian_midi_config_data")


def fake_chain(chain_id, midi_chan, name, midi=True, midi_out=()):
    return SimpleNamespace(chain_id=chain_id, midi_chan=midi_chan, midi_out=list(midi_out), midi_in=[],
                           is_midi=lambda: midi, get_name=lambda: name)


@pytest.fixture
def sm():
    chains = {
        1: fake_chain(1, 0, "Source", midi_out=[3]),
        2: fake_chain(2, 1, "Channel 2"),
        3: fake_chain(3, 0xffff, "Omni"),
        4: fake_chain(4, None, "Audio only", midi=False),
    }
    cm = SimpleNamespace(chains=chains, get_chain=chains.get, active_chain=chains[1],
                         will_midi_howl=lambda src, dst: False)
    return SimpleNamespace(chain_manager=cm, ctrldev_manager=SimpleNamespace(drivers={}))


def chain_rows(rows):
    i = [r[2] for r in rows].index("> CHAINS")
    return [(r[0], r[2]) for r in rows[i + 1:]]


def test_output_list_shows_all_channel_chains(fake_autoconnect, sm):
    rows = mcd.midi_config_list(sm, sm.chain_manager.chains[1], False)
    assert chain_rows(rows) == [(2, "☐ Channel 2"), (3, "☒ Omni")]


def test_output_list_without_other_midi_chains_has_no_chains_section(fake_autoconnect, sm):
    chains = sm.chain_manager.chains
    for cid in (2, 3):
        del chains[cid]
    rows = mcd.midi_config_list(sm, chains[1], False)
    assert "> CHAINS" not in [r[2] for r in rows]


# Upstream's audio to MIDI converter (e5ea8288, two outputs since 34b22105 / acee218e; aubionotes
# removed in 876d5e2d), ported into the shared module: each converter output is a MIDI input port
# like any other (no converter row, no toggle); routing an output to a chain gives its channel the
# first audio input (if it has none) and updates which outputs are analysed

A2M_ZMIPS = [3, 4]  # zmip of converter outputs 1 and 2


def a2m_sm(sm, fake_autoconnect):
    import zynautoconnect
    calls = []
    for name in ("netump", "rtpmidi", "qmidinet", "touchosc2midi", "bluetooth"):
        setattr(sm, f"start_{name}", lambda **kw: None)
        setattr(sm, f"stop_{name}", lambda **kw: None)
    sm.ctrldev_manager.request_identity = lambda idev: None
    sm.ctrldev_manager.is_input_device_available_to_chains = lambda idev: True
    sm.audio2midi_default_input = lambda output: calls.append(("default_input", output))
    sm.update_audio2midi_outputs = lambda: calls.append(("update_outputs",))
    for output, zmip in enumerate(A2M_ZMIPS):
        zynautoconnect.devices_in[zmip] = SimpleNamespace(aliases=[zynautoconnect.AUDIO2MIDI_UIDS[output],
                                                                   f"Audio ➔ MIDI {output + 1}"])
    fake_autoconnect.get_audio2midi_zmips.return_value = list(A2M_ZMIPS)
    fake_autoconnect.is_audio2midi_zmip.side_effect = lambda zmip: zmip in A2M_ZMIPS
    return calls


class FakeRouter:
    """lib_zyncore's zmop routes (zmop, zmip) -> bool"""

    def __init__(self):
        self.routes = {}

    def zmop_get_route_from(self, zmop, zmip):
        return self.routes.get((zmop, zmip), False)

    def zmop_set_route_from(self, zmop, zmip, route):
        self.routes[(zmop, zmip)] = bool(route)


@pytest.fixture
def no_services(monkeypatch):
    import zynconf
    monkeypatch.setattr(zynconf, "is_service_active", lambda service: False)


def test_device_list_shows_the_converter_outputs_as_ports(fake_autoconnect, no_services, sm):
    import zynautoconnect
    a2m_sm(sm, fake_autoconnect)
    rows = mcd.midi_config_list(sm, None, True)
    a2m = [(r[0], r[1]) for r in rows if r[0] in zynautoconnect.AUDIO2MIDI_UIDS]
    assert a2m == [(zynautoconnect.AUDIO2MIDI_UIDS[0], 3), (zynautoconnect.AUDIO2MIDI_UIDS[1], 4)]
    titles = [r[2] for r in rows if r[0] in zynautoconnect.AUDIO2MIDI_UIDS]
    assert [t.endswith(f"Audio ➔ MIDI {n}") for n, t in enumerate(titles, 1)] == [True, True]  # (mode icons first)
    # No converter toggle row any more; aubionotes is gone (upstream 876d5e2d)
    assert not [r for r in rows if r[0] == "audio2midi"]
    assert not [r for r in rows if r[0] and "aubio" in str(r[0])]


def test_selecting_a_converter_output_in_the_device_list_shows_its_options(fake_autoconnect, sm):
    import zynautoconnect
    a2m_sm(sm, fake_autoconnect)
    row = (zynautoconnect.AUDIO2MIDI_UIDS[1], 4, "Audio ➔ MIDI 2")
    assert mcd.midi_config_action(sm, None, True, row) == "options"


def test_routing_a_converter_output_to_a_chain_gives_its_channel_an_input(fake_autoconnect, sm, monkeypatch):
    import zynautoconnect
    calls = a2m_sm(sm, fake_autoconnect)
    router = FakeRouter()
    monkeypatch.setattr(mcd, "lib_zyncore", router)
    chain = SimpleNamespace(zmop_index=0, midi_chan=0)
    row = (zynautoconnect.AUDIO2MIDI_UIDS[1], 4, "☐ Audio ➔ MIDI 2")
    assert mcd.midi_config_action(sm, chain, True, row) is None
    assert router.routes[(0, 4)] is True
    assert calls == [("default_input", 1), ("update_outputs",)]
    # Unrouted: no input change, the outputs are updated (output 2 is no longer analysed)
    calls.clear()
    mcd.midi_config_action(sm, chain, True, row)
    assert router.routes[(0, 4)] is False
    assert calls == [("update_outputs",)]


def test_routing_another_device_leaves_the_converter_alone(fake_autoconnect, sm, monkeypatch):
    calls = a2m_sm(sm, fake_autoconnect)
    router = FakeRouter()
    monkeypatch.setattr(mcd, "lib_zyncore", router)
    chain = SimpleNamespace(zmop_index=0, midi_chan=0)
    mcd.midi_config_action(sm, chain, True, ("USB:keys", 1, "☐ Keys"))
    assert router.routes[(0, 1)] is True and calls == []
