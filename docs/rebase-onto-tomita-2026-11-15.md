# Rebase of tomita-rb-next onto origin/tomita (2026-11-15)

State of the rebase, how it was done, and what still needs work. For the next agent working on this branch.

## Summary

- `tomita-rb-next` was rebased onto `origin/tomita` at `7dbabb85`. Before the rebase, the merge base was `322e9079`, and upstream had 95 new commits: a large cleanup (whitespace, CRLF, imports, `subprocess.run` instead of `os.system`), MIDI binding, fader/DPM, the drawbar widget and a pytest suite.
- All 348 branch commits applied. One commit was added on top: `ef92d73e` "Adapt to upstream's MIDI binding rework (rebase onto tomita)".
- A second fix commit, `b55d92f6` "Qt mixer meters: zynmixer DPM values are meter positions now": upstream's `getDpm`/`getDpmHold` return an inverted meter position instead of dBFS, so the Qt meters (and the meters remote zynthians send) showed almost full. See `docs/upstream-tomita-changes-2026-11-15.md` for all upstream changes in the range.
- The pre-rebase branch is kept as `tomita-rb-next-backup`. Compare with `git diff tomita-rb-next-backup tomita-rb-next`.
- **Not pushed.** Publishing needs a force push of `tomita-rb-next`. The user has to OK it, and CI must not be running (see memory: no push during CI).
- The repo config now has `rerere.enabled=true` and `merge.conflictStyle=zdiff3`.

## Conflicts and how they were resolved

| Commit (original) | File | Resolution |
|---|---|---|
| 1d2b155c autoconnect: keep port aliases locally | `zynautoconnect/zynthian_autoconnect.py` | Ours. Upstream's `patch_jack_library()` is replaced by our local alias store. |
| ede9c3fc directories via env vars | `zynconf/zynthian_config.py` | `check_output([zynthian_paths.sys_dir + ".../update_zynthian_sys.sh"])` (upstream's list form + our path). |
| 1a554d6c desktop mode | `zynconf/zynthian_config.py`, `zyngine/zynthian_state_manager.py` | Desktop-mode guards kept, wrapped around upstream's list-form `check_output` (`systemctl`, `powersave_control.sh`). |
| 55403426 zynmixer invalid free / stale buffers | `zynlibs/zynmixer/mixer.c` | Both: upstream's `updateDpmTiming()` + our `MAX_PERIOD_FRAMES` fixed buffers. `onJackBuffersize` only calls `updateDpmTiming()`. Compiles with and without `-DMIXBUS`. |
| 50ddf333 native libs from ZYNTHIAN_LIB_DIR | `zynlibs/zynsmf/zynsmf.py` | Both imports. |
| 8a1c33f2 desktop: hide uninstalled engines | `zyngine/zynthian_chain_manager.py` | Both: upstream's `CC_NAMES`/`zynthian_midi_output_cc_binding` + our `engine2program`. |
| f6168bbc LEDs after screen change | `zyngui/zynthian_wsleds_base.py` | Both: upstream's `wsled_state_changed` + our `update_lock`. Upstream's "TODO: shadow of Tk update()" comment moved to `update()`. |
| 128585b0 Qt M1 (init_zyncore) | `zyngui/zynthian_gui_config.py` | Ours (`init_zyncore()`). The function-level `lib_zyncore_init` import was dropped because upstream imports it at module level. |
| 349b489e, 21851f37 Qt launcher | `zyngui/zynthian_gui_mixer.py` | Upstream's extended `zynthian_gui_dpm` import (`db_to_norm`, `DPM_*`, ...) + our `zynthian_launcher_data` imports. |
| 0c383f6d Qt envelope/filter widgets | `zyngui/zynthian_gui_control.py` | Ours (`widget_screen_type()`). Upstream's new **drawbar** type was added to `zyngui/zynthian_widget_data.screen_type()`. In `zynqt/screens/control.py`, `"drawbar"` maps to no widget (the Qt UI has no drawbar widget, so the controllers are shown). |
| 1e472c00 Qt plugin widgets | `zynqt/screens/control.py` | Both (the drawbar mapping above + plugin widget). |
| ed0fa55f Qt euclidseq widget | `zyngui/zynthian_widget_euclidseq.py` | Upstream's changes there were whitespace only. Took ours with trailing whitespace stripped. |
| 98be8991 MIDI learn shared module | `zyngui/zynthian_gui_control.py`, `zyngui/zynthian_gui_controller.py`, `zyngui/zynthian_midi_learn_data.py` | **Substantive**: see "MIDI binding" below. Tk behaviour is exactly upstream's. |
| c58df11d LS SFZ → sfizz | `zyngine/zynthian_legacy_snapshot.py` | Both: upstream's `version_5()` (V5→V6: binding keys, fader law) + our `linuxsampler_sfz_to_sfizz()`. |
| 90ba6272 oldest legacy formats | `zyngine/zynthian_legacy_snapshot.py` | Imports merged: `os`, `copy`, `ceil, log, log10`. |

## MIDI binding (upstream rework) and our adaptation

Upstream (branch `1820/midi_binding`) replaced MIDI learn with MIDI bindings in `zyngine/zynthian_chain_manager.py`:

- A key is 32 bits: `chain_id << 24 | zmip << 16 | chan << 8 | cc`. `chain_id` 0xff means a global binding. `zmip == ZMIP_STEP_INDEX` is a step-sequencer **automation** binding (key `| 0xff000000`).
- API: `add_midi_binding(zctrl, cc, chan, zmip, chain_id)`, `toggle_midi_binding`, `clear_midi_binding(proc, symbol)` (keeps automation if patterns use it), `clean_midi_binding(chain_id | proc | zctrl)`, `get_midi_binding_from_zctrl(zctrl, filter_chain, filter_global, filter_automate, max_results)`. The last one returns `[key, "chain"|"global"|"automate"]`. Also `pack/unpack_midi_bind_key`, `enable/disable/toggle_automate_zctrl`, `get_automate_zctrls(chan)`.
- Removed: `add_midi_learn`, `get_midi_learn_from_zctrl`, `clean_midi_learn`, `remove_midi_learn`, `add_zynstep_midi_learn`, `get_zynstep_mapped_zctrl`.
- Tk: chain learn now binds to the input device it was learned from (plus the chain). The controller options have an "Automate" toggle and "Learned MIDI Inputs" (toggle devices). The "ZynStep CC" entry is gone.

Our shared module `zyngui/zynthian_midi_learn_data.py` now provides:

- `binding(cm, zctrl)` → `(text, kind)`, kind `"abs"` (global), `"chain"` or `"automate"`. The text starts with `A:` if the controller is automated and with `⏺` while relative mode is being learned. `"abs"` was kept for the global kind because QML (`Controller.qml` (tk), `+classic/Controller.qml`) colours by it.
- `unlearn_label(cm, ml)`: the signature changed.
- `automate_cc(cm, zctrl)` replaces `zynstep_cc`.
- `automate_zctrl(cm, chan, cc)` replaces `get_zynstep_mapped_zctrl`.

Fix commit `ef92d73e` adapted the remaining callers:
- `zynthian_chain_manager.set_chain_remote`: saves the raw binding keys and restores them with `add_midi_binding`.
- `zynthian_engine_standin`: auto-learns the same way `zynthian_engine` does.
- Qt `control.py` (`_midi_cc` mirrors `zynthian_gui_control.midi_learn_bind`; `midi_unlearn_action`).
- Qt `controller_options.py` (Automate, Learned MIDI Inputs, Unlearn, as Tk).
- Qt `chain_options.py`, `processor_options.py`, `ui.py` CUIA unlearn handlers.
- Qt `pattern_editor.py`.

## Verification done

- `uvx ruff check .`: clean.
- pytest (`xvfb-run -a python -m pytest`, venv from `requirements-dev.txt`): 363 passed, 186 skipped, 1 failed. The failure is `tests/gui/test_tk_infrastructure.py::test_tk_root_opens_and_processes_events`, which fails identically on plain `origin/tomita`, so it comes from the test environment.
- Static scan: no calls to chain-manager methods that don't exist, except upstream's own (below).
- `mixer.c` builds both variants. The ctypes names used from Python are exported, except `addOscClient`, `removeOscClient`, `getAllMono` and `togglePfl`, which are also missing on `origin/tomita`.
- **Not done:** running the Tk or Qt UI. The MIDI learn changes need a device test: chain/global learn, Automate toggle, Learned MIDI Inputs, unlearn, a remote chain move keeping bindings, and the Qt pattern editor CC titles.

## Open follow-ups

1. **Device test** of the MIDI learn changes above (QEMU VM or Duet; see memories).
2. **Qt mixer meters/fader**: the meter values are converted correctly since `b55d92f6` (`meter_fraction`), and `Meter.qml` colours use the default 72 dB thresholds. Still open: upstream now configures the meters and fader through `set_meter_config` (from the state manager), with `dpm_range_db` (72 dB), `dpm_small_range_db` (launcher), and a fader law with unity at 75% of the travel (`fader_zero_db`; `zynmixer.level_to_db` / `db_to_level`). The Qt meters and any dB labels should follow `zyngui/zynthian_gui_dpm.py` / `zynthian_gui_mixer.py`.
3. **Qt pattern editor CC view**: upstream's `zyngui/zynthian_gui_pated_cc.py` now lists the automated parameters first, then the MIDI output CCs (`build_avail_entries`, `cc_output`). The Qt `pattern_editor.py` still has the old "CC number + mapped controller" model.
4. **Qt drawbar widget** (upstream `zynthian_widget_drawbar.py`, setBfree and LV2 organs). Qt currently shows the controllers instead.
5. **Upstream bugs seen, not fixed** (candidates for the upstream log):
   - `zyngui/zynthian_gui.py` `cuia_midi_unlearn_node` calls `clear_midi_binding([params[0], params[1]])`, but the signature is `(proc, symbol)`. The Qt version in `zynqt/ui.py` does it right.
   - `zyngine/ctrldev/zynthian_ctrldev_launchpad_pro_mk2.py:629` calls `chain_manager.get_filtered_chain_by_index`, which only exists on the ctrldev base class.
6. Commit messages of the rebased commits are unchanged. `98be8991`'s message still mentions "the step sequencer CC"; its code now uses automation.
7. **Qt websocket server**: upstream's Tk UI serves a websocket API (CUIA, keys via xdotool, MIDI notes, LED state). The Qt UI doesn't. See `docs/upstream-tomita-changes-2026-11-15.md` §3.
8. **Qt pattern editor MIDI record**: upstream maps learned CCs to automation CCs while recording (`update_learn_mapping`, `addLearnMapping`).
