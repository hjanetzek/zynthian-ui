# Load each factory snapshot in the running zynthian and compare the chains with the file: every
# processor of the snapshot (by id) must be there with its engine, and its preset loaded (SFZ,
# SoundFont, LV2 preset). Saves the current state first and restores it afterwards.
# Run with nura/tools/zyninject.sh test_factory_snapshots.py -t 1200 (Tk or Qt UI).

OUTPUT = "/tmp/zynthian-test-factory-snapshots.txt"
SETTLE = 3           # seconds to wait after each load (engines finishing their start)
ONLY = ""            # a substring of snapshot names to test only those, e.g. "012"

import glob
import json
import os
import threading
import time
import traceback

from zyngui import zynthian_gui_config
from zynconf import zynthian_paths


def _snapshot_procs(fpath):
    """{proc_id: (eng_code, preset file or name or None)} of a snapshot file"""
    with open(fpath) as f:
        snap = json.load(f)
    snap = zynthian_paths.remap_os_paths(snap)
    procs = {}
    zs3 = snap.get("zs3", {}).get("zs3-0", {}).get("processors", {})
    for chain in snap.get("chains", {}).values():
        for slot in chain.get("slots", []):
            for proc_id, eng_code in slot.items():
                pinfo = zs3.get(str(proc_id), {}).get("preset_info")
                procs[int(proc_id)] = (eng_code, pinfo[0] if pinfo else None)
    return procs


def _zyn_test():
    sm = zynthian_gui_config.zyngui.state_manager
    cm = sm.chain_manager
    lines = []
    backup = "/tmp/zyninject-before-factory-test.zss"
    try:
        sm.save_snapshot(backup)
        files = sorted(glob.glob(zynthian_paths.data_dir + "/snapshots/*.zss"))
        ok_count = 0
        for fpath in files:
            name = os.path.basename(fpath)
            if ONLY and ONLY not in name:
                continue
            expected = _snapshot_procs(fpath)
            t0 = time.monotonic()
            state = sm.load_snapshot(fpath)
            dt = time.monotonic() - t0
            time.sleep(SETTLE)
            problems = []
            if state is None:
                problems.append("load_snapshot failed")
            for proc_id, (eng_code, preset) in sorted(expected.items()):
                proc = cm.processors.get(proc_id)
                if proc is None:
                    problems.append(f"{proc_id} {eng_code}: missing")
                    continue
                if proc.eng_code != eng_code:
                    problems.append(f"{proc_id} {eng_code}: loaded as {proc.eng_code}")
                if proc.engine is None:
                    problems.append(f"{proc_id} {eng_code}: no engine")
                elif getattr(proc.engine, "proc", "n/a") is None and eng_code not in ("MI", "MR"):
                    problems.append(f"{proc_id} {eng_code}: engine process not running")
                if preset and not proc.preset_info:
                    problems.append(f"{proc_id} {eng_code}: preset not loaded ({os.path.basename(str(preset))})")
            extra = sorted(set(cm.processors) - set(expected) - {p for p in cm.processors if cm.processors[p].eng_code in ("MI", "MR")})
            n_chains = len([c for c in cm.chains if c != 0])
            status = "OK" if not problems else "PROBLEMS"
            ok_count += not problems
            lines.append(f"{name}: {status} ({len(expected)} processors, {n_chains} chains, {dt:.1f} s)")
            lines += [f"    ! {p}" for p in problems]
            if extra:
                lines.append(f"    (extra processors: {extra})")
        lines.append(f"{ok_count} of {len([f for f in files if not ONLY or ONLY in os.path.basename(f)])} snapshots complete")
    except BaseException:
        lines.append("test failed:\n" + traceback.format_exc())
    finally:
        try:
            sm.load_snapshot(backup)
            lines.append("previous state restored")
        except BaseException:
            lines.append("restoring the previous state failed:\n" + traceback.format_exc())
        with open(OUTPUT, "w") as f:
            f.write("\n".join(lines) + "\n")


threading.Thread(target=_zyn_test, name="zyninject factory snapshots", daemon=True).start()
