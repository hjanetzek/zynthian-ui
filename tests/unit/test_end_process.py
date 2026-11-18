"""zyngine.zynthian_engine.end_process: bounded stops of engine processes."""

import sys
import time

import pexpect

import zyngine.zynthian_engine  # noqa: F401 (the module, see module())


def module():
    """zyngine/__init__ star-imports the engine classes, so go via sys.modules"""
    return sys.modules["zyngine.zynthian_engine"]


def test_without_signals_a_process_ignoring_them_is_killed_after_the_grace():
    # like sfizz_jack: signals don't end it
    proc = pexpect.spawn("sh", ["-c", "trap '' HUP INT TERM; echo ready; sleep 30"])
    proc.expect("ready")
    t = time.monotonic()
    assert module().end_process(proc, "test", grace=0.2, signals=False) is False
    assert time.monotonic() - t < 1.0
    assert not proc.isalive()


def test_without_signals_a_process_ending_in_the_grace_is_not_killed():
    proc = pexpect.spawn("sh", ["-c", "echo ready; sleep 0.1"])
    proc.expect("ready")
    assert module().end_process(proc, "test", grace=2.0, signals=False) is True
    assert not proc.isalive()


def test_with_signals_a_process_is_terminated():
    proc = pexpect.spawn("sh", ["-c", "echo ready; sleep 30"])
    proc.expect("ready")
    t = time.monotonic()
    assert module().end_process(proc, "test", grace=0, timeout=2.0) is True
    assert time.monotonic() - t < 2.0
    assert not proc.isalive()


def test_a_process_ignoring_sighup_ends_quickly():
    # like Pure Data: SIGHUP ignored, SIGINT ends it
    proc = pexpect.spawn("sh", ["-c", "trap '' HUP; echo ready; sleep 30"])
    proc.expect("ready")
    t = time.monotonic()
    assert module().end_process(proc, "test", grace=0, timeout=2.0) is True
    assert time.monotonic() - t < 0.2
