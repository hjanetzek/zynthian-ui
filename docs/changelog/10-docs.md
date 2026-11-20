# Changelog: 10-docs, shared docs and plans

What strand 10 of `main` changes, newest entry first: the docs shared by all strands (logs, plans,
analyses, rebase notes). File-disjoint from the code strands. Marker `strand/10-docs`; this file is
the strand's last commit, with 01-upstream's changelog commit below it (see
[README.md](README.md)).

## 2026-11-26: rebased onto tomita e2f423d33: no conflicts; the rebase notes and upstream's changes

- `edee9c861` docs: rebase onto tomita e2f423d3 (2026-11-26): one conflict in 05 (keymap screen state), fixes, checks

## 2026-11-26: docs: the DrivenByMoss drivers in architecture, the CUIA table regenerated (PATTERN_EDITOR_WINDOW for both UIs); strand 08-dbm in the strand table

- `4ac37271e` docs: architecture: the DrivenByMoss drivers; the CUIA table regenerated (PATTERN_EDITOR_WINDOW)
- `3a915d93f` docs: strand 08-dbm (strand table, changelog README)

## 2026-11-21: rebased onto tomita 3dbab929 with the 2026-11-21 integration: no conflicts, notes, architecture.md on the broker

- `aeb477705` docs: rebase onto tomita 3dbab929 with the 2026-11-21 integration: no conflicts, checks, tests

## 2026-11-21: docs: architecture.md on upstream's CC feedback broker keeping the callbacks (6f18babb)

- `b8b46231b` docs: architecture: controller feedback through the CC feedback broker (upstream 6f18babb)

## 2026-11-20: rebase onto tomita 0c1098a6: notes (rebase-onto-tomita-2026-11-20c.md)

- `8d73122d8` docs: rebase onto tomita 0c1098a6: two strand-01 fixes obsolete upstream, SysEx identity in the shared MIDI config module, checks, tests

## 2026-11-20: rebased onto tomita 88635347, with the jalv start-failure and Qt websocket branches integrated: notes and the Qt websocket status

- `55fc08eb0` docs: rebase onto tomita 88635347, with the jalv and Qt websocket integration: no conflicts, checks, tests
- `3a166c660` docs: tomita changes: the Qt UI has the websocket API now

## 2026-11-20: the changelog tools also remap docs/upstream-candidates.md

- `41ad3dd10` docs: changelog tools: the remap also covers docs/upstream-candidates.md

## 2026-11-20: the strand when the changelog started

19 commits on strand 09, written 2026-11-03 to 2026-11-20.

- **Plans:** reimplementing the UI (Qt Quick with PySide6 decided), the CUIAs the Qt UI missed
  (done: all 126 in both UIs) (`8a38431fe`, `1e224074b`, `4ce6fe816`, `70df84db7`). Docs:
  [ui-reimplementation-plan.md](../ui-reimplementation-plan.md),
  [qt-cuia-plan.md](../qt-cuia-plan.md).
- **Analyses:** architecture, multi-zynthian and Ableton Link, the OSC interface, zynthian widgets
  of LV2 plugins (`a40629839`, `7a141c572`, `469511b0d`, `c8367ad5e`). Docs:
  [architecture.md](../architecture.md), [multi-zynthian-and-link.md](../multi-zynthian-and-link.md),
  [osc-interface.md](../osc-interface.md).
- **Rebasing onto upstream:** the procedure, the check for upstream changes lost in moved code, the
  feature strands and their scripts, the changelogs; the notes of the rebases onto tomita
  (`ac47e7120`, `2c4d46c4d`, `34a9d760d`, `0b71f507f`, `9fd3b4f58`). Docs:
  [rebasing-onto-upstream.md](../rebasing-onto-upstream.md),
  [rebase-onto-tomita-2026-11-20.md](../rebase-onto-tomita-2026-11-20.md).
- **Upstream candidates:** the living list of what we could offer upstream and its state
  (`731ffbcf8`). Docs: [upstream-candidates.md](../upstream-candidates.md).
