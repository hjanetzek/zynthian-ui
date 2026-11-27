# Rebase of main onto origin/tomita 26c42c46 (2026-11-27, second one)

`main` db82bc9f8 (tomita 5b0b69662 + 10 strands, 563 commits, plus 13 unplaced commits on top: the
zs3/dbm work with its upstream-candidates commit, switch_ui.sh testing, tools/zynctl.sh and 6 Qt
widget-shim / help commits) rebased onto `origin/tomita` 26c42c460: 8 upstream commits
(docs/upstream-tomita-changes-2026-11-27b.md). Basis: docs/rebase-onto-tomita-2026-11-27.md (the
rebase onto 5b0b6966 the same morning). Procedure: docs/rebasing-onto-upstream.md, on the branch
`rebase-tomita-2026-11-27b` in its own worktree (`git rebase --update-refs origin/tomita`), backup
tag `backup/main-pre-rebase-2026-11-27b` = db82bc9f8. Nothing was taken upstream, nothing dropped
(all 576 commits rebased); the unplaced commits stay on top in their order, with one new commit
after them (the Qt help port, below).

## Impact analysis (before the rebase)

Files of each upstream commit that our series also changes (`git diff --name-only 5b0b69662 main`),
the strands touching them, the expected trouble and what the Qt UI or the test VM needs.

| Upstream | Files we change too (our strands) | Expected | Qt UI / test VM |
|---|---|---|---|
| 35afa50c clip launcher decimal BPM | `zyngine/zynthian_engine_clippy.py` (03) | clean (one regex) | none |
| 34b22105 #1854 two audio→MIDI channels, converter always running, outputs routed like devices | `zynautoconnect` (01, 03, 04, 06), chain manager (01, 03, 05, 06), state manager (01, 03, 04, 05, 09), `zynthian_engine_audio2midi.py` (03: `LIB_PATH`, help dir), `zynthian_legacy_snapshot.py` and its test (01), `zynthian_gui.py` (01, 02, 03, 05, 06, 07), `zynthian_gui_config.py` (02, 03, 05), `zynthian_gui_midi_config.py` (03, 05: list and route action moved into `zynthian_midi_config_data`), `zynthian_gui_selector.py` (02), `zynthian_state_schema.py` (05) | conflicts at 03's `LIB_PATH`, 01's vanished-device log line, 04's HID driver states in the MIDI capture state; the MIDI config changes **lost in moved code** unless ported into `zynthian_midi_config_data` (yesterday's port of the converter row and toggle now wrong); our module tests of the old row fail | the Qt UI must follow: no converter row/toggle, outputs as devices, `SCREEN_AUDIO2MIDI` with a channel, no "Select audio inputs" (Qt `Audio2MidiInputs`), controls of one channel; test VM: the native build of the changed library (same dependencies) |
| f870d820 zynvoice update progress | `zyngine/zynthian_tts.py` (03) | clean | none (no Qt update view) |
| 9f5a87c3 restored MIDI inputs: the chain's own router output | state manager, `tests/integration/test_state_manager.py` (01, 03, 05) | test file conflicts next to 01's snapshot merge test and 03's OSC status test; `import re` next to 03's `zynthian_paths` import | none (state manager, both UIs); a merged snapshot in the Qt VM |
| acee218e audio→MIDI controls per channel, input routing | `zynthian_engine_audio2midi.py` (03), state manager, `zynthian_gui_midi_config.py` (05) | as 34b22105 (`audio2midi_default_input(output)` in the moved route action) | as 34b22105 |
| 7b6fbaa2 #1694 RLock screen lock | `zyngui/zynthian_gui.py` | 05's websocket mixin moved the `WebsocketServer` import from the changed import line | none (Qt has its own screen switching); 01's screen history test builds a bare zynthian_gui with a plain Lock |
| 35fdbbb2 #1687 switches in power save | `zyngui/zynthian_gui.py` | clean (the zynswitch loop is Tk's) | the Qt CUIA thread needs the same |
| 26c42c46 #1779 help page candidates | `zynthian_gui.py`, `zynthian_gui_base.py` (02, 03), `zynthian_gui_chain_control.py`, `zynthian_gui_selector.py`, `zynthian_gui_selector_grid.py` (02), `zynthian_gui_control.py` (01, 02, 03, 05), `zynthian_gui_bank.py` | clean expected (none of our commits changes `show_help` / `get_help_fpath`) | the Qt help lookup (`_help_topic`, in 07 and extended by the unplaced widget-help commits) should offer the same candidates |

New dependencies: none (zynaudio2midi has the same sources list and libraries: jack, libm). The
nura-builds recipes need nothing new beyond yesterday's open item (build zynaudio2midi at all).

## Conflicts, by strand

| Strand | Commit | Conflict | Resolution |
|---|---|---|---|
| 01 | Snapshot load: a vanished MIDI device no longer fails it; busy cleared on errors | upstream 34b22105 added `is_audio2midi_zmip` / `forget_audio2midi_port` after the disconnect log line the commit changes | both: the commit's `_port_name()` log line and upstream's two lines |
| 01 | Snapshot merge: map the chain controllers' processor ids | its test next to upstream 9f5a87c3's two tests in `test_state_manager.py` | all three tests |
| 03 | Make all directories configurable through environment variables | the `zynthian_paths` import next to upstream 9f5a87c3's `import re` | both imports |
| 03 | OSC status query /STATUS/BUSY | its test next to upstream 9f5a87c3's tests | both |
| 03 | audio2midi engine: native library and help page through zynthian_paths; desktop install | upstream 34b22105 / acee218e: the `zynautoconnect` import and the two channels' constants (JACK ports comment, `NUM_OUTPUTS`, `AUDIO_IN_SYMBOLS`, `DETECTION_SYMBOLS`) next to `LIB_PATH` | both imports; `LIB_PATH` from `zynthian_paths` with upstream's constants |
| 04 | ctrldev manager: HID drivers, loaded without a MIDI port | `get_midi_capture_state`: the HID drivers' states next to upstream 34b22105's converter routes (`audio2midi_routes`) | both blocks |
| 05 | MIDI config, audio out screens: lists and actions as modules | upstream 34b22105 / acee218e changed the Tk list and route action the commit moves (both outputs as ports, no converter row or toggle; routing an output: `audio2midi_default_input(output)`, `update_audio2midi_outputs()`), the Tk-only parts too (bold select and the controls option: `cuia_screen_audio2midi` with the channel; options in `get_options(idev)`; `audio2midi_inputs` removed) | the Tk file as the commit has it with upstream's Tk-only changes; the module gets the list changes (outputs in order, `append_audio2midi` gone) and the route action |
| 05 | Audio input list, ALSA input controls, MIDI device drivers as module functions | the device options moved into upstream's `get_options()` | the driver options through `device_drivers()` / `driver_description()` in `get_options()` |
| 05 | zyngui: websocket server and feedback streams in a toolkit-independent mixin | the import line next to upstream 7b6fbaa2's `RLock` | `from threading import Thread, Lock, RLock, Event`, `WebsocketServer` stays in the mixin |

## Upstream changes lost in moved code

`refactor_report.py --lost-upstream 5b0b69662 26c42c460 <top>`: 0 lost, 0 partly lost, 0 reverted;
2 "changed" hunks, both the port above (34b22105 / acee218e's route toggle in
`zynthian_gui_midi_config.select_action`, now `zynthian_midi_config_data.midi_config_action` with
`sm` for `self.zyngui.state_manager`), 3 "arrived" (the list changes found unchanged in the module).

## Fixes and follow-ups for upstream's changes

| Strand | Commit | Why |
|---|---|---|
| 01 | fixup of "zynthian_gui: an options list shown again doesn't end the screen history at an older one" | its test built zynthian_gui with a plain `threading.Lock`; since 7b6fbaa2 `close_screen` holds the lock while it shows the previous screen: deadlock (the test run hung). An RLock as zynthian_gui's |
| 05 | fixups of "tests: upstream's audio to MIDI row and #1847 in the shared modules" | the module tests of the old converter row and toggle replaced: both outputs as ports (no toggle row, no aubio rows), a tap in the device list: options; routing an output: its channel's default input and the active outputs; other devices leave the converter alone |
| 07 | Qt UI: the audio to MIDI converter's two outputs as MIDI devices, as upstream's Tk UI | the Qt devices list: tap on an output: its options, long press: its channel's controls; the options offer the controls (no "Select audio inputs", `Audio2MidiInputs` removed); `cuia_screen_audio2midi(params)` sets the channel as zynthian_gui. Test `test_qt_audio2midi_devices.py` |
| 07 | Qt UI: a switch pressed in power save only wakes the UI (short press ignored), as upstream #1687 | the Qt CUIA thread acted on a short press that woke the screen; tests in `test_qt_cuia_thread.py` |
| on top (unplaced) | Qt help: the candidate pages of upstream #1779 | `_help_topic`: the views sharing chain control (tempo, Audio Levels, audio player, audio→MIDI) their own page, then the processor's (widget page, `<name>.html` with spaces as underscores), then `chain_control.html`; the bank list falls back to `preset.html`. It changes the code of the unplaced widget-help commits (e90b78121 and e67862e95 before the rebase), so it stays with them, after the widget-shim commits: place it with them. (No Qt parameter editor or chain config view for `parameter_editor.html` / `chain_config.html`) |

The CUIA list needed nothing (it has no parameters; `SCREEN_AUDIO2MIDI` is in it since the
morning's rebase).

## Checks

strand-check.sh up to `strand/10-docs`: ok (01: 64, 02: 19, 03: 45, 04: 9, 05: 51, 06: 30, 07: 272,
08: 4, 09: 40, 10: 32 commits). Above `strand/10-docs` it reports "living docs with more than one
commit: docs/upstream-candidates.md" (the unplaced zs3 upstream-candidates commit), as on main
before. Strand 01 has no Claude-Session lines; 01 is based on tomita 26c42c46 directly, 02 (without
its changelog commit) applies directly on it (`git rebase --onto origin/tomita strand/01-upstream`).

Test VM (port 2264), the top: `run all` 0 failed: default 1565 passed, 40 skipped, 30 xfailed;
gui 1567 passed, 38 skipped, 30 xfailed; native 374 passed, 17 xfailed (zynaudio2midi's new
native tests run). The first top run (before the fixes) hung in `test_screen_history_options.py`
(the Lock) and failed the three old module tests of the converter row. `run default` at the tops
of the strands with conflicts, 0 failed:

| Tree | Result |
|---|---|
| 01 top | 1103 passed, 4 skipped, 30 xfailed |
| 03 top | 1118 passed, 4 skipped, 30 xfailed |
| 04 top | 1121 passed, 39 skipped, 30 xfailed |
| 05 top | 1251 passed, 40 skipped, 30 xfailed |

Qt UI in compare VM 2242 (480x320, this tree's Python through sync_ui.sh; the package of the
dc35f878a era has no `libzynaudio2midi.so`: the test VM's native build of this tree copied into
`/usr/lib/zynthian` for the test, removed afterwards): starts, "001-Parity Test" loads (Dexed,
MiniOPL3, Fabla). MIDI Input Devices lists "Audio ➔ MIDI 1" and "Audio ➔ MIDI 2" as devices (no
toggle row); a long press on output 2 shows "Audio ➔ MIDI 2" (pages Audio: audio input none, onset
-60, release -66, noise filter 15; MIDI); Dexed's MIDI input list has both outputs unrouted;
routing output 2 sets channel 2's audio input to 1 (pw-link: capture_FL → audio2midi:input_2,
both MIDI outputs on the router's device inputs); `SCREEN_AUDIO2MIDI:1` shows channel 1 (input
none; MIDI page: mode mono, pitch bend on, bend range 2); the options of output 1 offer "Audio ➔
MIDI controls" first, which opens channel 1. "008-Drone" merged into the parity test ("Load Merge
Chains"): 9 chains, upstream 9f5a87c3's fix logged once (chain 1's saved `ch5_out` replaced by its
own `ch0_out`), every router output feeds only its own chain; no tracebacks in the log.
Afterwards: main's code (db82bc9f8) synced back, theme v4 (zynthian_custom_config.sh from the
`.v4bak`), "900-Test/001-Parity Test" loaded; both compare VMs and the test VM stopped.
