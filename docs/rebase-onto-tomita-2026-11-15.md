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

## Upstream changes lost in moved code (found 2026-11-18)

Two upstream changes were lost without a conflict, not in this rebase but in the earlier one main came from (about 2026-11-07; both upstream commits are older than this rebase's base 322e9079). An earlier attempt, branch `nura-tomita` (2026-11-05, base 500e5cd1, its notes in `git show 5a147281:docs/rebase-tomita.md`), had ported both into the shared modules, but main wasn't built from it. They were lost because our commits moved the code
they changed out of the Tk files into shared modules (procedure and check: docs/rebasing-onto-upstream.md):

| Upstream change | Our commit (written on an older base) | What happened |
|---|---|---|
| efb40f48 (2026-10-25) curves in the envelope widget | 14442743 "Qt UI: envelope and filter widgets on controller pages" (moves the geometry to `zyngui/zynthian_widget_data.py`) | The replayed commit deleted the widget's drawing code including `build_curve_table()` / `curve_points()`; the module kept straight segments. |
| be13d828 (2026-11-03) routing to "ALL MIDI-CHAN" chains (`midi_chan == 0xffff`) | 3b84a84a "Chain routing in the Qt UI; MIDI config and audio out lists shared" (moves the lists to `zyngui/zynthian_midi_config_data.py`) | The Tk screen's condition with upstream's `or chain.midi_chan == 0xffff` was deleted; the module kept `midi_chan < 16`. |

Found by the screenshot comparison and code review of the upstream extraction branch `tk-ui-abstraction`; fixed on main by branch `fix-regressions` (e8292224 MIDI output list, d14c672e envelope curves, tests 824bb69b).

### Review of all suspects (2026-11-18, branch `fix-regressions`)

Ranges checked against the branch: upstream `d6ed3592..14c9ddad` (from our first base, vangelis
d6ed3592 of 2026-11-02, to main's current base on tomita; this includes the tomita-only commits older
than d6ed3592) with `zynthian-stuff/tools/refactor-report/refactor_report.py --lost-upstream` (final
report: `lost-upstream-fix-regressions-5e4d8917.txt` there), `lostcheck.sh`, a blame of every
upstream line our diff removes, and a comparison of main's shared modules and Tk screens with the
ones `tk-ui-abstraction` extracted from current upstream (differences: only the port's additions).
The 10 upstream commits after 14c9ddad (websocket feedback, CUIA categories, ...) aren't in main's
base yet: not lost, pending the next rebase. Vangelis after d6ed3592 has one commit not in tomita,
3d28ae56 "MIDI Player" title, the same change as tomita's 14c9ddad.

| Upstream change | Verdict | Evidence / fix |
|---|---|---|
| efb40f48 envelope curves | **lost** (moved code) | fixed d14c672e: `zynthian_widget_data.envelope_geometry()`; Tk widget and Qt `EnvelopeView` draw it |
| be13d828, 8f58743a/0fbd308f ALL-channel chains in the MIDI output list | **lost** (moved code) | fixed e8292224: `zynthian_midi_config_data.midi_config_list()` |
| 6a149c4a/3f4d5937 `fader_overlay = None` in mixer strips | **lost in effect** (semantic conflict): upstream's init made our `has_mixer_widgets()` (`hasattr`) always true | fixed 344c3d08: tests `fader_overlay is not None` |
| 732e32b7 `zynthian_widget_gxgraphiceq` lowercase | **lost** on the Qt side: `plugin_widget()` takes the name from the file, `PLUGIN_WIDGETS` had "GxGraphicEQ" | fixed 4823566f (+ test: every widget in `lv2/` has a Qt view) |
| a1527c99 widgets as LV2 extension bundles in `lv2/` | **lost** in packaging: `lv2/` wasn't installed nor on LV2_PATH, so no LV2 plugin widget in either UI on Nura | fixed 5e4d8917: `desktop/install.sh`, `zynthian_desktop_env.sh`, `sync_ui.sh` |
| 14c9ddad / 3d28ae56 "MIDI Player" title | **not followed** by the Qt screen | fixed 55c63a7c |
| ac618562 CC view: assigned CCs only, bold knob 1 "show all"; ff02526e CC names | changed again upstream (11-15 CC view rework); main's Tk `zynthian_gui_pated_cc.py` is upstream's; the Qt editor has both (`cc_show_all`, CC names in `tkTitle`) | — (the Qt CC list model: open follow-up 3) |
| 9511465f learn-mode indicator, 172d6741/494db0f2/150f48b7 binding display and unlearn texts | adapted: `zynthian_midi_learn_data.binding()` / `unlearn_label()` (Tk controller and control screen, Qt control) | — |
| 67cc6aa7 `remove_unused_automate` | adapted ("Adapt to upstream's MIDI binding rework": extra `automated` argument) | — |
| ee07890c drawbar `screen_type` | adapted: `zynthian_widget_data.screen_type()` returns "drawbar" (no Qt widget: follow-up 4) | — |
| c0d83cac `list(self.drivers.values())` | adapted: `list(drivers) + list(hid_drivers)` | — |
| 4b0dbe47 legacy snapshot `mixer_ids` | adapted: `main_mixbus_id()` (import cycle broken) | — |
| 500e5cd1, a69c4289 `patch_jack_library` | replaced on purpose by our alias store (2079cb4f); upstream later dropped the fallbacks 04882b7f added in autoconnect too | — |
| 04882b7f `RBPI_VERSION` | adapted: no version counts as RPi4 class (desktop) | — |
| 6d8ca287 LV2 hot reload, a1527c99 `ZYNGUI_BUILTIN_WIDGETS_DIR` | adapted: lazy lilv world, `zynthian_paths.ui_dir` | — |
| 0aab7eb3 `check_output(update_zynthian_sys.sh)`, powersave | adapted: `zynthian_paths.sys_dir`; moved, same calls | — |
| 7be0ece9 remember the last pattern editor | kept in Tk (`show_screen("pated")`, `get_editor_screen()`); Qt has one editor screen whose `cc_mode` persists | — |
| 8f8213af cycle xfails in `test_imports` | adapted: main broke the cycle | — |
| c31d5dcd, 82071c48, 63ab84b1, cfa5ddba, a9105074, 4fe36269, f10309d9 | whitespace / comments / tests moved to `tests/native` / schema doc (changed again upstream) | — |

Not an upstream change but noted in the comparison: `zynthian_snapshot_files.bank_list()/snapshot_list()`
number rows by position (`len(rows)`), where the Tk screen counted only some rows; the selected row
after a load is the loaded snapshot in both when a "Save" row is shown, upstream's is off by one
without it. Left as is on main (`tk-ui-abstraction` keeps upstream's counting).

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
