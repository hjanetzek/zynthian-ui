# Changelog: 10-docs, shared docs and plans

What strand 10 of `main` changes, newest entry first: the docs shared by all strands (logs, plans,
analyses, rebase notes). File-disjoint from the code strands. Marker `strand/10-docs`; this file is
the strand's last commit, with 01-upstream's changelog commit below it (see
[README.md](README.md)).

## 2026-11-20: rebase onto tomita 0c1098a6: notes (rebase-onto-tomita-2026-11-20c.md)

- `7ed4acd1f` docs: rebase onto tomita 0c1098a6: two strand-01 fixes obsolete upstream, SysEx identity in the shared MIDI config module, checks, tests

## 2026-11-20: rebased onto tomita 88635347, with the jalv start-failure and Qt websocket branches integrated: notes and the Qt websocket status

- `79b435098` docs: rebase onto tomita 88635347, with the jalv and Qt websocket integration: no conflicts, checks, tests
- `e1df6b13c` docs: tomita changes: the Qt UI has the websocket API now

## 2026-11-20: the changelog tools also remap docs/upstream-candidates.md

- `2b9005414` docs: changelog tools: the remap also covers docs/upstream-candidates.md

## 2026-11-20: the strand when the changelog started

19 commits on strand 09, written 2026-11-03 to 2026-11-20.

- **Plans:** reimplementing the UI (Qt Quick with PySide6 decided), the CUIAs the Qt UI missed
  (done: all 126 in both UIs) (`e54e4489c`, `1a0c3e348`, `79763b765`, `75f28e91f`). Docs:
  [ui-reimplementation-plan.md](../ui-reimplementation-plan.md),
  [qt-cuia-plan.md](../qt-cuia-plan.md).
- **Analyses:** architecture, multi-zynthian and Ableton Link, the OSC interface, zynthian widgets
  of LV2 plugins (`7849bde41`, `37554d9dd`, `eae174614`, `f816413d2`). Docs:
  [architecture.md](../architecture.md), [multi-zynthian-and-link.md](../multi-zynthian-and-link.md),
  [osc-interface.md](../osc-interface.md).
- **Rebasing onto upstream:** the procedure, the check for upstream changes lost in moved code, the
  feature strands and their scripts, the changelogs; the notes of the rebases onto tomita
  (`443bfb955`, `20d7f8f8f`, `17cc81924`, `532698837`, `4b3254682`). Docs:
  [rebasing-onto-upstream.md](../rebasing-onto-upstream.md),
  [rebase-onto-tomita-2026-11-20.md](../rebase-onto-tomita-2026-11-20.md).
- **Upstream candidates:** the living list of what we could offer upstream and its state
  (`0b19554c3`). Docs: [upstream-candidates.md](../upstream-candidates.md).
