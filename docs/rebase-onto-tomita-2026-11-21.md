# Integration and rebase of main onto origin/tomita 3dbab929 (2026-11-21)

`main` 5adf23a92 (tomita 0c1098a68 + 9 strands, 491 commits): four finished branches placed into
their strands, then the whole stack rebased onto `origin/tomita` 3dbab929d (5 new upstream commits
and 2 merges). Procedure: docs/rebasing-onto-upstream.md. The analysis before the rebase (per
upstream commit, duplicates, files, dry run) is in zynthian-stuff
`results/2026-11-21-tomita-3dbab929-impact.md`.

## Placed branches (on 0c1098a68, before the rebase)

| Branch | Strand | Commits | Notes |
|---|---|---|---|
| `fix/jalv-output-decoding` / `jalv-poll-spin` | 01 | 5b88c2a72 jalv engine: an invalid UTF-8 byte in jalv's output doesn't stop its reading | at strand 01's end; one conflict with 01's start watchdog (cb164ca40) around the jalv `Popen`: the watchdog kept, `errors="replace"` added, as jalv-poll-spin's version |
| `jalv-poll-spin` | 06 | fe41b8a34 tests: jalv's output thread after jalv's end | tests 06's `proc_poll_thread_task()`; its fake jalv now sets the exit status before closing the output (`EndingJalv`): the thread could read the end first and log "still running" (failed once in the test VM) |
| `small-fixes-2026-11-21b` | 03 | 42521f1cd desktop launcher: source the configuration only in each start's subshell | |
| | 07 | 6c410e18a CUIA thread guards, bd2321d37 file selector for path controllers, b1414970f SS_GUI_CONTROL_MODE, a6df03e60 BACK after adding a chain | |
| | 09 | aeeb88da6 no firewall in the VMs, 29ffda845 zynthianos_vm.sh sync/restore/run-tests, 26b3c8da2 qemu_compare.sh waits for SSH | |

None of the eight small fixes needed splitting: each touches only its strand's files.
Upstream-candidate rows: the decoding fix (ready, strand 01); noticed: Tk's lost
`SS_GUI_CONTROL_MODE` listener (upstream 631c645d6), inet_radio's output thread spinning, AIDA-X
path parameters without file types, Neural Amp Modeler aborting without a model.

## Upstream changes in the range

| Commit | What |
|---|---|
| 6f18babb | CC feedback broker keeps the callbacks: `zctrl.send_value_cb` and `register_/unregister_send_value_cb()` gone, `zctrl.feedback` + `send_feedback()`; the ctrldev manager keeps identity replies |
| a2bbb360 | broker comments |
| d7d241aa | Tk processor options: Remove after Reload |
| 470728c7 | `.claude/skills/zynthian-lv2-plugin/`: a Claude skill for DPF LV2 plugins with zynthian widgets |
| 3dbab929 | FCB1010 (riban firmware) driver; `sysex_ids` are bytes, `on_identity()` takes bytes |
| 5021e61b, b6552c4e | merges |

## Rebase

`git rebase --update-refs origin/tomita`: **no conflicts**, nothing dropped (no strand-01 commit is
upstream; pull requests #618 and #619 are still open). No strand used `send_value_cb` outside
upstream's own files; docs/architecture.md, which described the callback list, now describes the
broker (b9dc48399, strand 10). The FCB1010 driver makes upstream's own broker/identity tests pass
(the "Noticed" row of 2026-11-20 is closed: fixed upstream).

Lost upstream (`refactor_report.py --lost-upstream 0c1098a68 3dbab929d`): 0 lost, 0 changed,
0 arrived, 80 kept, 18 format.

Qt follow-ups (not done): the Qt processor options have no "Reload" entry (Tk has it; with
d7d241aa's order Replace, Reload, Remove).

## Checks and tests

- strand-check (base 3dbab929d): 01 56, 02 19, 03 44, 04 5, 05 43, 06 30, 07 243, 09 36, 10 27
  = 503, ok. Strand 01 sits directly on tomita, no Claude-Session lines.
- Every hash in the changelogs and upstream-candidates resolves to this history or upstream,
  except the deliberately dropped e6fdd5fe, de6ea448, 6a360d91.
- Test VM 2262, top: default 1152 passed / 4 skipped / 26 xfailed, gui 1154 / 2 / 26, native
  252 / 13 xfailed: no failures (the FCB1010 errors of the last rebases are gone). Strand 01
  alone: default 908 / 3 / 26, gui 910 / 1 / 26, native 252 / 13: no failures.
- ZynthianOS VM 2272 (its zynthian-ui pulled to 3dbab929), strand 01 (`run-tests native` first: it rebuilds tests/native,
  the default run doesn't): default 908 passed / 1 failed / 2 skipped / 26 xfailed, native 251 / 1 /
  13 xfailed; the one failure both times is zynaudioplayer's
  `test_start_after_seeking_while_stopped_plays_from_the_beginning`, which fails the same on
  upstream's own tree there (flaky in this VM, as `test_crop_start_does_not_move_where_playback_begins`
  before). A first attempt ran the default suite before the rebuild (stale libraries: a segfault in
  the zynseq tests) and left JACK state behind that hung `jack.Client()` in the native fixture,
  also on upstream's tree, until the VM was rebooted. Restored, native libraries rebuilt from the
  original tree, "usable: yes".
- Qt VM 2242 (480x320): starts with Parity Test; a samplv1 chain's "Sample File" controller
  (Params 1) opens the file selector (User Samples, sfz, System Samples, puredata); the websocket
  answers from the host on 8390. Main's code, theme v4 and Parity Test restored.
