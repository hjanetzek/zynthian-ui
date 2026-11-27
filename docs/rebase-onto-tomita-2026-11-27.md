# Rebase of main onto origin/tomita 5b0b6966 (2026-11-27)

`main` 1adbb02ad (tomita e2f423d33 + 10 strands, 557 commits, plus 6 unplaced commits on top:
switch_ui.sh testing and the jam-zs3 work) rebased onto `origin/tomita` 5b0b69662: 19 upstream
commits (docs/upstream-tomita-changes-2026-11-27.md). Procedure: docs/rebasing-onto-upstream.md,
on the branch `rebase-tomita-2026-11-27` in its own worktree (`git rebase --update-refs
origin/tomita`), backup tag `backup/main-pre-rebase-2026-11-27`. No strand-01 commit was taken
upstream, nothing dropped (all 563 commits rebased); the 6 unplaced commits stay on top.

## Impact analysis (before the rebase)

Files of each upstream commit that our series also changes (`git diff --name-only e2f423d33 main`),
with our strands touching them, the expected trouble and what the Qt UI or the test VM needs.

| Upstream | Files we change too (our strands) | Expected | Qt UI / test VM |
|---|---|---|---|
| 899951fe, a76250fb, a8b68e46, 29198d95 zynthian-lv2-plugin skill | none (`.claude/skills/`) | clean | – |
| 4089478d #1851 (lv2:enabled bypass, one bypass per processor) | `zyngine/zynthian_engine_jalv.py` (01, 03, 06, 07) | 06's port-description cache near the changed loop | none (the Qt UI reads `bypass_zctrl`) |
| 00d766ba debugpy | none (`zynthian_main.py` is Tk's) | clean | optional: the same for `zynthian_qt_main.py` |
| 98ccefc7, 81598b1c, d2128246, 27b65fd2 update progress view | `zyngui/zynthian_gui.py` (01, 02, 03, 05, 06, 07), `zyngui/zynthian_gui_admin.py` (03, 05) | imports and screen table next to 05's changes | the Qt UI has no "Update Software" (Nura updates are packages): no progress screen needed; `zynthian_gui_update_progress` imports tkinter (Tk only) |
| 5f4a18c4, c391277b LV2 scan speed-ups | `zyngine/zynthian_lv2.py` (01, 03, 06) | 06's lazy lilv (world on first use, rdflib only for TTL parsing) at the rdflib import and the preset functions; 03's config paths next to the new cache file | none |
| e5ea8288, 3ff19459 native audio→MIDI (engine AM, id -5, `zynlibs/zynaudio2midi`, SCREEN_AUDIO2MIDI) | `zynautoconnect` (01, 03, 04, 06), chain and state manager (01, 03, 04, 05, 06, 09), `zynthian_gui.py`, `zynthian_gui_config.py`, `zynthian_gui_control.py`, `zynthian_gui_midi_config.py` (05 moves its list and actions into `zyngui/zynthian_midi_config_data.py`), `zynthian_state_schema.py` | the MIDI config changes are **lost in moved code** unless ported into `zynthian_midi_config_data`; `LIB_PATH` hard-codes `/zynthian/zynthian-ui/zynlibs/...` (03: `zynthian_paths`) | new CUIA SCREEN_AUDIO2MIDI: CUIA list (05), Qt UI (07: chain control with the global processor, like tempo / alsa_mixer); the Qt MIDI devices list gets the row through the module; test VM: `libzynaudio2midi.so` in the native build (tests/native/build_native.sh, upstream's change) |
| f1c9be06 keymap_state on demand | `zyngui/zynthian_gui_pated_notes.py` (01, 05) | conflict with 05's keymap move (`self.keymap_state` from `zynthian_pated_data.keymap_state`); upstream's own tests still use `keymap_state` | the Qt pattern editor uses the module's `load_keymap` / `keymap_state`: unchanged |
| 876d5e2d aubionotes removed, legacy snapshots converted | `zynautoconnect`, `zynthian_legacy_snapshot.py` (01), state manager, `zynthian_gui_config.py`, `zynthian_gui_midi_config.py` (05), `tests/integration/test_legacy_snapshot.py` (01) | `zynthian_midi_config_data` still lists aubionotes and calls `sm.start_aubionotes` (removed) | no aubio code in `zynqt/` |
| 45aa64ae #1849 | `zyngine/zynthian_engine.py` (01, 03, 06) | small | none |
| 5b0b6966 #1847 (audio file widget: audio-typed path controller) | `zyngui/zynthian_widget_audio_file.py` (05 moves the lookup into `zyngui/zynthian_audio_file_data.py`) | **lost in moved code** unless ported into `zynthian_audio_file_data` | the Qt audio file view uses the module |

New dependencies for the test VM: none beyond the native build of `zynlibs/zynaudio2midi` (jack,
libm); debugpy is optional. Packaging (nura-builds, not here): the zynthian-ui recipes must build
`zynaudio2midi` (their lib loop lists zynsmf zynseq zynaudioplayer zynmixer zynclippy only);
`desktop/install.sh` now installs `libzynaudio2midi.so` and fails without it.

## Conflicts, by strand

| Strand | Commit | Conflict | Resolution |
|---|---|---|---|
| 01 | zynthian_gui: CHAIN_OPTIONS checks the shown screen, not the left-over special processor | upstream e5ea8288 added `is_shown_audio2midi()` to the same check | `self.current_screen in ("alsa_mixer", "audio2midi")` |
| 01 | zyngine: break the state manager <-> chain manager / legacy snapshot import cycle | no git conflict, found by the tests: upstream 876d5e2d uses `zynthian_state_manager.AUDIO2MIDI_UID` in `version_5()`, the commit removes that module import (NameError in four test_legacy_snapshot tests) | fixup: `audio2midi_uid()`, imported on use like `main_mixbus_id()` |
| 03 | Make all directories configurable through environment variables | upstream 5f4a18c4's `LV2_PLUGIN_INFO_CACHE_FILE` next to the config file paths | all from `zynthian_paths`, the new cache file too |
| 03 | Add desktop mode (ZYNTHIAN_DESKTOP=1) | upstream 876d5e2d removed `start/stop_aubionotes`, which the commit marks `@system_service` | upstream's side; the in-process audio→MIDI converter is no system service |
| 05 | MIDI config, audio out screens: lists and actions as modules | upstream e5ea8288 (converter row, its port, toggle) and 876d5e2d (aubionotes removed) changed the Tk list and actions the commit moves | the Tk file as the commit has it (module calls; upstream's Tk-only bold select and options for the converter stay); the module gets upstream's list changes (`append_audio2midi`, the converter's port, no aubio rows or service) and the toggle (the converter's row without chain: `sm.toggle_audio2midi()`) |
| 05 | Admin screen: toggles in zyngui/zynthian_admin_settings.py | the import next to upstream 98ccefc7's `update_running` | both imports |
| 05 | Pattern editor: keymaps and note tables in zyngui/zynthian_pated_data.py | upstream f1c9be06 replaced `self.keymap_state` (set by `load_keymap`) with `self.keymap_name` and `get_keymap_state()` | as upstream: `load_keymap` sets `self.keymap_name` from the module's `build_keymap()`; `get_keymap_state()` returns the module's `keymap_state(self.keymap_name, self.keymap, getScale())` |
| 05 | Audio file widget: engine view parameters and waveform loading as a module | upstream 5b0b6966 (#1847) changed the path controller lookup the commit moves into `zynthian_audio_file_data.file_zctrl` | the commit's widget; the module gets `AUDIO_FILE_TYPES` and `find_audio_path_zctrl(processor)`, used by `file_zctrl` (Tk widget and Qt view) |
| 06 | zynthian_lv2: build the lilv world on first use, not at import; rdflib only for TTL parsing | upstream 5f4a18c4 moved the rdflib import into `get_info_from_ttl` too; c391277b removed `generate_presets_cache_workaround`; 5f4a18c4 filters `generate_all_presets_cache` by `is_plugin_supported()` | upstream's rdflib import (the commit's part is upstream's now); workaround dropped; `get_world()` with upstream's filter |

## Upstream changes lost in moved code

`refactor_report.py --lost-upstream e2f423d33 5b0b69662 <top>`: 0 reverted; 4 "lost" one-line
hunks, all deliberate rewrites of upstream's new lines, upstream's change is in each:

- 5f4a18c4 `LV2_PLUGIN_INFO_CACHE_FILE` with `os.environ.get('ZYNTHIAN_CONFIG_DIR')`: from
  `zynthian_paths.config_dir` (03);
- e5ea8288 `LIB_PATH = "/zynthian/zynthian-ui/zynlibs/..."`: `zynthian_paths.native_lib` (03);
- e5ea8288 `if self.is_shown_alsa_mixer() or self.is_shown_audio2midi():` in CHAIN_OPTIONS:
  `self.current_screen in ("alsa_mixer", "audio2midi")` (01);
- 876d5e2d `midi_capture.setdefault(zynthian_state_manager.AUDIO2MIDI_UID, aubio_cfg)` in the
  legacy snapshot converter: `audio2midi_uid()` (01, the import-cycle fixup above).

One "partly lost" (f1c9be06 `get_keymap_state`: its body is the module's `keymap_state`); the
"changed" hunks are the ports above (midi_config, audio_file, pated_notes, the audio2midi help
page). The legacy snapshot NameError wasn't reported before its fixup: the line stayed, the import
it needs went (the tests found it).

## Fixes for upstream's changes

| Strand | Commit | Why |
|---|---|---|
| 01 | tests: test_view_state: the keymap state from get_keymap_state() | upstream's own test still used `keymap_state` after f1c9be06 (fails on tomita); upstream candidate |
| 01 | fixup of the import-cycle commit (above) | 876d5e2d's `zynthian_state_manager.AUDIO2MIDI_UID` |
| 03 | audio2midi engine: native library and help page through zynthian_paths; desktop install | the converter on Nura (`ZYNTHIAN_LIB_DIR`, `ZYNTHIAN_HELP_DIR`); `desktop/install.sh` installs the library |
| 05 | CUIA list: SCREEN_AUDIO2MIDI from upstream | test_cuia_list.py |
| 05 | tests: upstream's audio to MIDI row and #1847 in the shared modules | regression tests of the two ports |
| 07 | Qt UI: SCREEN_AUDIO2MIDI and the audio to MIDI converter in the MIDI devices list, as the Tk UI | both UIs offer the same CUIAs; the converter's row: tap toggles, long press: controls, or its options while it runs (controls, audio inputs, port options) |

Not done (logged in zynthian-stuff ui-parity/issues.txt): an update progress screen in the Qt UI
(not needed on Nura), debugpy in `zynthian_qt_main.py`, the nura-builds recipes (zynaudio2midi).

## Checks

strand-check.sh up to `strand/10-docs`: ok (563 commits on 5b0b69662: the 557 rebased, 5 follow-ups, these notes). With the 6 unplaced
commits on top it reports "living docs with more than one commit: docs/upstream-candidates.md"
(the unplaced jam-zs3 upstream-candidates commit), as on main before the rebase. Strand 01 has no
Claude-Session lines; strands 01 and 02 apply directly on tomita 5b0b69662 (01: identical tree).

Test VM (port 2264; `run all` at the top, `run default` at the tops of 01, 03, 05, 06), 0 failed
everywhere (after the two fixes above; the first top run had 5 failures: the legacy snapshot
NameError and a fake in the new midi_config test):

| Tree | Result |
|---|---|
| top, default | 1481 passed, 40 skipped, 30 xfailed |
| top, gui | 1483 passed, 38 skipped, 30 xfailed |
| top, native | 338 passed, 17 xfailed (zynaudio2midi's native tests run) |
| 01 top | 1036 passed |
| 03 top | 1051 passed |
| 05 top | 1183 passed |
| 06 top | 1225 passed |

Qt UI in the compare VM 2242 (this tree's Python; the package's libraries are from 2026-11-26 and
have `getPatternState`; `libzynaudio2midi.so` from the test VM's native build, temporarily): starts,
"001-Parity Test" loads (Dexed, MiniOPL3, Fabla), the pattern editor shows Fabla's pattern with its
keymap (chromatic, named C rows); SCREEN_AUDIO2MIDI shows the converter's controls (onset, release,
mode, noise filter; Pitch bend page); MIDI Input Devices lists "Audio ➔ MIDI", a tap starts it (its
port row: ☒ ⇥ ♣), a long press shows its options, "Select audio inputs" its inputs (Input 1 on);
stopped again. "006-Tide" (factory, schema 5 with `AUBIONOTES_ENABLED`) loads without errors.
Afterwards the VM got main's code back, the temporary library removed, the MIDI profile line the
toggle wrote removed, "001-Parity Test" loaded.
