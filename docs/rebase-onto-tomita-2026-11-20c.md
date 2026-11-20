# Rebase of main onto origin/tomita 0c1098a6 (2026-11-20, third)

`main` a93b9762c (tomita 88635347d + 9 strands, 492 commits) rebased onto `origin/tomita`
0c1098a68 (6 new upstream commits and 3 merges). Procedure: docs/rebasing-onto-upstream.md. The
analysis before the rebase (per upstream commit, duplicates, interactions, dry run) is in
zynthian-stuff `results/2026-11-20-tomita-0c1098a6-impact.md`.

## Upstream changes in the range

| Commit | What |
|---|---|
| d6d08865 | CC feedback broker (`zyngine/zynthian_cc_feedback.py`, `chain_manager.cc_feedback`): drivers register a callback for their MIDI input and get the values of the controllers bound to its CCs (MIDI learn and their own bindings); APC40 mk2 and Behringer Motor rewritten onto it |
| 07793ae7 | SysEx identity: the ctrldev manager asks devices without an ID driver who they are and autoloads drivers by `sysex_ids` (DIN-5 ports); the MIDI config screen asks every input and lists identity-matched drivers |
| 1ab1ee19 | broker: continuous knobs (APC40 device controls) on toggle controllers |
| ab067ee3 | vangelis' copy of 3624cfc6 (patch-parameter `drawbar` key), already in 88635347: no change |
| 1723a5ab | virtual zynthian: no VNC for the UI; the admin screen's VNC entry follows `vncserver1` |
| 38063708, 27067e23, 0c1098a6 | merges |

## Dropped (obsolete upstream)

Strand 01's de6ea448 "APC40 mk2: end() unregisters the ZS3 handler with unregister()" and
6a360d91 "Behringer Motor: reset_feedback() passes its callback to unregister_send_value_cb()"
fixed code d6d08865 deletes (the APC40's `SS_LOAD_ZS3` handler, the Motor's `reset_feedback()`):
both conflicted and were dropped with their tests. Strand 01 has 55 commits. Their upstream
candidate rows say "obsolete upstream"; the branches `fix/apc40-mk2-end-unregister` and
`fix/behringer-motor-reset-feedback` (no pull request was opened) are obsolete too.

## Conflicts and resolutions

| Strand | Commit | Conflict | Resolution |
|---|---|---|---|
| 01-upstream | 5a6665378 import cycle | the import block: d6d08865 adds the broker import next to the state-manager import 5a666537 removes | broker import kept, state-manager import removed |
| 03-port | 87ed0cc4c desktop mode | the admin screen's Wi-Fi/VNC/Bluetooth entries, indented under `if not zynconf.desktop_mode:`, vs 1723a5ab's `vncserver1` | ours with `vncserver1` |
| 05-tkabs | 42337d654 MIDI config lists as modules | 07793ae7's identity request loop in the Tk list builder that the commit moves | ported into `zynthian_midi_config_data.midi_config_list()` (both UIs) |
| 05-tkabs | 723d699a3 driver list as module functions | 07793ae7's driver list (`get_device_drivers()`, the identity note) in the Tk options that the commit moves | `device_drivers()` = `request_identity()` + `get_device_drivers()`; `driver_description(driver_class, sm=None, idev=None)` adds "Matches the device's SysEx identity (...)"; the Tk screen passes `sm, idev` |
| 06-loadopt | 45cf83069 remove_all_chains once | `clear_midi_binding()`: d6d08865's `cc_feedback.bindings_changed()` after `remove_unused_automate()`, which 45cf8306 defers during `remove_all_chains()` | the broker refresh goes with the immediate path; `remove_all_chains()` refreshes it once in its `finally`, after the deferred automation checks |

Auto-merged with context changes only: 04-ctrldev's a84370bc5 (user driver folders) and
470276781 (HID drivers) next to 07793ae7's new manager attributes. The resolutions were made in a
dry run first and replayed from it (the result's tree is the dry run's).

## Checks

- **Lost upstream** (`refactor_report.py --lost-upstream 88635347d 0c1098a68 <top>`): 2 lost,
  1 changed, 2 arrived, 58 kept, 4 format. All five are the resolutions above: the lost/changed
  hunks are 07793ae7's Tk midi-config code, now in `zynthian_midi_config_data.py` in the
  module's form (identity loop in `midi_config_list()`, driver list and note in
  `device_drivers()` / `driver_description()`); arrived: the `vncserver1` check (indented) and
  the broker refresh (also in `remove_all_chains()`).
- **strand-check** (base 0c1098a68): linear, no merge, no empty commit; 01 55, 02 19, 03 43,
  04 5, 05 43, 06 29, 07 239, 09 33, 10 25 (with these notes; 491 commits). Strand 01 has no
  Claude-Session line and sits directly on tomita.
- **Hashes:** the changelogs and upstream-candidates.md map to the new range or upstream, except
  the intentional e6fdd5fe, de6ea448 and 6a360d91 (dropped).

## Tests

- **Test VM** (2262, `test_vm.sh run all` at the top): default 1085 passed / 4 failed / 6 errors /
  4 skipped / 26 xfailed, gui 1087 / 4 / 6 / 2 / 26, native 252 / 13 xfailed. Strand 01 top
  alone (default): 889 passed / 4 failed / 6 errors / 3 skipped / 26 xfailed. The 4 failures and
  6 errors are upstream's new tests for a driver tomita doesn't have
  (`zynthian_ctrldev_behringer_fcb1010_riban`: test_cc_feedback `test_fcb_*` ImportError,
  test_ctrldev_identity 4 failures); upstream's own tree fails them the same way (upstream
  candidates, "Noticed"). Nothing else fails, the APC40 and Motor lifecycle tests included.
- **ZynthianOS VM** (2272): its zynthian-ui moved to 0c1098a6 (`git pull`); upstream's own tree:
  815 passed / 5 failed / 6 errors (the 10 above and the flaky zynaudioplayer seek test). Strand
  01 top synced over it, native sources touched and rebuilt: default 888 passed / 5 failed /
  6 errors (the same 11), native 252 / 13 xfailed. Pitfall: `run-tests` doesn't rebuild
  `tests/native/build`, which the default run's native tests load; a first run with the
  previous round's libraries failed strand 01's zynseq/zynmixer tests and segfaulted. Run
  `tests/native/build_native.sh /zynthian/zyncoder` in the VM after a sync with C changes.
  Restored, native libraries rebuilt from the original tree, "usable: yes".
- **Qt VM 2252** (`sync_ui.sh -V -R` from the rebased tree): restart ready after 4.5 s;
  001-Parity Test loaded. Over the websocket (8370; upstream's `zynctl.py` run inside the VM,
  with `/usr/share/zynthian/python` on PYTHONPATH): `state`/`chains` answer; a Dexed note peaks
  at -22 dBFS, `ZYNPOT 0,-20` on the mixer takes it to -34 (and back); chain control of Dexed
  (52 pages, arrows move); a setBfree chain added through ADD_CHAIN: its control pages and the
  drawbar view (16' ... 1') show. Main's code synced back, Parity Test reloaded, theme v4.

## Follow-ups

1. Qt: `zynqt/screens/routing.py` could pass `ui.state_manager, idev` to `driver_description()`
   for the SysEx identity note, and show `get_identity_str()` in the device options.
2. `request_identity()` runs on each autoload attempt for a device without an ID driver (once
   per port and 5 s): watch it on Nura/PipeWire with many MIDI ports.
3. `zynthianos_vm.sh run-tests`: build `tests/native` first (see the pitfall above).
4. Upstream: the tests for the missing FCB1010 driver (upstream-candidates.md, "Noticed").
