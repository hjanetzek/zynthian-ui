"""BACK after adding a chain or a processor (ZynUI.modify_chain / chain_control), as the Tk UI
(zynthian_gui.modify_chain, checked in upstream's Tk UI 2026-11-21):

- a new chain starts a new history: BACK from its first screen (preset, bank, chain control) goes
  to the mixer, not back to the MIDI channel list;
- a processor added to (or replaced in) a chain keeps the history: BACK from chain control goes to
  the screen before chain control (it ends the history there), from bank/preset to the engine list."""

from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6.QtCore")
ui_mod = pytest.importorskip("zynqt.ui")

from tests.unit.test_qt_screen_signals import screen_ui  # noqa: E402

ZynUI = ui_mod.ZynUI


def proc(preset=""):
    return SimpleNamespace(eng_code="SY", chain=None, get_preset_name=lambda: preset,
                           get_bank_list=lambda: [], bank_list=[], preset_list=[])


def chain_ui(processor, status):
    ui = screen_ui()
    for n in ("add_chain", "engine", "midi_chan", "chain_options"):
        ui.list_screens[n] = SimpleNamespace(build=lambda: None, hide=lambda: None, mode=None)
    ui.list_screens["preset"].is_flat = lambda p: True
    ui.chain_control_screen.set_mode = lambda mode: None
    chain = SimpleNamespace(chain_id=3, current_processor=processor)
    ui.chain_manager = SimpleNamespace(active_chain=chain, get_chain=lambda cid: chain,
                                       set_active_chain_by_id=lambda cid: None)
    steps = iter([("midi_chan", None)] if "chain_id" not in status else [])

    def next_step():
        return next(steps, ("done", (3, processor)))

    ui.chain_edit = SimpleNamespace(status=dict(status), start=lambda s: None, next_step=next_step)
    for name in ("modify_chain", "chain_control", "close_screen", "set_current_processor"):
        setattr(ui, name, getattr(ZynUI, name).__get__(ui))
    return ui


def add_chain(processor):
    """mixer > add chain > engine > MIDI channel > the new chain"""
    ui = chain_ui(processor, {"type": "MIDI Synth", "engine": "SY"})
    ui.show_screen("add_chain")
    ui.show_screen("engine")
    ui.modify_chain()   # the engine chosen: the MIDI channel list
    assert ui.current_screen == "midi_chan"
    ui.modify_chain()   # the channel chosen: the chain is created
    return ui


@pytest.mark.parametrize("preset, first", [("", "preset"), ("Init", "chain_control")])
def test_back_from_a_new_chain_goes_to_the_mixer(preset, first):
    ui = add_chain(proc(preset))
    assert ui.current_screen == first
    assert ui.screen_history == []
    ui.close_screen()
    assert ui.current_screen == "mixer"


def add_processor(processor):
    """mixer > chain control > chain options > engine > the added processor"""
    ui = chain_ui(processor, {"chain_id": 3, "type": "Audio Effect", "engine": "SY"})
    for name in ("chain_control", "chain_options", "engine"):
        ui.show_screen(name)
    ui.modify_chain()
    return ui


def test_back_after_adding_a_processor_goes_to_the_screen_before_chain_control():
    ui = add_processor(proc("Default"))
    assert ui.current_screen == "chain_control"
    ui.close_screen()
    assert ui.current_screen == "mixer"


def test_back_from_the_added_processors_presets_goes_to_the_engines():
    ui = add_processor(proc())
    assert ui.current_screen == "preset"
    ui.close_screen()
    assert ui.current_screen == "engine"
