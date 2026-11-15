# Upstream tomita changes, 322e9079 → 7dbabb85 (seen 2026-11-15)

What changed in zynthian upstream `tomita` between our previous base (`322e9079`) and `origin/tomita` at `7dbabb85`, the base of the rebase described in `docs/rebase-onto-tomita-2026-11-15.md`. The range has 95 commits and touches 237 files (+8902/−4361). Most of the line count is formatting and tests.

The last column of each table says what a change means for our branch (Qt UI, desktop/Nura port, multi-zynthian).

## 1. MIDI binding rework (branch `1820/midi_binding`, PR #613)

The biggest functional change. It replaces "MIDI learn" in `zyngine/zynthian_chain_manager.py`.

| Change | Impact on our branch |
|---|---|
| One map `midi_cc_binding` with 32-bit keys `chain_id<<24 \| zmip<<16 \| chan<<8 \| cc`. It replaces `chain_midi_cc_binding` and `absolute_midi_cc_binding`. `chain_id` 0xff means a global binding. `zmip == ZMIP_STEP_INDEX` (key `\| 0xff000000`) is a step-sequencer **automation** binding. | Done (`ef92d73e`). |
| New API: `add_midi_binding`, `toggle_midi_binding`, `clear_midi_binding(proc, symbol)`, `clean_midi_binding(obj)`, `get_midi_binding_from_zctrl(...)` → `[key, "chain"\|"global"\|"automate"]`, `pack/unpack_midi_bind_key`, `enable/disable/toggle_automate_zctrl`, `get_automate_zctrls(chan)`, `get_spare_automate_cc`, `reassign_automate_cc`, `remove_unused_automate`. Removed: `add_midi_learn`, `get_midi_learn_from_zctrl`, `clean_midi_learn`, `remove_midi_learn`, `add_zynstep_midi_learn`, `get_zynstep_mapped_zctrl`. | Callers adapted (`ef92d73e`). |
| Chain learn is device-specific: it binds the input device the CC came from, plus the chain. "Learned MIDI Inputs" toggles devices. A learned controller is automatically enabled for automation. | Qt controller options now match Tk. |
| Controller options: an "Automate" toggle (asks before removing automation from patterns). The "ZynStep CC" entry is gone. | Done in Qt. |
| The controller shows `A:` when automated, `⏺` while relative CC mode is being learned. Colours: global = `color_ml`, chain with channel = `color_hl`. | Via `zynthian_midi_learn_data.binding()`. |
| `zctrl.midi_cc_mode` is saved/restored in snapshots (`zynthian_controller`, `zynthian_processor`). | Nothing to do. |
| zynseq: when recording MIDI, a learned CC is recorded as its automation CC. New `addLearnMapping`/`clearLearnMapping` in `zynseq.cpp`; `zynthian_gui_pated_base.update_learn_mapping()` fills the map when MIDI record is enabled. New zynseq.py helpers: `get_channel_patterns`, `get_cc_patterns`, `is_cc_used`, `move_cc`, `get_automated_patterns`, `remove_automated_patterns`. | **Open:** Qt pattern editor (no `update_learn_mapping` call; old CC model). |
| Pattern editor CC view (`zynthian_gui_pated_cc.py`): the automated parameters (`get_automate_zctrls`) are listed first, then the MIDI output CCs (all 128 if a chain on the channel has MIDI thru, otherwise only CC64). Interpolation display fixes. The last pattern editor used (notes/CC) is remembered (`pated_base.get_editor_screen`, CUIA screen `pated`). | **Open:** Qt pattern editor parity. |
| Snapshot schema **V6** (`zynthian_state_schema.py`). `midi_learn` keys are 24-bit hex (`ccccnn`: chain or ff, chan or ff, cc), stored per MIDI input device under `midi_capture`. The per-chain `midi_learn` is gone. `midi_profile_state` is documented (every `ZYNTHIAN_MIDI_*` variable). Internal MIDI learn is marked "not implemented". The legacy converter `version_5()` turns V5 chain bindings into per-device bindings (chain bindings are copied to every device). | Our snapshot code goes through the state manager, so nothing to do. Multi-zynthian snapshot sync uses the same state, so recheck remote-chain snapshots. |

## 2. Mixer: fader law and DPM (PR "1822/fader_law")

| Change | Impact on our branch |
|---|---|
| `mixer.c`: new fader law. The level is a **fader position** 0..1 (1.0 = +10 dB, unity at `FADER_UNITY` 0.75, no kink at 0 dB). New `levelToDb`/`dbToLevel` (Python `zynmixer.level_to_db/db_to_level`). New snapshots start at 0 dB = 0.75. Legacy snapshots are converted (`version_5`: linear gain → position). | The Qt fader shows the raw position. Any dB labels/ticks should use `level_to_db`. `MixerScreen.qml` (tk) draws the old fader scale. |
| DPM: `getDpm`/`getDpmHold` return an **inverted meter position** (0 = full scale, 1 = empty, linear in dB over the range) instead of dBFS. Per-strip hold counters, decay in dB/s. `setMeterConfig(range, decay, hold, fader headroom)` is called by the state manager. | **Fixed** for the Qt meters and the multi-zynthian meter stream (`b55d92f6`: `meter_fraction()`). Mixed-version multi-zynthian setups (old and new zynmixer) would show wrong remote meters. |
| New config (`zynthian_gui_config.get_env_float`): `ZYNTHIAN_MIXER_DPM_RANGE_DB` (72), `..._DPM_SMALL_RANGE_DB` (40, launcher), `..._DPM_ZERO_DB` (−18, yellow above), `..._DPM_DECAY_DB_PER_S` (30), `..._DPM_HOLD_S` (2), `ZYNTHIAN_MIXER_FADER_ZERO_DB` (−10). Red above −2 dB (`DPM_OVER_DB`), with the over indication held for 4 s. | Qt `Meter.qml` uses the default thresholds (2/72, 18/72). **Open:** read the config values, the small range in launcher mode, the over-hold, the tk skin colours (`MixerScreen.qml` (tk), `TopBar.qml` (tk), still 0.8/0.94). |
| `zynthian_gui_dpm.py` rewritten (Tcl scripts batched via `run_script`, `db_to_norm`). The status bar DPM is drawn in the main thread (`refresh_dpm`). | Tk only. |
| The power-save check uses the new hold position (`hold_limit` from `audio_power_threshold`). | Nothing to do. |
| The mixer UI uses the mixer controllers (`zctrl`) for UI/lib sync. A new chain resets its mixer processor at 0 dB. | Check that the Qt mixer sets levels through zctrls (it did). |

## 3. New features

| Change | Impact on our branch |
|---|---|
| **Drawbar widget** (`zyngui/zynthian_widget_drawbar.py`, `zynthian_widget_setbfree.py`). Controllers have a `drawbar` attribute, from the LV2 `parameters#drawbar` designation (`zynthian_lv2`) or set by setBfree. Supports dragging, and engines with fewer drawbars. A Calf Organ entry is added. `zynthian_engine_setbfree` sets `custom_gui_fpath` from `ZYNTHIAN_UI_DIR`. | `screen_type()` returns `"drawbar"`. **Open:** no Qt widget (the controllers are shown). |
| **Websocket API** in `zynthian_gui.py` (`websocket_server`, port `zynconf.ServerPort['websocket']`). Input: `{"cuia": ..., "args": ...}`, `{"key": "down"\|"up", "code": ...}` (injected with `xdotool`), `{"midi": "note_on"\|"note_off"\|...}` on the active chain's channel. Output: `{"wsled_state": ...}` on LED changes (`wsleds_base.wsled_state_changed`). | **Open:** the Qt UI (`zynqt/ui.py`) has no websocket server. Webconf's virtual keypad/LEDs won't work with it. `xdotool` is X11 only. Our desktop/Wayland sessions need another key path. |
| OSC `/MIXER/` rewritten (`osc_mixer_control`, `OSC_MIXER_PARAMS`, through `chain_manager.get_mixer_zctrl`). This fixes the broken namespace in our candidates list. | Check the Qt OSC handler if it copied the old code. |
| ctrldev base: `get_chain_mixer_chan()`, `get_chain_zctrl()`. Many drivers (APC40, MPK249, Launchkey, SMK25, ...) use mixer zctrls. Sinco driver mixer fixes. | Nothing to do. |
| Internet radio: the `volume` controller was removed (too laggy). | Qt controller pages follow the engine. |
| Transport clock source fix. Fixes for TTS-triggered crashes. | — |

## 4. Code quality (most of the diff, little behaviour)

- Formatting: CRLF → LF, tabs, trailing whitespace, `is None`/`is True`, no mutable default arguments, fewer function-level imports (e.g. `lib_zyncore_init` at module level in `zynthian_gui_config`), logging following the coding guidelines (`print` → `logging`). `#!/usr/bin/python3` and `# -*- coding -*-` headers removed. Author e-mails changed to `@zynthian.org`.
- `os.system`/`shell=True` replaced by `subprocess.run`/`check_output` with argument lists across the codebase (admin, state manager, config, engines, jalv). `eval()` replaced by `getattr()`.
- Rename: `zynthian_widget_GxGraphicEQ.py` → `zynthian_widget_gxgraphiceq.py` (and the class name). Our `zynthian_widget_data.PLUGIN_WIDGETS` uses the name `"GxGraphicEQ"` only as a key, so it still works.
- `zynthian_gui_mixer`: `id` no longer shadows the built-in.
- Build type of zynseq is no longer hardcoded.

## 5. Tests and CI (new)

- `tests/`: a hermetic pytest suite with markers `unit`, `integration`, `gui` (xvfb), `jack`, `native` (real .so), `hardware`; fakes for zyncore and the native libs; architecture tests (layering, CLI scripts); native tests for zynmidirouter, zynseq, zynsmf, zynaudioplayer with a shared JACK harness. The old `zynlibs/*/unit_tests.py` and `zynlibs/zynseq/tests` were moved or removed.
- `pyproject.toml` (pytest options, ruff with only syntax errors/undefined names), `requirements-dev.txt`, `.github/workflows/tests.yml` (ruff, native build, `xvfb-run pytest`), `run_tests.sh`.
- On our branch: 363 passed. `test_tk_root_opens_and_processes_events` fails locally on plain upstream too (environment). Worth adding tests for our shared `*_data.py` modules and the Qt models in the same style.

## 6. Our upstream candidates vs. this range

Checked against `docs/upstream-candidates.md` (2026-11-15):

- **None of our "ready"/"split" fixes was applied upstream.** `git cherry` finds no patch-identical commit. The functions involved are unchanged apart from formatting. This covers: legacy converter (90ba6272), autoconnect gone-port name (85dbc36e), zynmixer deadlock under pipewire-jack (0a8e28b2), CPU colour > 100 % (50d7d86a), jack_capture from PATH (fa23e789), list preset ids (effe2a4d), exit crash / `lib_stop` (be63e13b), PFL odd ports (6de94330), PipeWire hardware ports and main output (e6db61fe, 5b0beedc), zynseq `uint8_t`/`bool` restypes (6a073863, 35d77428), `osffset` typo (1b575e6a), OS path remap (454d2d02), Organelle path (3237ba5a), save pattern (1f883200), SMF import (f7feec7f), X-Y offset (116b17e0), ALSA mixer startup (92e6ebb1), LV2 UI type (47389d82), LS SFZ → sfizz (c58df11d), Aeolus read-only data (c1ba3f2d). The zyncoder MCP23017 fix (f55b0ca) is in another repo and was not checked.
- **Open bugs still present upstream:** among others, `CHANNEL_CHARS` comma, `getPatternZoom` restype, `allow_preset_preload` not called, `zynthian_headless.py` import, `remove_slow_update_callback`, zynmixer.py calling missing C functions (`togglePfl`, `getAllMono`, `addOscClient`, `removeOscClient`), `cuia_enable_midi_learn_cc` and `cuia_midi_unlearn_node` signatures (the latter now calls `clear_midi_binding([..])`), `START_MIDI_PLAY`, the tonic `% 12`, the grid drag parentheses, `delete_bank`, `getMidiLearnSequence`, and the midiproc example syntax error.
- **Fixed upstream independently:** the OSC `/MIXER/` namespace (`osc_mixer_control`). `add_osc_client` still calls the missing `addOscClient`.
- **New upstream bug noticed:** `zyngine/ctrldev/zynthian_ctrldev_launchpad_pro_mk2.py:629` calls `chain_manager.get_filtered_chain_by_index` (the method is on the ctrldev base class).
