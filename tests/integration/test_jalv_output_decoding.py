"""jalv's output isn't always valid UTF-8 (plugin messages, preset names saved in another encoding).

The engine read it with Popen(text=True) and strict decoding: one invalid byte raised
UnicodeDecodeError in readline(), which ended jalv's output thread (or failed the engine start, or
the plugin test). Nothing read jalv's output after that, so jalv blocked once the pipe was full.
jalv is faked here with a real pipe, decoded the way Popen does with the engine's arguments.
"""

import io
import locale
import os
import sys
import threading
import time

import pytest

pytestmark = pytest.mark.integration


class PipeJalv:
    """A Popen look-alike whose stdout is a real pipe, decoded as Popen(text=True, **kwargs) does"""

    def __init__(self, data, kwargs):
        rfd, self._wfd = os.pipe()
        encoding = kwargs.get("encoding") or locale.getpreferredencoding(False)
        self.stdout = io.TextIOWrapper(io.open(rfd, "rb", buffering=-1), encoding=encoding,
                                       errors=kwargs.get("errors"))
        self.stdin = io.StringIO()
        self.pid = 4242
        self.returncode = None
        self.write(data)

    def write(self, data):
        os.write(self._wfd, data)

    def end(self, code=-9):
        if self._wfd is not None:
            os.close(self._wfd)
            self._wfd = None
            self.returncode = code

    def poll(self):
        return self.returncode

    def kill(self):
        self.end()

    terminate = kill

    def wait(self, timeout=None):
        return self.returncode

    def communicate(self, input=None, timeout=None):
        self.end(0)
        return self.stdout.read(), None


def wait_for(cond, seconds=5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if cond():
            return True
        time.sleep(0.02)
    return False


@pytest.fixture
def jalv_mod():
    # (zyngine's star imports shadow the module attribute with the class of the same name)
    import zyngine.zynthian_engine_jalv  # noqa: F401
    return sys.modules["zyngine.zynthian_engine_jalv"]


@pytest.fixture
def engine(monkeypatch, jalv_mod):
    """A jalv engine with just what start() needs; ``engine.start_data``: jalv's output at start"""
    procs = []

    def popen(command, **kwargs):
        procs.append(PipeJalv(engine.start_data, kwargs))
        return procs[-1]
    monkeypatch.setattr(jalv_mod, "Popen", popen)
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
    engine.start_data = b"Plugin:       urn:test:plugin\n>\n"
    engine.lines = []
    engine.proc_poll_parse_line = engine.lines.append
    yield engine
    engine.proc_exit = True
    for proc in procs:
        proc.end()


def start(engine):
    result = {}
    t = threading.Thread(target=lambda: result.setdefault("output", engine.start()), daemon=True)
    t.start()
    t.join(10)
    assert not t.is_alive(), "start() didn't return"
    return result["output"]


def test_output_thread_keeps_reading_after_an_invalid_byte(engine):
    start(engine)
    thread = engine.proc_poll_thread
    assert thread is not None and thread.is_alive()
    # A preset name in Latin-1, then more output
    engine.proc.write(b"#PRS> urn:test:preset (Gr\xfcn)\nLOG still read\n")
    assert wait_for(lambda: "LOG still read" in engine.lines), \
        f"the output thread stopped at the invalid byte (alive: {thread.is_alive()}, read: {engine.lines})"
    assert thread.is_alive()
    assert engine.lines[0] == "#PRS> urn:test:preset (Gr�n)"


def test_start_succeeds_with_an_invalid_byte_before_the_prompt(engine):
    engine.start_data = b"Plugin:       urn:test:plugin\nwarning: caf\xe9\n>\n"
    output = start(engine)
    assert output is not None and "warning: caf�" in output
    assert engine.proc_poll_thread is not None and engine.proc_poll_thread.is_alive()


def test_lv2_plugin_test_passes_with_an_invalid_byte_in_the_output(monkeypatch):
    import zyngine.zynthian_lv2  # noqa: F401
    lv2 = sys.modules["zyngine.zynthian_lv2"]
    monkeypatch.setattr(lv2, "Popen", lambda command, **kwargs: PipeJalv(
        b"Plugin:       urn:test:plugin\nwarning: caf\xe9\n>\n", kwargs))
    assert lv2.test_lv2_plugin({"NAME": "Test", "URL": "urn:test:plugin"}) is True
