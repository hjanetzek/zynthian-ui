# Rebase of main onto origin/tomita 6e0527a4 (2026-11-20)

`main` 9b712450d (tomita 7ed6003b + 9 strands, 459 commits) rebased onto `origin/tomita` 6e0527a45
(13 new upstream commits, 2 of them merges). Procedure: docs/rebasing-onto-upstream.md. The
analysis before the rebase (per upstream commit, overlaps, follow-ups) is in zynthian-stuff
`results/2026-11-20-tomita-6e0527a4-impact.md`.

## Upstream changes in the range

| Commit | What |
|---|---|
| 3d28ae56 | Tk MIDI recorder title "MIDI Player" (the Qt screen already said so) |
| 91d51107, 8c2822c9 | zctrl value-change callbacks are a list: `register_send_value_cb()` / `unregister_send_value_cb()` replace `set_/reset_send_value_cb()`; APC40 mk2 and Behringer Motor drivers switched |
| 6e0527a4 | APC40 mk2 updates its encoders on SS_LOAD_ZS3 |
| 747704d7 | the strict xfails of `remove_slow_update_callback` dropped |
| c9404a63 | tests on a real V5: the write guard lets an allowed root win a tie (ZYNTHIAN_UI_DIR = repo root on a device); zynsmf playback xfail on x86 only |
| 0261e0ca, 2ac20a90, f2a92055 | CI: bs4, python3-lilv + liblilv-dev, websocket-server; `test_lv2_widgets` skips with a stubbed lilv; `requirements.txt` rewritten for ZynthianOS devices |
| a94037ec | `requirements_all.txt`, `create_venv.sh all` |
| d1e19916 | Claude skill `.claude/skills/zynthian-operator` (drives a Tk UI over the websocket, `screen_state` as text) |

## Conflicts and resolutions

Only two, both strand 01, both duplicates of upstream commits:

| Our commit | File | Resolution |
|---|---|---|
| e6fdd5fea "tests: remove_slow_update_callback is fixed upstream (7ed6003b), drop its xfail markers" | tests/integration/test_state_manager.py | **Dropped**: upstream's 747704d7 removes the same two markers (and the reason constant). |
| c25171667 "tests: the websocket handshake test needs the real websocket-server package" | requirements-dev.txt | Upstream's file (f2a92055 adds the same requirement, with a comment). The commit keeps only the skip where `websocket_server` is stubbed; reworded: "tests: skip the websocket handshake test where websocket-server is stubbed" (797afc63). |

Strands 02-10 applied without a conflict.

## New commits

Two upstream bugs from the new range, fixed at the end of strand 01 (offered with PR #617):

- fceb20d7 **APC40 mk2: `end()` unregisters the ZS3 handler with `unregister()`.** 6e0527a4 calls
  `zynsigman.unregister_queued()`, which doesn't exist: `end()` raised AttributeError, so
  unloading/disabling the driver raised in `unload_driver()` and `on_zs3` stayed registered. The
  driver lifecycle contract test didn't show it (the APC40 is a strict xfail there for another
  defect); a focused test does.
- 02145ae5 **Behringer Motor: `reset_feedback()` passes its callback** to
  `unregister_send_value_cb()` for the Pianoteq controllers (TypeError since 91d51107). Test included.

Docs strand: "docs: upstream candidates" (hashes remapped by subject: 77 tokens; 10 upstream,
36 of older histories left as written; e6fdd5fe's row now points to upstream 747704d7, c2517166's
to the skip-only 797afc63, the ZynthianOS write-guard row "fixed upstream (c9404a63)", rows for the
two new fixes), "docs: architecture: zctrl feedback callbacks are a list", and this file.

## Checks

- **Lost upstream** (`refactor_report.py --lost-upstream 7ed6003b 6e0527a45 <top>`): 0 lost,
  0 partly lost, 0 reverted, 0 arrived; 27 hunks kept, 2 format, 2 "changed": the two lines our
  new fixes change on purpose (APC40 `unregister`, Behringer `send_feedback`). Same at the strand 01
  top. No upstream hunk is in code our tkabs/qt strands moved.
- **strand-check** (base 6e0527a45): linear, no merge, no empty commit; 01 52, 02 18, 03 42,
  04 4, 05 39, 06 26, 07 232, 09 31, 10 18 (462 commits). Strand 01 has no Claude-Session line.
- **Tree:** the rebased top = old main + upstream's range, except the two duplicates (identical
  content kept once) and the new commits.
- **Test VM** (2262, `test_vm.sh run all` at the top): default 984 passed / 3 skipped / 26 xfailed,
  gui 986 / 1 skipped / 26 xfailed, native 252 / 13 xfailed: no failure. Strand 01 top alone
  (default): 853 passed / 3 skipped / 26 xfailed. The two new tests fail without the fixes
  (AttributeError `unregister_queued`, TypeError `cb_func`) and pass with them.
- **ZynthianOS VM** (2272): its zynthian-ui moved to 6e0527a4 (`git pull` in the VM, no native
  changes in the range); strand 01 top synced over it, native sources touched and rebuilt: default
  852 passed / 1 failed / 3 skipped / 26 xfailed, native 251 / 1 failed / 13 xfailed; the failure in
  both is the known flaky `zynaudioplayer test_crop_start_does_not_move_where_playback_begins`.
  The write-guard failure of the earlier runs (`test_sandbox_tmp_and_repo_are_writable`) is gone
  (upstream c9404a63). Restored, native libraries rebuilt from the original tree, "usable: yes".
- **Qt VM 2252** (`sync_ui.sh -V -R` from the rebased tree): restart ready after 10 s; 001-Parity
  Test loaded (Dexed, MiniOPL3, Fabla); mixer: the Qt mixer model's `setLevel` reached the DSP
  (0.25) and was restored; chain control of Dexed shown, `ZYNPOT_ABS 0,0.5` set cutoff to 0.5,
  restored. (`ZYNPOT` by injected CUIA changes nothing in chain control on main's code either: not
  from the rebase.) Main's code synced back, Parity Test loaded, theme v4.

## Follow-ups

1. **Qt UI and the zctrl callback list:** a Qt control screen / mixer could register
   `register_send_value_cb()` for the shown controllers instead of polling values changed by MIDI
   or drivers; the callbacks run in the thread that sets the value, so only post to the GUI thread.
2. **Websocket `screen_state` for the Qt UI**, so upstream's zynthian-operator skill (and our
   agents) can drive and read the Qt UI as text; also a cheap Tk/Qt parity probe.
3. Upstream's skill: `zynctl.py cuias` imports `zynagent/zynagent_tools.py`, which is in neither
   tomita nor vangelis (report upstream). The skill defaults to `zynthian.lan`; against our Tk VMs
   or the Pi 4 kit use `--host` / a forwarded port 8370.
4. `requirements.txt` is now a ZynthianOS device list (Debian packages assumed): not a complete
   dependency list for other systems (nura-builds uses its own package lists).
