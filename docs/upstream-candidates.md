# Upstream candidates

Log of changes on the `nura` branch that could go to zynthian upstream, and of upstream bugs
noticed but not fixed yet. The overview of what is already proposed is the description of
[PR #1](https://github.com/hjanetzek/zynthian-ui/pull/1); this file adds what came later.
Keep it up to date with each fix.

Status: **ready** (self-contained commit), **split** (mixed with port changes, needs its own
commit), **open** (noticed, not fixed).

## Bug fixes

| Commit | Status | Change |
|---|---|---|
| [50d7d86a](https://github.com/hjanetzek/zynthian-ui/commit/50d7d86a) | ready | **Top bar: CPU load above 100 %.** The status colour fades from green to red with the load; above 100 % (pipewire-jack reports that at times) its green part went negative and Tk rejected the colour (`invalid color name "#cc-400"`) on every status refresh. |
| [fa23e789](https://github.com/hjanetzek/zynthian-ui/commit/fa23e789) | ready (the zynthian part; the APKBUILD line is port-specific) | **Audio recorder: jack_capture from PATH.** It started `/usr/local/bin/jack_capture`, where ZynthianOS installs it; distributions install it in PATH, so recording failed. Falls back to `/usr/local/bin`. |
| [effe2a4d](https://github.com/hjanetzek/zynthian-ui/commit/effe2a4d) | ready | **Restoring presets whose id is a list.** `set_preset()` with a preset_info looked the id up in the favourites as is; favourites are keyed by the id's string, and FluidSynth's ids are lists: `unhashable type: 'list'`, the preset of such a chain wasn't restored from snapshots. |
| [be63e13b](https://github.com/hjanetzek/zynthian-ui/commit/be63e13b) | ready | **Crash at exit after playing a file.** `chain_manager.remove_processor(None, proc)` (processors without chain: audio player, tempo, ALSA mixer) didn't remove the processor from its engine: the audio player's file thread outlived the interpreter and crashed in the Python callback at exit (SIGSEGV, Tk and Qt). Then `zynaudioplayer.stop()` called the non-existent `lib_stop` instead of `stop`, so its jack client was never closed (probably the rare PipeWire abort at exit). |
| [6de94330](https://github.com/hjanetzek/zynthian-ui/commit/6de94330) | split (with the admin settings below) | **Admin: PFL output list with an odd number of playback ports** raised `IndexError` (the pair loop read past the end). **Hotplug menu: the ZynVoice entry** paused autoconnect and returned without resuming it, so autoconnect stayed off. |
| [2fd07f40](https://github.com/hjanetzek/zynthian-ui/commit/2fd07f40) | ready, in PR #1 | Chain manager: a chain that can't be moved left `None` as the selected index; the UI got stuck. |

## Refactorings: UI-independent logic out of the Tk screens

Useful upstream on their own (testable without a display, reusable by other front ends). In
these commits they come together with the Qt UI; each would need its own commit.

| Commit | Status | Change |
|---|---|---|
| [8f267cac](https://github.com/hjanetzek/zynthian-ui/commit/8f267cac) | split | `zynthian_gui_config.init_zyncore()`: zyncore, control I/O and MIDI set-up as a function instead of code in the Tk-only block; the Tk path calls it at the same place. |
| [4da7bc9f](https://github.com/hjanetzek/zynthian-ui/commit/4da7bc9f) | split | `zyngine/zynthian_snapshot_files.py`: the snapshot screen's file logic (banks, names, MIDI program numbers, bank and snapshot lists); `zynthian_gui_snapshot` uses it. |
| [7f17ec36](https://github.com/hjanetzek/zynthian-ui/commit/7f17ec36) | split | `zyngui/zynthian_admin_settings.py`: the admin menu's simple toggles (program change mode, bank change, active MIDI channel, USB MIDI by port, audio levels on snapshots, peak meters, preset preload), moved unchanged; `zynthian_gui_admin` calls them. [6de94330](https://github.com/hjanetzek/zynthian-ui/commit/6de94330) adds the value settings (PFL output, visible chains/launchers, mixer toggle, channel pressure => CC) and the hotplug audio menu (options and actions). |
| [237a5026](https://github.com/hjanetzek/zynthian-ui/commit/237a5026) | split | `zyngui/zynthian_chain_graph.py`: the chain manager's graph (nodes per chain and row, source/destination flags, node colour class), moved out of `zynthian_gui_chain_manager`, which calls it. |
| [7e346eb3](https://github.com/hjanetzek/zynthian-ui/commit/7e346eb3) | split | `zyngui/zynthian_midi_recorder_data.py`: the MIDI recorder's file list, moved unchanged; `zynthian_gui_midi_recorder` calls it. |
| [3d2ef140](https://github.com/hjanetzek/zynthian-ui/commit/3d2ef140) | split | `zyngui/zynthian_midi_config_data.py`, `zynthian_audio_out_data.py`: list building and route/service actions of `zynthian_gui_midi_config` and `zynthian_gui_audio_out`, moved unchanged; the Tk screens call them. |

## Noticed, not fixed yet

| Where | Status | Problem |
|---|---|---|
| `zyngui/zynthian_gui_main_menu.py` (4-column menu) | open | "MIDI Output" calls `midi_in_config`, so it opens the MIDI input devices. |
| `zyngui/zynthian_gui_snapshot.py`, `delete_bank()` | open | Deleting the current bank sets `sm.snapshot_dir = None` instead of `sm.snapshot_bank`. |
| `zynthian_snapshot_files.check_bankless_mode()` (from `zynthian_gui_snapshot`) | open | Without banks it creates `000` but doesn't select it (the comment says "choose it"); only the next call does. |
| `zyngui/zynthian_gui_processor_options.py`, `randomize()` | open (fixed in the Qt UI) | Float values are drawn from 0 to the range instead of min to max: wrong for controllers with a negative minimum. |
| `zyngui/zynthian_gui.py`, `cuia_select()` | open | `SELECT` without a parameter raises `IndexError` in the CUIA thread (logged on every such OSC message). |
| `zyngine/ctrldev/examples/zynthian_ctrldev_midiproc_notes_filter.py:67` | open | Syntax error (`filter_enabled =`): `compileall` over `zyngine` fails. |
| `zyngui/zynthian_midi_config_data.py` (from `zynthian_gui_midi_config`) | open | Network MIDI services are only offered if their binaries are in `/usr/local/bin` (jacknetumpd, jackrtpmidid, qmidinet), as with jack_capture. |
| `zyngui/zynthian_gui.py`, exit on SIGTERM | open (the Qt UI saves it) | The last state is only saved by the admin's Exit/power actions and "Clean", not when zynthian is stopped with SIGTERM (systemd, a kiosk session ending): changes since then are lost although the next start restores the last state. |
| PipeWire, at exit | probably fixed by the audio player fix above | Rarely an abort at exit, after the mixers shut down: `'source->loop == &impl->loop' failed at spa/plugins/support/loop.c:189 remove_from_poll()`; seen with the audio player's jack client left open. |
