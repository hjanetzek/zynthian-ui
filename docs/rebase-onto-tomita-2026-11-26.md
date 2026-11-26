# Rebase of main onto origin/tomita e2f423d3 (2026-11-26)

`main` fedaebd71 (tomita 3dbab929d + 10 strands, 543 commits, the placement of 2026-11-26 with
the new strand 08-dbm) rebased onto `origin/tomita` e2f423d33: 17 upstream commits
(docs/upstream-tomita-changes-2026-11-26.md). Procedure: docs/rebasing-onto-upstream.md, on a
branch in its own worktree (`git rebase --update-refs origin/tomita`), backup tag
`backup/main-pre-rebase-2026-11-26`.

## Conflicts, by strand

Only strand **05-tkabs**, in `zyngui/zynthian_gui_pated_notes.py`; no strand-01 commit was
upstream, nothing dropped.

| Commit | Conflict | Resolution |
|---|---|---|
| Pattern editor: keymaps and note tables in zyngui/zynthian_pated_data.py | upstream's 7f25f8f3 split the Tk `load_keymap()` into `load_keymap()` (the keymap's screen state, `self.keymap_state`) and `build_keymap()`; the commit moves the keymap code into `zynthian_pated_data.load_keymap()` | the module gets upstream's split too: `build_keymap(map_info, scale, tonic)` (the map from an already looked-up custom keymap) and `keymap_state(name, keymap, scale)`; `load_keymap(chain_manager, channel, …)` stays for the Qt pattern editor. The Tk `load_keymap()` looks the custom keymap up through its own `get_custom_keymap()` (upstream's hook, which upstream's tests/unit/test_view_state.py replaces) and sets `self.keymap_state` |
| Pattern editor: chord intervals in zynthian_pated_data; …: per-note parameter texts and settings in zynthian_pated_data | the import line of the module (follow-up of the resolution above) | their import, with `build_keymap, keymap_state` for `load_keymap` |

The load_keymap choice: the Tk screen calls its own `get_custom_keymap()` instead of the module
function with `self.zyngui.chain_manager`, so upstream's test double (a screen without `zyngui`,
`get_custom_keymap` replaced) works unchanged and upstream's hook stays; the test isn't changed.

## Upstream changes lost in moved code

`refactor_report.py --lost-upstream 3dbab929d e2f423d33 <top>`: 0 lost hunks, 0 reverted;
one hunk "partly lost" (7f25f8f3 in pated_notes): its one lost line is `name =
self.build_keymap()`, which is now the `build_keymap(map_info, …)` call; its other lines are in
`zynthian_pated_data.keymap_state`.

## Fixes for upstream's changes

| Strand | Commit | Why |
|---|---|---|
| 01 | fixup of "zynthian_gui: ENABLE_MIDI_LEARN_CC and MIDI_UNLEARN_NODE find the controller by processor id and symbol": "Params:" instead of "Keyword Args:" | upstream's test_cuia_docstrings.py (dd012ced) |
| 05 | CUIA list: VNC_START, VNC_STOP and SET_PATTERN_JSON from upstream | test_cuia_list.py: the list matches the Tk CUIAs and their categories |
| 07 | Qt UI: VNC_START, VNC_STOP and SET_PATTERN_JSON, as the Tk UI | both UIs offer the same CUIAs; VNC in a thread (systemctl) |
| 09 | test_vm.sh: py3-jsonschema for upstream's zynseq schema tests | cb79f1a7's tests skip without it |

## Checks

strand-check.sh: ok (547 commits on e2f423d33). Strand 01 has no Claude-Session lines; strands 01
and 02 apply directly on tomita e2f423d33. `--lost-upstream`: 0 lost hunks (above).

Test VM (`run all` at the top; `run default` at the tops of 01, 05, 07), 0 failed everywhere:

| Tree | Result |
|---|---|
| top, default | 1336 passed, 40 skipped, 29 xfailed |
| top, gui | 1338 passed, 38 skipped, 29 xfailed |
| top, native | 292 passed, 16 xfailed (the zynseq schema tests run: py3-jsonschema) |
| 01 top | 960 passed |
| 05 top | 1100 passed |
| 07 top | 1336 passed |

Qt UI in the compare VM 2242 (this tree's Python, and its libzynseq.so from the test VM's native
build: the package's library lacks upstream's `getPatternState`, which zynseq.py binds at start):
starts, "001-Parity Test" loads (Dexed, MiniOPL3, Fabla), the pattern editor shows Fabla's pattern
with its keymap (chromatic, named C rows). Afterwards the VM got main's code and the package's
library back (theme v4, Parity Test loaded). With the old package library, the rebased Python
fails at zynseq's start: the Qt and Tk packages must be built from this tree (native libraries
included) before devices get it.
