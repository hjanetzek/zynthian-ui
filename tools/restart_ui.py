"""Restart zynthian (RESTART_UI) on the device and check that it happened: run there by
sync_ui.sh -R (piped to "python3 - TIMEOUT" over ssh; only the standard library).

zynthian ignores OSC CUIAs while it is busy (snapshot loading, an engine starting, or stuck busy),
so the restart is checked, nothing is killed:
1. wait until zynthian is idle (the OSC query /STATUS/BUSY, zynthian_state_manager.osc_status_reply),
   showing what it is busy with, up to TIMEOUT seconds;
2. send /CUIA/RESTART_UI and wait until that process has ended (TIMEOUT);
3. wait for a new zynthian process (another PID, TIMEOUT) and until it answers idle: started up,
   UI shown, snapshot loaded (TIMEOUT).
A zynthian older than the query doesn't answer it: then RESTART_UI is sent without the busy
check (said so), the restart itself is still checked; a new process with older code (its
zynthian-ui directory has no osc_status_reply) counts as ready when it still runs 10 s later.

Exit codes: 0 restarted and ready, 2 still busy (RESTART_UI not sent), 3 no restart (the process
still runs), 4 no new process, 5 the new process isn't ready, 10 zynthian isn't running.
"""

import socket
import struct
import subprocess
import sys
import time

OSC_PORT = 1370  # zynconf.ServerPort["cuia_osc"]
# As common.sh's ZYN_PID: the newest match (under qmlpreview the UI is the child of a waiting parent)
PATTERN = r"^(/usr/bin/)?python3 [^ ]*zynthian_(qt_)?main.py"
NO_ANSWER_GRACE = 10  # seconds without an answer to the query before RESTART_UI is sent unchecked


def osc_string(s):
    b = s.encode() + b"\0"
    return b + b"\0" * (-len(b) % 4)


def osc_message(path):
    return osc_string(path) + osc_string(",")


def parse_osc(data):
    """(path, [args]) of an OSC message with int and string arguments"""
    def string(pos):
        end = data.index(b"\0", pos)
        return data[pos:end].decode(errors="replace"), (end + 4) & ~3

    path, pos = string(0)
    tags, pos = string(pos)
    args = []
    for t in tags[1:]:
        if t == "i":
            args.append(struct.unpack(">i", data[pos:pos + 4])[0])
            pos += 4
        elif t == "s":
            s, pos = string(pos)
            args.append(s)
        else:
            raise ValueError(f"OSC type {t}")
    return path, args


def zyn_pid():
    res = subprocess.run(["pgrep", "-n", "-f", PATTERN], stdout=subprocess.PIPE, text=True)
    return int(res.stdout.split()[0]) if res.returncode == 0 and res.stdout.strip() else None


def alive(pid):
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return False


def send(path):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(osc_message(path), ("127.0.0.1", OSC_PORT))


def query(timeout=1.0):
    """zynthian's busy state: dict(pid, busy, clients, message, details), or None without answer"""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        s.settimeout(timeout)
        s.sendto(osc_message("/STATUS/BUSY"), ("127.0.0.1", OSC_PORT))
        deadline = time.monotonic() + timeout
        while True:
            try:
                data = s.recv(4096)
            except OSError:
                return None
            try:
                path, args = parse_osc(data)
            except (ValueError, IndexError, struct.error):
                path, args = None, []
            if path == "/STATUS/BUSY" and len(args) >= 5:
                return dict(pid=args[0], busy=bool(args[1]), clients=args[2], message=args[3], details=args[4])
            if time.monotonic() >= deadline:
                return None


class Shown:
    """Prints a busy state when its clients change, or every 5 s (the snapshot progress changes all the time)"""

    def __init__(self):
        self.clients = None
        self.t = 0

    def __call__(self, st, text):
        if st["clients"] != self.clients or time.monotonic() - self.t >= 5:
            self.clients = st["clients"]
            self.t = time.monotonic()
            print(text, flush=True)


def answers_status(pid):
    """The process's code has the /STATUS/BUSY query: zynthian runs in its zynthian-ui directory"""
    try:
        with open(f"/proc/{pid}/cwd/zyngine/zynthian_state_manager.py") as f:
            return "def osc_status_reply" in f.read()
    except OSError:
        return True  # can't tell: ask


def describe(st):
    text = st["clients"] or "?"
    extra = " - ".join(x for x in (st["message"], st["details"]) if x)
    return f"{text} ({extra})" if extra else text


def fail(code, message):
    print(f"sync_ui: {message}", file=sys.stderr)
    sys.exit(code)


def main():
    timeout = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    t0 = time.monotonic()
    pid = zyn_pid()
    if pid is None:
        fail(10, "zynthian is not running")

    # 1. Idle?
    deadline = time.monotonic() + timeout
    show = Shown()
    checked = False
    while True:
        st = query()
        if st is not None:
            if not st["busy"]:
                checked = True
                break
            show(st, f"zynthian is busy: {describe(st)}, waiting (up to {timeout:.0f} s)")
        elif show.clients is None and time.monotonic() - t0 >= min(NO_ANSWER_GRACE, timeout):
            print(f"zynthian (PID {pid}) doesn't answer /STATUS/BUSY (older code, or its OSC server isn't up):"
                  " RESTART_UI sent without the busy check", flush=True)
            break
        if time.monotonic() >= deadline:
            if st is None:
                fail(2, f"zynthian doesn't answer /STATUS/BUSY any more after being busy with {show.clients}:"
                     " RESTART_UI not sent")
            fail(2, f"zynthian is still busy after {timeout:.0f} s: {describe(st)}. RESTART_UI not sent"
                 " (zynthian ignores it while busy); try again, -t SECONDS to wait longer")
        time.sleep(1)

    # 2. RESTART_UI, the process ends
    send("/CUIA/RESTART_UI")
    t_sent = time.monotonic()
    deadline = t_sent + timeout
    while alive(pid):
        if time.monotonic() >= deadline:
            st = query()
            if st and st["busy"]:
                fail(3, f"no restart: zynthian (PID {pid}) still runs {timeout:.0f} s after RESTART_UI,"
                     f" busy with {describe(st)} (it ignores RESTART_UI while busy)")
            fail(3, f"no restart: zynthian (PID {pid}) still runs {timeout:.0f} s after RESTART_UI"
                 + ("" if checked else " (its busy state couldn't be read)")
                 + "; the UI hasn't run the CUIA (hanging?), it may still restart later")
        time.sleep(0.2)

    # 3. A new process, ready
    deadline = time.monotonic() + timeout
    while True:
        new = zyn_pid()
        if new is not None and new != pid:
            break
        if time.monotonic() >= deadline:
            fail(4, f"zynthian (PID {pid}) ended, but no new zynthian process {timeout:.0f} s later"
                 " (the launcher didn't start it again: see ~/.local/state/tinydm.log)")
        time.sleep(0.2)
    if not answers_status(new):
        # Older code: no query to ask; it runs and doesn't end during NO_ANSWER_GRACE
        t = time.monotonic()
        while time.monotonic() - t < NO_ANSWER_GRACE:
            if not alive(new):
                fail(5, f"the new zynthian (PID {new}) ended while starting (see ~/.local/state/tinydm.log)")
            time.sleep(0.5)
        print(f"zynthian restarted (RESTART_UI): PID {pid} -> {new}; its code has no /STATUS/BUSY:"
              f" running for {NO_ANSWER_GRACE} s, readiness not checked")
        return
    deadline = time.monotonic() + timeout
    pids = [new]
    show = Shown()
    while True:
        st = query()
        if st is not None and st["pid"] == new and not st["busy"]:
            break
        if st is not None and st["busy"]:
            show(st, f"new zynthian (PID {new}) starting: {describe(st)}")
        if not alive(new):
            new = zyn_pid()
            if new is None or new in pids:
                fail(5, f"the new zynthian (PID {pids[-1]}) ended while starting (see ~/.local/state/tinydm.log)")
            pids.append(new)
            print(f"the new zynthian ended while starting, another one runs: PID {new}", flush=True)
        if time.monotonic() >= deadline:
            if st is None:
                fail(5, f"the new zynthian (PID {new}) doesn't answer /STATUS/BUSY {timeout:.0f} s after"
                     " its start (hanging? see ~/.local/state/tinydm.log)")
            fail(5, f"the new zynthian (PID {new}) is still busy {timeout:.0f} s after its start: {describe(st)}")
        time.sleep(0.5)
    again = f", {len(pids) - 1} more restart(s) while starting" if len(pids) > 1 else ""
    print(f"zynthian restarted (RESTART_UI): PID {pid} -> {new}, ready after"
          f" {time.monotonic() - t_sent:.1f} s{again}")


if __name__ == "__main__":
    main()
