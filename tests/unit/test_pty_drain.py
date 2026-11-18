"""zyngine.zynthian_pty_drain: the output of engines started on a pty is read continuously.

A process writing to a pty nobody reads blocks when the pty's buffer is full (about 20 KB): on a
Galaxy S III Neo ZynAddSubFX's JACK notification thread blocked printing "Jack reports xrun", and
with it the JACK server and every snapshot change."""

import logging
import sys
import time

import pexpect

import zyngine.zynthian_engine  # noqa: F401 (the module, see engine_module())
from zyngine.zynthian_pty_drain import pty_drain

PY = sys.executable
LINES = 5000  # "Jack reports xrun NNNN\n" x 5000: about 115 KB, 5x a pty's buffer


def engine_module():
    """zyngine/__init__ star-imports the engine classes, so go via sys.modules"""
    return sys.modules["zyngine.zynthian_engine"]


def make_engine(tmp_path, script, prompt="READY"):
    path = tmp_path / "engine.py"
    path.write_text(script)
    eng = engine_module().zynthian_basic_engine("test", f"{PY} -u {path}", prompt=prompt)
    eng.proc_timeout = 5
    return eng


def wait_for(cond, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cond():
            return True
        time.sleep(0.02)
    return cond()


def all_lines_read(eng):
    # The lines expect() read past the prompt stay in pexpect's buffer, the drain reads the rest
    return lambda: eng.proc.zyn_drain.lines + eng.proc.buffer.count(b"\n") >= LINES


def flood_script(done_path):
    # Prints far more than a pty holds after its prompt, then marks that it got through
    return ("import time\n"
            "print(\"READY\")\n"
            f"for i in range({LINES}): print(\"Jack reports xrun %d\" % i)\n"
            f"open(\"{done_path}\", \"w\").close()\n"
            "time.sleep(30)\n")


def test_output_beyond_the_pty_buffer_without_a_command_does_not_block_the_engine(tmp_path):
    done = tmp_path / "done"
    eng = make_engine(tmp_path, flood_script(done))
    eng.start()
    try:
        assert wait_for(done.exists), "the engine blocked writing to its pty"
        assert wait_for(all_lines_read(eng))
    finally:
        eng.stop()


def test_without_the_drain_the_engine_blocks(tmp_path):
    # The bug, to show the test above tests something: a pexpect process whose pty isn't read
    done = tmp_path / "done"
    proc = pexpect.spawn(PY, ["-u", "-c", flood_script(done)])
    proc.expect("READY")
    try:
        assert not wait_for(done.exists, timeout=1.5)
    finally:
        proc.close(force=True)


# An interactive engine (like fluidsynth/sfizz): answers "echo X" with "X" and its prompt, while a
# thread prints noise all the time (like xrun messages)
INTERACTIVE = (
    "import sys, threading, time\n"
    "def noise():\n"
    "    i = 0\n"
    "    while True:\n"
    "        sys.stdout.write(\"Jack reports xrun %d\\n\" % i); sys.stdout.flush(); i += 1\n"
    "        if i % 100 == 0: time.sleep(0.01)\n"
    "threading.Thread(target=noise, daemon=True).start()\n"
    "sys.stdout.write(\"READY\\n> \"); sys.stdout.flush()\n"
    "for line in sys.stdin:\n"
    "    cmd = line.split()\n"
    "    if cmd and cmd[0] == \"echo\": sys.stdout.write(\"answer=%s\\n\" % cmd[1])\n"
    "    if cmd and cmd[0] == \"quit\": sys.stdout.write(\"cheers!\\n\"); sys.stdout.flush(); break\n"
    "    sys.stdout.write(\"> \"); sys.stdout.flush()\n"
)


def test_proc_cmd_gets_its_response_while_the_drain_reads_the_rest(tmp_path):
    eng = make_engine(tmp_path, INTERACTIVE, prompt="\n> ")
    eng.start()
    try:
        drain = eng.proc.zyn_drain
        # Between commands the noise exceeds a pty's buffer many times over
        assert wait_for(lambda: drain.nbytes > 100000)
        for i in range(50):
            out = eng.proc_cmd(f"echo {i}")
            assert f"answer={i}" in out
            if i % 10 == 0:
                time.sleep(0.2)
        n = drain.nbytes
        assert wait_for(lambda: drain.nbytes > n), "the drain doesn't read after the commands"
    finally:
        eng.stop()


def test_a_response_isnt_taken_by_the_drain_under_owner(tmp_path):
    # As fluidsynth's stop: "quit", then expect "cheers!" (inside proc_io)
    eng = make_engine(tmp_path, INTERACTIVE, prompt="\n> ")
    eng.start()
    try:
        for _ in range(20):
            with eng.proc_io():
                eng.proc.sendline("echo x")
                eng.proc.expect("answer=x", timeout=2)
                eng.proc.expect("\n> ", timeout=2)
    finally:
        eng.stop()


def test_stop_ends_the_thread_and_the_process(tmp_path):
    eng = make_engine(tmp_path, INTERACTIVE, prompt="\n> ")
    eng.start()
    proc = eng.proc
    drain = proc.zyn_drain
    t = time.monotonic()
    eng.stop()
    assert time.monotonic() - t < 1.0
    assert not drain.is_alive()
    assert eng.proc is None
    assert not proc.isalive()
    assert proc.closed
    assert drain._wake_r == drain._wake_w == -1  # its wake-up pipe is closed


def test_a_stop_with_the_engine_flooding_its_pty_is_quick(tmp_path):
    eng = make_engine(tmp_path, flood_script(tmp_path / "done"))
    eng.start()
    drain = eng.proc.zyn_drain
    t = time.monotonic()
    eng.stop()
    assert time.monotonic() - t < 1.0
    assert not drain.is_alive()


def test_the_thread_ends_with_the_process(tmp_path, caplog):
    eng = make_engine(tmp_path, "import time; print(\"READY\"); time.sleep(0.2)")
    eng.start()
    drain = eng.proc.zyn_drain
    with caplog.at_level(logging.WARNING):
        assert wait_for(lambda: not drain.is_alive(), timeout=3)
    assert any("closed its output" in r.getMessage() for r in caplog.records)
    eng.stop()  # still reaps and closes it


def test_an_expected_end_isnt_logged_as_unexpected(tmp_path, caplog):
    eng = make_engine(tmp_path, INTERACTIVE, prompt="\n> ")
    eng.start()
    drain = eng.proc.zyn_drain
    with caplog.at_level(logging.WARNING):
        eng.proc_exit = True
        eng.proc.sendline("quit")
        assert wait_for(lambda: not drain.is_alive(), timeout=3)
        eng.stop()
    assert not any("closed its output" in r.getMessage() for r in caplog.records)


def test_end_process_stops_the_drain_of_a_plain_pexpect_process():
    proc = pexpect.spawn(PY, ["-u", "-c", "print(\"READY\"); import time; time.sleep(30)"])
    proc.expect("READY")
    drain = pty_drain(proc, "plain")
    assert engine_module().end_process(proc, "plain", grace=0, timeout=2.0)
    assert not drain.is_alive()
    assert proc.zyn_drain is None


def test_logging_is_rate_limited(tmp_path, caplog):
    done = tmp_path / "done"
    with caplog.at_level(logging.DEBUG):
        eng = make_engine(tmp_path, flood_script(done))
        eng.start()
        try:
            assert wait_for(all_lines_read(eng))
        finally:
            eng.stop()
    logged = [r for r in caplog.records if r.getMessage().startswith("test > ")]
    # a few one-second windows of LOG_LINES_PER_S lines and a summary each
    assert 0 < len(logged) < 10 * (pty_drain.LOG_LINES_PER_S + 1)
    assert any("more lines not logged" in r.getMessage() for r in logged)
