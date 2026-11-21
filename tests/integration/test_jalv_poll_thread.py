"""jalv's output thread (proc_poll_thread_task) after jalv has ended: it must neither spin nor stay.

Before strand 01's "the output thread stops when jalv ends", the thread kept reading the closed
pipe and used a whole CPU until the engine was stopped. These cases check the ways jalv's output
can end: a crash mid-line or mid-character, another process keeping the pipe open after jalv's
end, and the restart after a broken pipe (proc_cmd), which starts a second thread for the engine.
jalv is faked with real pipes (tests/integration/test_jalv_output_decoding.py's PipeJalv).
"""

import io
import os
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from tests.integration.test_jalv_output_decoding import PipeJalv, wait_for

pytestmark = pytest.mark.integration

START = b"Plugin:       urn:test:plugin\nJACK Name:    test\n>\n"


class EndingJalv(PipeJalv):
    """PipeJalv with its exit status set before its output closes, as a real process has it: the
    output thread reads the end of the output and then asks for the status (wait()); set after the
    close, the thread could see "still running" (seen once in the test VM)"""

    def end(self, code=-9):
        if self._wfd is not None:
            self.returncode = code
        super().end(code)


class BrokenPipeStdin(io.StringIO):
    """jalv's stdin: a broken pipe once jalv has ended"""

    def __init__(self, proc):
        super().__init__()
        self.proc = proc

    def writelines(self, lines):
        if self.proc.returncode is not None:
            raise BrokenPipeError(32, "Broken pipe")
        super().writelines(lines)


@pytest.fixture
def jalv_mod():
    # (zyngine's star imports shadow the module attribute with the class of the same name)
    import zyngine.zynthian_engine_jalv  # noqa: F401
    return sys.modules["zyngine.zynthian_engine_jalv"]


@pytest.fixture
def engine(monkeypatch, jalv_mod):
    """A jalv engine with just what start() and proc_cmd() need; ``engine.procs``: its fake jalvs"""
    procs = []

    def popen(command, **kwargs):
        proc = EndingJalv(START, kwargs)
        proc.stdin = BrokenPipeStdin(proc)
        procs.append(proc)
        return proc
    monkeypatch.setattr(jalv_mod, "Popen", popen)
    monkeypatch.setattr(jalv_mod.zynautoconnect, "request_audio_connect", lambda *a, **kw: None)
    monkeypatch.setattr(jalv_mod.zynautoconnect, "request_midi_connect", lambda *a, **kw: None)
    engine = jalv_mod.zynthian_engine_jalv_base.__new__(jalv_mod.zynthian_engine_jalv_base)
    engine.name = "Jalv/Test"
    engine.jackname = "test"
    engine.plugin_name = "Test"
    engine.plugin_url = "urn:test:plugin"
    engine.proc = None
    engine.proc_exit = False
    engine.proc_poll_thread = None
    engine.command = ["jalv", "-n", "test", "urn:test:plugin"]
    engine.command_env = {}
    engine.command_cwd = None
    engine.command_prompt = ">"
    engine.processors = [SimpleNamespace(preset_info=None)]
    engine.set_preset = lambda processor, preset_info: None
    engine.lines = []
    engine.proc_poll_parse_line = engine.lines.append
    engine.procs = procs
    yield engine
    engine.proc_exit = True
    for proc in procs:
        proc.end()


def start(engine):
    t = threading.Thread(target=engine.start, daemon=True)
    t.start()
    t.join(10)
    assert not t.is_alive(), "start() didn't return"
    assert engine.proc_poll_thread is not None and engine.proc_poll_thread.is_alive()
    return engine.proc_poll_thread


def cpu_percent(thread, seconds=0.5):
    """CPU use of a thread (percent of one core) over ``seconds``, from /proc/self/task/<tid>/stat"""
    def ticks():
        try:
            with open(f"/proc/self/task/{thread.native_id}/stat") as f:
                fields = f.read().rsplit(")", 1)[1].split()
        except FileNotFoundError:
            return None
        return int(fields[11]) + int(fields[12])
    t0 = ticks()
    time.sleep(seconds)
    t1 = ticks()
    if t0 is None or t1 is None:
        return 0.0
    return (t1 - t0) * 100 / os.sysconf("SC_CLK_TCK") / seconds


def poll_threads():
    return [t for t in threading.enumerate() if t.name == "proc_poll_test" and t.is_alive()]


def test_crash_mid_line(engine, caplog):
    thread = start(engine)
    proc = engine.proc
    proc.write(b"#CTR> 3#cutoff=0.5\n#CTR> 4#reso")
    proc.end(-11)  # SIGSEGV while writing a line
    thread.join(5)
    assert not thread.is_alive(), "the output thread keeps reading the closed pipe"
    assert engine.lines == ["#CTR> 3#cutoff=0.5", "#CTR> 4#reso"]
    assert "ended unexpectedly with: signal SIGSEGV" in caplog.text


def test_crash_mid_character(engine, caplog):
    thread = start(engine)
    engine.proc.write(b"LOG caf\xc3")  # the first byte of a 2-byte UTF-8 character
    engine.proc.end(-9)
    thread.join(5)
    assert not thread.is_alive()
    assert engine.lines == ["LOG caf�"]
    assert "ended unexpectedly with: signal SIGKILL" in caplog.text


def test_pipe_kept_open_by_another_process(engine, caplog):
    """A process that inherited jalv's stdout keeps the pipe open: the thread waits without CPU use"""
    thread = start(engine)
    proc = engine.proc
    other_writer = os.dup(proc._wfd)
    try:
        proc.end(-9)
        assert cpu_percent(thread) < 20, "the output thread spins while the pipe stays open"
        assert thread.is_alive()
        os.write(other_writer, b"LOG from the other process\n")
        assert wait_for(lambda: "LOG from the other process" in engine.lines)
    finally:
        os.close(other_writer)
    thread.join(5)
    assert not thread.is_alive()
    assert "ended unexpectedly with: signal SIGKILL" in caplog.text


def test_restart_after_broken_pipe_leaves_one_output_thread(engine, caplog):
    old_thread = start(engine)
    old_proc = engine.proc
    old_proc.end(-9)  # jalv killed (OOM): the next command finds a broken pipe and restarts it
    engine.proc_cmd("set 1 0.5")
    assert engine.proc is not old_proc and len(engine.procs) == 2
    old_thread.join(5)
    assert not old_thread.is_alive(), "the old output thread survived the restart"
    new_thread = engine.proc_poll_thread
    assert new_thread is not old_thread and new_thread.is_alive()
    assert poll_threads() == [new_thread]
    engine.proc.write(b"LOG new jalv\n")
    assert wait_for(lambda: "LOG new jalv" in engine.lines)
    assert cpu_percent(new_thread) < 20
    # The old jalv's end is logged once (proc_cmd or its output thread, whichever sees it first)
    assert caplog.text.count("signal SIGKILL") == 1
