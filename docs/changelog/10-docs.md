# Changelog: 10-docs, shared docs and plans

What strand 10 of `main` changes, newest entry first: the docs shared by all strands (logs, plans,
analyses, rebase notes). File-disjoint from the code strands. Marker `strand/10-docs`; this file is
the strand's last commit, with 01-upstream's changelog commit below it (see
[README.md](README.md)).

## 2026-11-28: docs: placement and rebase onto tomita 046817e4 (2026-11-28)

- `3f6dee92f` docs: placement and rebase onto tomita 046817e4 (2026-11-28): conflicts in 01, 02, 03, 05, 06 (keymap test taken upstream, mixer toggle guard, main-loop lock imports), Qt checks, tests

## 2026-11-28: docs: OSC interface: ZS3_DELETE in the CUIA table

- `1482237f1` docs: OSC interface: ZS3_DELETE in the CUIA table

## 2026-11-27: docs: rebase onto tomita 26c42c46 (2026-11-27b)

- `583edada3` docs: rebase onto tomita 26c42c46 (2026-11-27b): conflicts in 01, 03, 04, 05 (two-channel audio to MIDI, router-output fix, RLock), Qt follow-ups, checks

## 2026-11-27: rebase onto tomita 5b0b6966: notes and upstream changes (2026-11-27)

- `f8a81fda4` docs: rebase onto tomita 5b0b6966 (2026-11-27): conflicts in 01, 03, 05, 06 (audio2midi, keymap state, LV2 scan, #1847), fixes, checks

## 2026-11-26: rebased onto tomita e2f423d33: no conflicts; the rebase notes and upstream's changes

- `b16a04520` docs: rebase onto tomita e2f423d3 (2026-11-26): one conflict in 05 (keymap screen state), fixes, checks

## 2026-11-26: docs: the DrivenByMoss drivers in architecture, the CUIA table regenerated (PATTERN_EDITOR_WINDOW for both UIs); strand 08-dbm in the strand table

- `7d30f19ac` docs: architecture: the DrivenByMoss drivers; the CUIA table regenerated (PATTERN_EDITOR_WINDOW)
- `777d37335` docs: strand 08-dbm (strand table, changelog README)

## 2026-11-21: rebased onto tomita 3dbab929 with the 2026-11-21 integration: no conflicts, notes, architecture.md on the broker

- `7133eb3af` docs: rebase onto tomita 3dbab929 with the 2026-11-21 integration: no conflicts, checks, tests

## 2026-11-21: docs: architecture.md on upstream's CC feedback broker keeping the callbacks (6f18babb)

- `3661c18d1` docs: architecture: controller feedback through the CC feedback broker (upstream 6f18babb)

## 2026-11-20: rebase onto tomita 0c1098a6: notes (rebase-onto-tomita-2026-11-20c.md)

- `6737f7514` docs: rebase onto tomita 0c1098a6: two strand-01 fixes obsolete upstream, SysEx identity in the shared MIDI config module, checks, tests

## 2026-11-20: rebased onto tomita 88635347, with the jalv start-failure and Qt websocket branches integrated: notes and the Qt websocket status

- `72b36e7e5` docs: rebase onto tomita 88635347, with the jalv and Qt websocket integration: no conflicts, checks, tests
- `edc79d41d` docs: tomita changes: the Qt UI has the websocket API now

## 2026-11-20: the changelog tools also remap docs/upstream-candidates.md

- `a4802112a` docs: changelog tools: the remap also covers docs/upstream-candidates.md

## 2026-11-20: the strand when the changelog started

19 commits on strand 09, written 2026-11-03 to 2026-11-20.

- **Plans:** reimplementing the UI (Qt Quick with PySide6 decided), the CUIAs the Qt UI missed
  (done: all 126 in both UIs) (`c0909c862`, `23b60f539`, `8fa3ca072`, `ceb864ae3`). Docs:
  [ui-reimplementation-plan.md](../ui-reimplementation-plan.md),
  [qt-cuia-plan.md](../qt-cuia-plan.md).
- **Analyses:** architecture, multi-zynthian and Ableton Link, the OSC interface, zynthian widgets
  of LV2 plugins (`6feb49901`, `299df257c`, `5d1a504db`, `076678296`). Docs:
  [architecture.md](../architecture.md), [multi-zynthian-and-link.md](../multi-zynthian-and-link.md),
  [osc-interface.md](../osc-interface.md).
- **Rebasing onto upstream:** the procedure, the check for upstream changes lost in moved code, the
  feature strands and their scripts, the changelogs; the notes of the rebases onto tomita
  (`0e6677082`, `59d989682`, `aae1216d0`, `c3eab2ae4`, `11ffdfaeb`). Docs:
  [rebasing-onto-upstream.md](../rebasing-onto-upstream.md),
  [rebase-onto-tomita-2026-11-20.md](../rebase-onto-tomita-2026-11-20.md).
- **Upstream candidates:** the living list of what we could offer upstream and its state
  (`61eb1a67c`). Docs: [upstream-candidates.md](../upstream-candidates.md).
