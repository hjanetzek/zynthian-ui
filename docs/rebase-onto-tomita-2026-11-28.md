# Placement of the unplaced commits, rebase of main onto origin/tomita 046817e4 (2026-11-28)

`main` d71391174 (tomita 26c42c460 + 10 strands, plus 14 unplaced commits on top: the zs3/dbm work
with its upstream-candidates commit, switch_ui.sh testing, tools/zynctl.sh and 7 Qt widget-shim /
help commits) first placed into its strands, then rebased onto `origin/tomita` 046817e46: 8
upstream commits (docs/upstream-tomita-changes-2026-11-28.md). Basis:
docs/rebase-onto-tomita-2026-11-27b.md. Procedure: docs/rebasing-onto-upstream.md, on the branch
`place-2026-11-28` in its own worktree. Backup tags: `backup/main-pre-place-2026-11-28` =
d71391174 (before the placement), `backup/main-pre-rebase-2026-11-28` (the placed stack before
the rebase).

## Step 1: placement

The upstream-candidates commit ("docs: upstream candidates: SS_ZS3_LIST, change_zs3_id,
ZS3_DELETE; the get_next_zs3_index clash") went into the living "docs: upstream candidates"
commit first (autosquash, before any strand-place.sh run). The zs3 commit spanned three strands
and was split by file; its strand-01 part got a port-neutral message (no "(upstream candidate)",
no Claude-Session line). The dbm commits import `views.py` and build on the host page
(`reporter.py`'s "page" subtree, the host page commands): both are strand-08 code, so 08 (not
04). Then `strand-place.sh -b origin/tomita` per strand, bottom up; no conflicts.

| Commit (on main) | Strand | Note |
|---|---|---|
| 8c672e372 zs3: SS_ZS3_LIST signal, change_zs3_id(), ZS3_DELETE CUIA | 01 | the core, Tk and test files (`zynthian_signal_manager`, `zynthian_state_manager`, `zynthian_gui.py` `cuia_zs3_delete`, `zynthian_gui_zs3*`, `test_zs3_list_signal.py`, `test_gui_zs3.py`): self-contained on tomita |
| (split off) CUIA list: ZS3_DELETE (category zs3) | 05 | `zyngui/zynthian_cuia_list.py` is a strand-05 module |
| (split off) docs: OSC interface: ZS3_DELETE in the CUIA table | 10 | `docs/osc-interface.md` (the table says both UIs: after 07) |
| 156cf96f0 qt: ZS3_DELETE CUIA, change_zs3_id, the ZS3 screen follows SS_ZS3_LIST | 07 | |
| 5847caf66 dbm: zynthian's ZS3s as the host's snapshots | 08 | |
| 9f8037b28 docs: upstream candidates: SS_ZS3_LIST, … | 10 | fixup of the living upstream-candidates commit; its link to 8c672e37 set to the 01 commit by hand (the reworded subject doesn't map) |
| ef335a612 dbm: snapshots: model.zs3_snapshots … | 08 | `test_host_page.py` too |
| 17f8bf95d switch_ui.sh: testing | 09 | |
| 464d53f52 tools/zynctl.sh | 09 | with its `docs/qemu-testing.md` lines (a 09 doc) |
| f7b5b44d7, 3c7f574cc, a030ea6cb, db3a3f0c9, 6bc475fc1, 0ea4d4a09, d71391174 (Qt help / widget shim) | 07 | one changelog entry |

Checks: strand-check.sh over the whole range ok, nothing above `strand/10-docs`; the tree equal to
d71391174's apart from `docs/changelog/*` and `docs/upstream-candidates.md`; no Claude-Session
line in 01; 01 based on tomita 26c42c46, 02 applies directly on it.

## Impact analysis (before the rebase)

Files of each upstream commit that our series also changes (`git diff --name-only 26c42c460
<top>`), the strands touching them and what the Qt UI needs.

| Upstream | Files we change too (our strands) | Expected | Qt UI / test VM |
|---|---|---|---|
| 6435cee7 stale widget binding after a reload | `zynthian_gui_control.py` (01, 02, 03, 05) | clean (new method; the refresh loop's lines untouched) | the Qt screen rebinds on every build: no bug; a test |
| dd017c8d its test | none | clean | runs in default |
| 85cbbf2f / c8b4503c toggle guard, force update | `zynthian_gui_mixer.py` (02, 03, 05), `zynthian_gui_admin.py` (03, 05) | conflict at 02's own toggle guard (same bug) | no Qt admin update entry (Nura) |
| 166af9fd ruff exclude | none | clean | none |
| 7e650774 clean-all freeze: busy screen from the main thread | `zynthian_gui.py` (01, 02, 03, 05, 06, 07) | clean (our commits don't change the busy thread's loading-screen code; strand 05 kept it in the Tk file) | Qt shows the busy overlay from a GUI-thread QTimer already |
| 511edda9 test fixes | `test_view_state.py` (01) | conflict: upstream's version of 01's keymap-state test fix | none |
| 046817e4 `zynthian_mainloop_lock` | `zynautoconnect` (01, 03, 04, 06), `zynthian_engine_inet_radio.py` (03, 06), `zynthian_gui.py` | import-line conflicts (RLock / Lock imports gone next to our imports) | the module is toolkit-free; without `set_tk` its waits are plain: right for Qt, whose cross-thread calls never wait for the GUI thread (`gui_thread.py`). Nothing to map |

## Conflicts, by strand

| Strand | Commit | Conflict | Resolution |
|---|---|---|---|
| 01 | tests: test_view_state: the keymap state from get_keymap_state() | upstream 511edda9 made the same change to the test | upstream's version; the commit became empty and was **dropped** (it only added an unused `getTonic` stub and a comment) |
| 02 | Mixer: also skip toggle, mute and DPM drawing on strips without mixer widgets | upstream 85cbbf2f / c8b4503c guard `draw_toggle` with try/except on `self.toggle` | ours (`if not self.has_mixer_widgets(): return`): the toggle is created in the same block as `fader_overlay`, so the guard covers upstream's case; no bare except |
| 03 | Controller drivers from other folders (ZYNTHIAN_CTRLDEV_PATH); PipeWire MIDI port uids | autoconnect's imports: upstream's `MainLoopLock` next to `zynthian_pipewire_ports` | both |
| 05 | zyngui: wiring layout MIDI set-up in zynthian_wiring | `zynthian_gui.py` imports: `zynthian_mainloop_lock` next to `zynthian_wiring` | both |
| 05 | zyngui: websocket server and feedback streams in a toolkit-independent mixin | the threading import: upstream dropped `RLock`, the mixin moved `WebsocketServer` out | `from threading import Thread, Lock, Event` |
| 06 | zynaddsubfx, autoconnect: wait for events instead of polling | autoconnect's imports: upstream dropped `Lock`, ours added `monotonic`, `Event` | `from time import sleep, monotonic`, `from threading import Thread, Event` |
| 06 | Engines: reap stopped processes, bounded stop timeouts | the inet radio's imports: `end_process`, `PROC_STOP_TIMEOUT` next to `zynthian_mainloop_lock`; its stop (upstream's `zynthian_mainloop_lock.join` of the poll thread, our `end_process`) merged by git | both imports |

## Upstream changes lost in moved code

`refactor_report.py --lost-upstream 26c42c460 046817e46 <top>`: 1 lost, 1 changed, the rest kept.
The lost hunk is 85cbbf2f's `draw_toggle` try/except, replaced by 02's guard (above: a deliberate
rewrite). The changed one is autoconnect's threading import (046817e4), now `Thread, Event` with
06's change. Nothing to port: 7e650774 and 046817e4 change Tk code that strand 05 left in
`zynthian_gui.py` (the busy thread, `busy_screen_update`, `wait_show/close_loading`), and the new
module is used from autoconnect and the inet radio, which no strand moved.

## Qt UI and the main-thread change

The shared modules call no Tk-only helper: `zynthian_mainloop_lock` is in `zyngine/`, has no Tk
import and only services Tk once `zynthian_gui` registered the interpreter (`set_tk`). The Qt UI
doesn't register anything, so `MainLoopLock` is a plain Lock/RLock and `join` a plain join there.
That is the right mapping: the deadlock it prevents needs a thread that waits for the main thread
(Tk runs other threads' Tk calls in the main thread and makes them wait). The Qt UI's calls from
other threads (`zynqt/gui_thread.py`: `GuiCaller.post`, `@gui_thread`) are queued signals that
return at once, and nothing in `zynqt/` waits for the GUI thread (no blocking connections, no waits
on GUI-thread events), so the GUI thread can wait for the autoconnect lock without a deadlock. The
busy overlay (7e650774) is polled in the GUI thread (`ZynUI._poll_status`, a QTimer).

## Fixes and follow-ups for upstream's changes

| Strand | Commit | Why |
|---|---|---|
| 07 | tests: the Qt chain control's widget follows a reloaded processor (upstream 6435cee7) | `tests/unit/test_qt_widget_processor_reload.py`: a plugin widget (PluginView) shown again after a reload, and a reload while shown, end on the new processor object. The Qt UI had no fix to make (`_set_widget` rebinds a view whose processor is another object, on every build) |

## Checks

strand-check.sh over the whole range: ok (01: 64, 02: 19, 03: 45, 04: 9, 05: 52, 06: 30, 07: 281,
08: 6, 09: 42, 10: 34 commits; nothing above `strand/10-docs`). Strand 01 has no Claude-Session
lines; 01 is based on tomita 046817e4 directly, 02 (without its changelog commit) applies directly
on it.

Test VM (port 2264), the top before the follow-ups: `run all` 0 failed: default 1578 passed, 42
skipped, 30 xfailed; gui 1582 passed, 38 skipped, 30 xfailed (upstream's `test_mainloop_lock_tk.py`
runs); native 374 passed, 17 xfailed. The new Qt test with the control-grid tests: 13 passed. The
final top (with the Qt test and these notes): default 1580 passed, 42 skipped, 30 xfailed; gui and
native each 1 failed, `tests/native/zynaudio2midi/test_jack.py::test_stop_releases_held_note` (no
note within 0.5 s of freewheeling), everything else passed. That test is flaky: neither it, its
rig (`tests/jacktest.py`) nor the library changed in this rebase; at the top `run native` passed
4 of 5 times afterwards (main d71391174: 4 of 4). `run default` at the
tops of the strands with conflicts (and 01, whose top changed with the placement):

| Tree | Result |
|---|---|
| 01 top | 1121 passed, 6 skipped, 30 xfailed |
| 02 top | 1128 passed, 6 skipped, 30 xfailed |
| 03 top | 1136 passed, 6 skipped, 30 xfailed |
| 05 top | 1268 passed, 42 skipped, 30 xfailed; 1 failed: `tests/native/zynaudio2midi/test_jack.py::test_stop_releases_held_note` (no note within 0.5 s; "Cannot lock down … memory" in its setup), passed in 3 reruns of the file: flaky, not the rebase |
| 06 top | 1311 passed, 42 skipped, 30 xfailed |

Qt UI in compare VM 2242 (480x320, this tree's Python through its own sync_ui.sh; the package of
the 2026-11-26 era has no `libzynaudio2midi.so`: the test VM's native build copied into
`/usr/lib/zynthian` for the test, removed afterwards): starts, "001-Parity Test" loads (Dexed,
MiniOPL3, Fabla). The 6435cee7 case: "1/3 Octave Spectrum Display Stereo" (spectr30, a PluginView)
added to MiniOPL3's chain, its widget shown, processor options > Reload: back on chain control
with the widget on the reloaded processor, no errors in the log. Main menu > Clean > confirm:
all chains removed, no freeze. Tk UI of this tree in compare VM 2243 (the test VM's native
libraries for the test): starts, "001-Parity Test" loads, main menu > Clean > "Clean All Chains &
Sequences": done at once, no freeze, no tracebacks (the drivenbymoss package there is too old for
08's drivers: `M.HOST_CELL_KIND` missing, as with main).

Afterwards: 2242 back on main's code (d71391174), theme v4 (`zynthian_custom_config.sh` equal to
the `.v4bak`), "900-Test/001-Parity Test" loaded; 2243 back on what it had (the
zynthian-ui-tomita package's files and libraries, from a tar backup), "001-Parity Test" loaded;
both compare VMs stopped.
