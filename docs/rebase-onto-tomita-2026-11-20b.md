# Rebase of main onto origin/tomita 88635347 (2026-11-20, second)

`main` af7633ee6 (tomita 6e0527a45 + 9 strands) with three branches integrated first (jalv start
failure into strand 01, the Qt ZYNPOT and websocket branches into 05/07/09), then rebased onto
`origin/tomita` 88635347d (2 new upstream commits and a merge). Procedure:
docs/rebasing-onto-upstream.md. The analysis before the rebase (per upstream commit, overlaps,
dry run) and the integration's conflicts are in zynthian-stuff
`results/2026-11-20-tomita-88635347-impact.md`.

## Upstream changes in the range

| Commit | What |
|---|---|
| 4b80624a | sfizz: voices and preload size in a `try` (a non-numeric `RBPI_VERSION_NUMBER` on non-RBPi platforms: 64 voices, preload 32768) |
| 88635347 | Tk mixer: `fader_horizontal = None` for strips without mixer processor; `tag_bind` and `draw_level()` check it |
| a3435270 | merge |

## Conflicts and resolutions

None: all 491 commits applied cleanly. Related, not duplicate: 02-tkfix's
`has_mixer_widgets()` guards (631db291, 86881123) return early from the strip's draw methods for
a strip built before its chain got a mixer processor; upstream's check covers the item in
`__init__`'s `tag_bind` and `draw_level()`. Both stay, side by side in `draw_level()`. The Qt
mixer checks `chain.zynmixer_proc` everywhere (no such bug).

## Integration before the rebase

- **Strand 01, at its end:** the jalv start-failure fixes (an engine whose constructor raises or
  a jalv that exits or hangs before its prompt fails the processor add cleanly, a new chain whose
  processor fails is removed, the output thread and `test_lv2_plugin()` stop at jalv's EOF).
  Their main-side conflicts: 03-port's desktop engine commit keeps only its comment on the failed
  processor's cleanup; 06-loadopt's jalv -B and crashed-jalv logging commits combine the import
  lines, the latter keeps only its exit-status log in the output thread. The tree equals the
  branch prepared on main (`jalv-start-failure-main`).
- **05-tkabs:** the websocket server and its feedback streams as a toolkit-independent mixin
  (`zyngui/zynthian_websocket.py`).
- **07-qt:** ZYNPOT run directly, bad CUIA parameters, the encoders over dialogs; the websocket
  API on port 8370 with Tk's `screen_state` (`zynqt/ws_state.py`, `ws_keys.py`, docs/qt-websocket.md).
  The two branches met in `zynqt/ui.py` at the module helpers before `class ZynUI` (both kept).
- **09-devtools:** the QEMU VMs forward the UI websocket.
- **10-docs:** upstream-tomita-changes-2026-11-15.md no longer lists the Qt websocket server as
  open; upstream candidates: the jalv fixes, and two open points (a failing synth replacement loses
  the chain's synth; a snapshot chain whose only processor failed keeps its strip).

## Checks

- **Lost upstream** (`refactor_report.py --lost-upstream 6e0527a45 88635347d <top>`): 0 lost,
  partly lost, reverted, re-added, changed or arrived; 5 hunks kept, 2 format. With the jalv
  commits as "upstream" (`--lost-upstream 02145ae5c <jalv top> <top>`): one line "lost", on
  purpose: the output thread's "has ended unexpectedly" log became 06-loadopt's
  `log_jalv_end(proc, "ended unexpectedly with")`, with jalv's exit status.
- **strand-check** (base 88635347d): linear, no merge, no empty commit; 01 57, 02 19, 03 43,
  04 5, 05 43, 06 29, 07 239, 09 33, 10 24 (492 commits). Strand 01 has no Claude-Session line
  and sits directly on tomita.
- **Tree:** the rebased top = the integrated top + upstream's range (2 files).
- **Test VM** (2262, `test_vm.sh run all` at the rebased top): default 1057 passed / 4 skipped /
  26 xfailed, gui 1059 / 2 skipped / 26 xfailed, native 252 / 13 xfailed: no failure. Strand 01
  top alone (default): 861 passed / 3 skipped / 26 xfailed.
- **ZynthianOS VM** (2272): its zynthian-ui moved to 88635347 (`git pull` in the VM); strand 01
  top synced over it, native sources touched and rebuilt: default 860 passed / 1 failed / 3
  skipped / 26 xfailed, native 252 / 13 xfailed. The failure is zynaudioplayer's timing-sensitive
  `test_start_after_seeking_while_stopped_plays_from_the_beginning` (or its sibling
  `test_crop_start_does_not_move_where_playback_begins`): on upstream's own tree in the same VM
  4 of 9 runs of `test_player.py` fail the same way, so it isn't strand 01's. Restored, native
  libraries rebuilt from the original tree, "usable: yes".
- **Qt VM 2252** (`sync_ui.sh -V -R` from the rebased tree, `websocket_server` copied into
  `~/.local` for the test, removed afterwards): restart ready after 3.5 s; 001-Parity Test loaded
  (Dexed, MiniOPL3, Fabla). Over the websocket (an ssh bridge to 8370; upstream's
  `zynctl.py`): `state` reports `mixer | 001-Parity Test`, `chains` the four chains; a Dexed note
  peaks at -25 dBFS on the DPM stream, `ZYNPOT 0,-20` on the mixer takes it to -36 (and back);
  `SCREEN_CONTROL` shows Dexed's chain control with its 52 pages, arrows move the selection; a
  `ZYNPOT x,1` is dropped with a warning. Main's code synced back, Parity Test, theme v4.

## Follow-ups

1. `ws_cuia_args_ok()` (zynqt/ui.py) still checks ZYNPOT with `int()`: since the ZYNPOT commit the
   CUIA thread converts with `zynpot_params()` (accepts "1.0") and no longer ends on bad
   parameters, so the websocket check is stricter than needed for ZYNPOT (ZYNSWITCH still needs
   it), and docs/qt-websocket.md's reason for it is outdated.
2. The two open upstream points from the jalv work (docs/upstream-candidates.md, "Noticed").
3. Nura has no package for `websocket_server`: the Qt UI's websocket only runs where it is
   installed (nura-builds).
