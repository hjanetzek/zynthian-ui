# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian Engine (zynthian_pty_drain)
#
# Continuous reading of the output of processes started on a pty (pexpect)
#
# ******************************************************************************
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

import os
import logging
from select import select
from time import monotonic
from contextlib import contextmanager, nullcontext
from threading import Thread, Condition, RLock, current_thread

# A process writing to a pty nobody reads blocks once the pty's buffer is full (about 20 KB on
# Linux). ZynAddSubFX prints "Jack reports xrun" from its JACK notification thread for every xrun:
# under an xrun storm that thread blocked in write(2), stopped reading its JACK notification
# socket, jackd's server thread blocked writing to it and no JACK request was answered any more
# (a snapshot change hung at "removing 1#Mixer Channel" and dead clients were never removed).
# So every process zynthian starts on a pty gets a pty_drain: a thread that reads its output
# whenever nobody else does, and steps aside while a command reads its response (owner()).


class pty_drain:
    """Read and discard the output of a pexpect process, logged (rate limited) at debug level.

    The thread reads the pty only while no one owns it: a command that waits for its response
    (pexpect's expect()) runs inside owner(), the thread doesn't touch the pty meanwhile and the
    response stays where expect() finds it. Output that arrives between commands is drained.
    The thread ends by itself when the process closes its output (it has ended), and stop()
    ends it at once (end_process() calls it before it closes the pty).
    """

    READ_SIZE = 65536
    LOG_LINES_PER_S = 10  # At most this many output lines logged per second, the rest counted
    MAX_PARTIAL = 1024  # Bytes kept of an unterminated line

    def __init__(self, proc, name, ending=None, log_level=logging.DEBUG):
        """proc : pexpect.spawn (child_fd: the pty master)
        name : for the log and the thread's name
        ending : callable returning True while the process is asked to end (its end of output
            isn't logged as unexpected then)
        """
        self.proc = proc
        self.name = name
        self.fd = proc.child_fd
        self.ending = ending
        self.log_level = log_level
        self.lines = 0  # Output lines read by the thread
        self.nbytes = 0  # Output bytes read by the thread
        self._partial = b""
        self._log_window = 0.0
        self._log_budget = 0
        self._log_suppressed = 0
        self._cond = Condition()
        self._owner_lock = RLock()  # Serializes commands (owners)
        self._owners = 0
        self._waiting = 0
        self._reading = False
        self._stopping = False
        self._wake_r, self._wake_w = os.pipe()
        self.thread = Thread(target=self._run, name=f"pty drain {name}", daemon=True)
        proc.zyn_drain = self
        self.thread.start()

    # -------------------------------------------------------------------------
    # API
    # -------------------------------------------------------------------------

    @contextmanager
    def owner(self):
        """Own the pty for a command and its response: the thread doesn't read meanwhile"""
        with self._owner_lock:
            with self._cond:
                self._waiting += 1
                while self._reading:
                    self._cond.wait()
                self._waiting -= 1
                self._owners += 1
            try:
                yield
            finally:
                with self._cond:
                    self._owners -= 1
                    self._cond.notify_all()

    def stop(self, timeout=1.0):
        """End the thread (before the pty is closed: its fd number could be reused)"""
        with self._cond:
            if self._stopping:
                return
            self._stopping = True
            self._cond.notify_all()
        try:
            os.write(self._wake_w, b"x")
        except OSError:
            pass
        if self.thread is not current_thread():
            self.thread.join(timeout)
            if self.thread.is_alive():
                logging.warning(f"Output reader of {self.name} didn't end in {timeout:.1f} s")
                return
        self._close_wake()
        if getattr(self.proc, "zyn_drain", None) is self:
            self.proc.zyn_drain = None

    def is_alive(self):
        return self.thread.is_alive()

    # -------------------------------------------------------------------------
    # Thread
    # -------------------------------------------------------------------------

    def _run(self):
        eof = False
        try:
            while not self._stopping:
                try:
                    r, _, _ = select([self.fd, self._wake_r], [], [])
                except (OSError, ValueError):
                    eof = True
                    break
                if self._stopping:
                    break
                if self.fd not in r:
                    continue
                with self._cond:
                    while (self._owners or self._waiting) and not self._stopping:
                        self._cond.wait()
                    if self._stopping:
                        break
                    self._reading = True
                data = None
                try:
                    # An owner may have read it meanwhile: don't block
                    if select([self.fd], [], [], 0)[0]:
                        data = os.read(self.fd, self.READ_SIZE)
                        if not data:
                            eof = True
                except OSError:
                    # EIO: the process has ended (the pty's other side is closed)
                    eof = True
                finally:
                    with self._cond:
                        self._reading = False
                        self._cond.notify_all()
                if eof:
                    break
                if data:
                    self._log(data)
        except Exception as e:
            logging.error(f"Output reader of {self.name} failed => {e}")
        finally:
            self._log_flush()
            if eof and not self._stopping and not (self.ending and self.ending()):
                logging.warning(f"Engine {self.name} (pid {self.proc.pid}) closed its output: it has ended?")

    def _log(self, data):
        self.nbytes += len(data)
        if not logging.getLogger().isEnabledFor(self.log_level):
            self.lines += data.count(b"\n")
            return
        lines = (self._partial + data).split(b"\n")
        self._partial = lines.pop()[-self.MAX_PARTIAL:]
        self.lines += len(lines)
        now = monotonic()
        if now - self._log_window >= 1.0:
            self._log_flush()
            self._log_window = now
            self._log_budget = self.LOG_LINES_PER_S
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if self._log_budget > 0:
                self._log_budget -= 1
                logging.log(self.log_level, f"{self.name} > {line.decode(errors='replace')}")
            else:
                self._log_suppressed += 1

    def _log_flush(self):
        if self._log_suppressed:
            logging.log(self.log_level, f"{self.name} > ... {self._log_suppressed} more lines not logged")
            self._log_suppressed = 0

    def _close_wake(self):
        for fd in (self._wake_r, self._wake_w):
            try:
                os.close(fd)
            except OSError:
                pass
        self._wake_r = self._wake_w = -1


def pty_owner(proc):
    """Context for reading a command's response from proc's pty: owner() of its drain, if any"""
    drain = getattr(proc, "zyn_drain", None)
    return drain.owner() if drain else nullcontext()


def stop_pty_drain(proc):
    """End proc's drain thread, if any (before its pty is closed)"""
    drain = getattr(proc, "zyn_drain", None)
    if drain:
        drain.stop()
