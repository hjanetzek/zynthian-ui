"""The Qt processor options' "Reload <processor>" (Tk: zynthian_gui_processor_options, upstream
6d8ca287, placed by d7d241aa): for LV2 (jalv, JV/) processors in a chain, between Replace and
Remove; chain_manager.reload_processor() runs in the background (the busy overlay draws), then the
new processor's control."""

from types import SimpleNamespace

import pytest

screen_mod = pytest.importorskip("zynqt.screens.processor_options")
ProcessorOptions = screen_mod.ProcessorOptions


def processor(eng_code="JV/http://example.org/fx", ptype="Audio Effect", chain=True):
    chain_obj = SimpleNamespace(chain_id=3, get_processor_count=lambda t: 1) if chain else None
    return SimpleNamespace(eng_code=eng_code, type=ptype, name="Reverb", chain=chain_obj, preset_list=[],
                           engine=SimpleNamespace(name="Reverb", get_options=lambda: {"replace": True}),
                           get_bank_list=lambda: [], is_bypassed=lambda: False,
                           get_basepath=lambda: "3#Reverb")


def titles(proc):
    entries = []
    screen = SimpleNamespace(processor=proc, last_random={}, set_title=lambda t: None,
                             set_entries=entries.extend)
    ProcessorOptions.fill(screen)
    return [e["title"] for e in entries]


def test_reload_is_offered_for_lv2_processors_between_replace_and_remove():
    t = titles(processor())
    assert t.index("Replace Reverb") + 1 == t.index("Reload Reverb") == t.index("Remove") - 1


def test_reload_is_offered_for_lv2_synths():
    t = titles(processor(ptype="MIDI Synth"))
    assert t.index("Replace Reverb") + 1 == t.index("Reload Reverb")
    assert t[t.index("Reload Reverb") + 1] == "Randomize parameters"


@pytest.mark.parametrize("proc", [processor(eng_code="SF"), processor(eng_code="MR"), processor(chain=False)])
def test_no_reload_for_other_engines_or_without_a_chain(proc):
    assert not any(t.startswith("Reload") for t in titles(proc))


class FakeUI:
    def __init__(self):
        self.calls = []
        self.background = None

    def run_background(self, task, done):
        self.background = (task, done)

    def purge_history(self, name):
        self.calls.append(("purge", name))

    def chain_control(self, chain_id=None, processor=None):
        self.calls.append(("chain_control", chain_id, processor))

    def set_current_processor(self, proc):
        self.calls.append(("current", proc))

    def show_info(self, text, ms=2500):
        self.calls.append(("info", text))


def reload_screen(result, removed=False):
    old = processor()
    ui = FakeUI()

    def reload_processor(p):
        assert p is old
        if removed:
            p.chain = None
        return result

    screen = SimpleNamespace(processor=old, ui=ui, chain_manager=SimpleNamespace(reload_processor=reload_processor))
    ProcessorOptions.reload(screen)
    task, done = ui.background
    assert ui.calls == []           # nothing until the background task is done
    done(task())
    return screen, ui, old


def test_reload_shows_the_new_processors_control(monkeypatch):
    connects = []
    monkeypatch.setattr(screen_mod.zynautoconnect, "request_audio_connect", lambda f: connects.append("audio"))
    monkeypatch.setattr(screen_mod.zynautoconnect, "request_midi_connect", lambda f: connects.append("midi"))
    new = object()
    screen, ui, old = reload_screen(new)
    assert screen.processor is new
    assert ui.calls == [("purge", "processor_options"), ("chain_control", 3, new)]
    assert connects == ["audio", "midi"]


def test_a_failed_reload_keeps_the_options():
    screen, ui, old = reload_screen(None)
    assert screen.processor is old
    assert ui.calls == [("info", "Can't reload Reverb")]


def test_a_failed_reload_that_removed_the_processor_leaves_its_options():
    screen, ui, old = reload_screen(None, removed=True)
    assert screen.processor is None
    assert ui.calls == [("info", "Can't reload Reverb"), ("current", None), ("purge", "processor_options"),
                        ("chain_control", 3, None)]
