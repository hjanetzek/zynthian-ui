# Load snapshots in the running zynthian and compare the chains with each file: every processor of
# the snapshot (as zynthian's legacy converter makes it, so old formats count too) must be there
# with its engine running and its preset loaded. Problems are classified: engine or plugin not
# installed here, preset in the user's data (my-data, other machines' files), preset missing from the
# shipped data. Saves the current state first and restores it afterwards. Results are written after
# each snapshot, so a long run that is interrupted leaves what it has.
#
# Run with nura/tools/zyninject.sh -t 1500 test_factory_snapshots.py (Tk or Qt UI); other snapshots:
#   zyninject.sh -s 'DIR="/tmp/shared-snapshots"' -t 9000 test_factory_snapshots.py  (NAME=VALUE, no spaces)

OUTPUT = "/tmp/zynthian-test-factory-snapshots.txt"
DIR = ""             # directory of .zss files (recursive); "" = the factory snapshots
SETTLE = 2           # seconds to wait after each load (engines finishing their start)
ONLY = ""            # a substring of snapshot paths to test only those, e.g. "012"
FROM = ""            # start at this snapshot path (relative to DIR), to resume an interrupted run

import copy
import glob
import json
import os
import threading
import time
import traceback

from zyngui import zynthian_gui_config
from zynconf import zynthian_paths
from zyngine.zynthian_legacy_snapshot import zynthian_legacy_snapshot


def _expected(sm, fpath):
    """{proc_id: (eng_code, preset file or name or None)} of a snapshot, as zynthian converts it"""
    with open(fpath) as f:
        snap = zynthian_paths.remap_os_paths(json.load(f))
    state = zynthian_legacy_snapshot(sm).convert_state(copy.deepcopy(snap))
    if state is None:
        raise ValueError("newer schema than this zynthian")
    procs = {}
    zs3 = state.get("zs3", {}).get("zs3-0", {}).get("processors", {})
    for chain in state.get("chains", {}).values():
        for slot in chain.get("slots", []):
            for proc_id, eng_code in slot.items():
                pinfo = zs3.get(str(proc_id), {}).get("preset_info")
                procs[int(proc_id)] = (eng_code, pinfo[0] if pinfo else None)
    return procs


def _missing_cause(cm, eng_code):
    info = cm.engine_info.get(eng_code)
    if info is None:
        return "plugin not installed" if eng_code.startswith("JV/") else "unknown engine"
    if info.get("ENGINE") is None:
        return "engine not installed"
    return "not loaded"


def _preset_cause(preset):
    p = str(preset)
    if p.startswith(zynthian_paths.my_data_dir) or "/zynthian-my-data/" in p:
        return "user file"
    if p.startswith("/") and not os.path.exists(p.split("#")[0]):
        return "file missing"
    return "not loaded"


def _zyn_test():
    sm = zynthian_gui_config.zyngui.state_manager
    cm = sm.chain_manager
    lines = []
    totals = {"snapshots": 0, "complete": 0}
    causes = {}

    def write(final=False):
        summary = [f"{totals['complete']} of {totals['snapshots']} snapshots complete"]
        summary += [f"  {n:4d} x {c}" for c, n in sorted(causes.items(), key=lambda x: -x[1])]
        with open(OUTPUT + ("" if final else ".part"), "w") as f:
            f.write("\n".join(lines + summary) + "\n")

    backup = "/tmp/zyninject-before-snapshot-test.zss"
    try:
        sm.save_snapshot(backup)
        root = DIR or zynthian_paths.data_dir + "/snapshots"
        files = sorted(glob.glob(root + "/**/*.zss", recursive=True))
        files = [f for f in files if os.path.basename(f) != "last_state.zss" and (not ONLY or ONLY in f)]
        if FROM:
            files = [f for f in files if os.path.relpath(f, root) >= FROM]
        for fpath in files:
            name = os.path.relpath(fpath, root)
            totals["snapshots"] += 1
            problems = []
            try:
                expected = _expected(sm, fpath)
            except Exception as e:
                lines.append(f"{name}: UNREADABLE ({e})")
                causes["unreadable"] = causes.get("unreadable", 0) + 1
                write()
                continue
            t0 = time.monotonic()
            state = sm.load_snapshot(fpath)
            dt = time.monotonic() - t0
            time.sleep(SETTLE)
            if state is None:
                problems.append(("load_snapshot failed", ""))
            for proc_id, (eng_code, preset) in sorted(expected.items()):
                proc = cm.processors.get(proc_id)
                if proc is None:
                    problems.append((_missing_cause(cm, eng_code), f"{proc_id} {eng_code}"))
                    continue
                if proc.eng_code != eng_code:
                    problems.append(("other engine", f"{proc_id} {eng_code} -> {proc.eng_code}"))
                if proc.engine is None:
                    problems.append(("no engine", f"{proc_id} {eng_code}"))
                elif getattr(proc.engine, "proc", "n/a") is None and eng_code not in ("MI", "MR", "AI", "MX"):
                    problems.append(("engine process not running", f"{proc_id} {eng_code}"))
                if preset and not proc.preset_info:
                    problems.append((f"preset: {_preset_cause(preset)}", f"{proc_id} {eng_code} {os.path.basename(str(preset))}"))
            n_chains = len([c for c in cm.chains if c != 0])
            totals["complete"] += not problems
            lines.append(f"{name}: {'OK' if not problems else 'PROBLEMS'} ({len(expected)} processors, {n_chains} chains, {dt:.1f} s)")
            for cause, what in problems:
                causes[cause] = causes.get(cause, 0) + 1
                lines.append(f"    ! {cause}: {what}")
            write()
    except BaseException:
        lines.append("test failed:\n" + traceback.format_exc())
    finally:
        try:
            sm.load_snapshot(backup)
            lines.append("previous state restored")
        except BaseException:
            lines.append("restoring the previous state failed:\n" + traceback.format_exc())
        write(final=True)


threading.Thread(target=_zyn_test, name="zyninject snapshot test", daemon=True).start()
