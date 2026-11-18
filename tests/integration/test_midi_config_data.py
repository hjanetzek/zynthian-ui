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
