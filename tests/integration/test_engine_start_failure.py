"""An engine that fails to start: the processor add fails cleanly and zynthian doesn't stay busy.

A jalv that exits at start (e.g. a plugin binary for another architecture: "Failed to instantiate
plugin") used to leave the engine reading the closed pipe forever, so the chain add or snapshot
load never ended and the UI stayed busy until restarted. jalv is faked here with real pipes (no
process is started): it writes its start output and then either exits, hangs or shows its prompt.
"""

import io
import os
import sys
import threading
import time

import pytest

pytestmark = pytest.mark.integration

JALV_START = ["Plugin:       urn:test:broken", "JACK Name:    broken", "Sample rate:  48000 Hz"]
JALV_FAIL = ["lilv_lib_open(): error: Failed to open library broken.so (wrong ELF class)",
             "error: Failed to instantiate plugin"]


class FakeJalv:
    """A Popen look-alike whose stdout is a real pipe.

    mode "exit": writes ``lines`` and exits with ``exit_code`` (end of output)
    mode "hang": writes ``lines`` and blocks until killed
    mode "prompt": writes ``lines`` and the prompt, then runs until killed
    """

    instances = []

    def __init__(self, lines, mode="exit", exit_code=1):
        rfd, self._wfd = os.pipe()
        self.stdout = io.TextIOWrapper(io.FileIO(rfd, "r"), encoding="utf-8")
        self.stdin = io.StringIO()
        self.pid = 4242
        self.returncode = None  # as Popen: set by poll(), wait() and communicate()
        self._exit_code = None
        self.killed = False
        self.reaped = False
        self._lock = threading.Lock()
        out = "".join(line + "\n" for line in lines)
        if mode == "prompt":
            out += ">\n"
        os.write(self._wfd, out.encode())
        if mode == "exit":
            self._end(exit_code)
        FakeJalv.instances.append(self)

    def _end(self, code):
        with self._lock:
            if self._wfd is not None:
                os.close(self._wfd)
                self._wfd = None
                self._exit_code = code

    def poll(self):
        self.returncode = self._exit_code
        return self.returncode

    def kill(self):
        if self._exit_code is None:
            self.killed = True
            self._end(-9)

    terminate = kill

    def wait(self, timeout=None):
        self.reaped = True
        return self.poll()

    def communicate(self, input=None, timeout=None):
        out = self.stdout.read()
        self.wait()
        return out, None


@pytest.fixture
def jalv_mod():
    # (zyngine's star imports shadow the module attribute with the class of the same name)
    import zyngine.zynthian_engine_jalv  # noqa: F401
    FakeJalv.instances = []
    return sys.modules["zyngine.zynthian_engine_jalv"]


@pytest.fixture
def fake_popen(monkeypatch, jalv_mod):
    """Make jalv engines start ``FakeJalv``s: set ``fake_popen.lines`` / ``.mode`` before starting."""
    class Factory:
        lines = JALV_START + JALV_FAIL
        mode = "exit"
        commands = []

        def __call__(self, command, **kwargs):
            self.commands.append(command)
            return FakeJalv(self.lines, self.mode)
    factory = Factory()
    monkeypatch.setattr(jalv_mod, "Popen", factory)
    return factory


def bare_engine(jalv_mod):
    """A jalv engine with just what start() needs (no LV2 world, no state manager)"""
    engine = jalv_mod.zynthian_engine_jalv.__new__(jalv_mod.zynthian_engine_jalv)
    engine.name = "Jalv/Broken"
    engine.jackname = "broken"
    engine.plugin_name = "Broken"
    engine.plugin_url = "urn:test:broken"
    engine.proc = None
    engine.proc_exit = False
    engine.proc_poll_thread = None
    engine.command = ["jalv", "-n", "broken", "urn:test:broken"]
    engine.command_env = {}
    engine.command_cwd = None
    engine.command_prompt = ">"
    return engine


def run_with_deadline(fn, seconds=10):
    """Run fn in a thread; fail (instead of hanging the suite) if it doesn't return in time"""
    result = {}

    def target():
        result["value"] = fn()
    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(seconds)
    assert not t.is_alive(), f"didn't return in {seconds} s: waits forever for a dead jalv"
    return result.get("value")


# --- jalv engine start ---------------------------------------------------------------------------------------
def test_start_returns_when_jalv_exits_at_start(jalv_mod, fake_popen, caplog):
    engine = bare_engine(jalv_mod)
    assert run_with_deadline(engine.start) is None
    assert engine.proc is None
    assert engine.proc_poll_thread is None
    proc = FakeJalv.instances[0]
    assert proc.reaped
    assert "Failed to instantiate plugin" in caplog.text
    assert "exit code 1" in caplog.text


def test_start_kills_a_jalv_that_never_shows_its_prompt(jalv_mod, fake_popen, monkeypatch, caplog):
    fake_popen.mode = "hang"
    monkeypatch.setattr(jalv_mod.zynthian_engine_jalv_base, "proc_start_timeout", 0.3)
    engine = bare_engine(jalv_mod)
    t0 = time.monotonic()
    assert run_with_deadline(engine.start) is None
    assert time.monotonic() - t0 < 5
    proc = FakeJalv.instances[0]
    assert proc.killed and proc.reaped
    assert engine.proc is None
    assert "didn't start in 0.3 s" in caplog.text


def test_start_succeeds_when_jalv_shows_its_prompt(jalv_mod, fake_popen):
    fake_popen.lines = JALV_START
    fake_popen.mode = "prompt"
    engine = bare_engine(jalv_mod)
    output = run_with_deadline(engine.start)
    try:
        assert "JACK Name:" in output
        assert engine.proc is FakeJalv.instances[0]
        assert not engine.proc.killed
    finally:
        engine.proc_exit = True
        FakeJalv.instances[0].kill()


# --- chain manager -------------------------------------------------------------------------------------------
@pytest.fixture
def cm(state_manager, monkeypatch, jalv_mod, fake_popen):
    cm = state_manager.chain_manager
    for chain_id in [c for c in list(cm.chains) if c != 0]:
        cm.remove_chain(chain_id)
    # A jalv plugin whose jalv exits at start (the real engine class, LV2 lookups stubbed)
    monkeypatch.setitem(cm.engine_info, "JV/Broken", {
        "NAME": "Broken", "TITLE": "Broken", "TYPE": "MIDI Synth", "CAT": "Synth", "URL": "urn:test:broken",
        "UI": False, "ENGINE": jalv_mod.zynthian_engine_jalv, "ENABLED": True, "INDEX": 99,
        "DESCR": "", "QUALITY": 0, "COMPLEX": 0, "EDIT": 0, "ID": "99"})
    monkeypatch.setattr(jalv_mod.zynthian_engine_jalv, "get_lv2_controllers_dict", lambda self: {})
    monkeypatch.setattr(jalv_mod.zynthian_engine_jalv, "generate_ctrl_screens", lambda self, d: None)
    monkeypatch.setattr(jalv_mod.zynthian_engine_jalv, "get_custom_gui_fpath", lambda self: None)
    monkeypatch.setattr(jalv_mod.zynthian_lv2, "check_lv2_changes", lambda: None)
    # The error message stays on screen for 2 s: not needed here
    monkeypatch.setattr(sys.modules["zyngine.zynthian_chain_manager"], "sleep", lambda s: None)
    return cm


def test_add_processor_fails_cleanly_when_jalv_exits_at_start(cm, fake_popen):
    sm = cm.state_manager
    errors = []
    real_set_busy_error = sm.set_busy_error
    sm.set_busy_error = lambda msg, details=None: (errors.append(msg), real_set_busy_error(msg, details))
    try:
        assert cm.add_chain(1, midi_chan=0) == 1
        processor = run_with_deadline(lambda: cm.add_processor(1, "JV/Broken"))
    finally:
        del sm.set_busy_error
    assert processor is None
    assert fake_popen.commands, "jalv wasn't started"
    assert not sm.is_busy(), f"still busy: {sm.busy}"
    chain = cm.get_chain(1)
    assert chain.get_processors() == []
    assert all(p.eng_code != "JV/Broken" for p in cm.processors.values())
    assert not any(k.startswith("JV/") for k in cm.zyngines)
    assert errors == ["Can't start Broken"]
    assert all(p.reaped for p in FakeJalv.instances)


def test_any_engine_constructor_failure_ends_the_busy_state(cm, monkeypatch):
    class BrokenEngine:
        def __init__(self, *args):
            raise OSError("engine binary missing")
    info = dict(cm.engine_info["JV/Broken"], ENGINE=BrokenEngine, TYPE="Audio Effect")
    monkeypatch.setitem(cm.engine_info, "XB", info)
    assert cm.add_chain(1, midi_chan=0) == 1
    assert run_with_deadline(lambda: cm.add_processor(1, "XB")) is None
    assert not cm.state_manager.is_busy()
    assert cm.get_chain(1).get_processors() == []


def test_snapshot_load_continues_after_a_jalv_that_exits_at_start(cm):
    state = {
        1: {"midi_chan": 0, "slots": [{"1": "JV/Broken"}, {"2": "MI"}]},
        2: {"midi_chan": 1, "slots": [{"3": "MI"}]},
    }
    run_with_deadline(lambda: cm.set_state(state, {}))
    assert not cm.state_manager.is_busy(), f"still busy: {cm.state_manager.busy}"
    assert 1 not in cm.processors
    assert [p.eng_code for p in cm.get_chain(1).get_processors()] == ["MI"]
    assert [p.eng_code for p in cm.get_chain(2).get_processors()] == ["MI"]
