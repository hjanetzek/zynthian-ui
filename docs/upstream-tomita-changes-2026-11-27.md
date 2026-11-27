# Upstream tomita changes, e2f423d3 → 5b0b6966 (seen 2026-11-27)

What changed in zynthian upstream `tomita` between our previous base (`e2f423d33`) and
`origin/tomita` at `5b0b69662`, the base of the rebase described in
`docs/rebase-onto-tomita-2026-11-27.md`: 19 commits (one merge, edfc7535), 2026-11-26..27.
The last column says what a change means for this repository.

| Commit | Change | Impact here |
|---|---|---|
| 4089478d | #1851: a port designated `lv2:enabled` is the processor's bypass; an undesignated "bypass"/"enable" toggle is then hidden; only one bypass per processor | merged cleanly with 06's port-description cache (`get_plugin_ports`); the Qt UI reads `bypass_zctrl` |
| 00d766ba | `ZYNTHIAN_DEBUGPY=[host:]port` (and `ZYNTHIAN_DEBUGPY_WAIT=1`) start debugpy in `zynthian_main.py` | Tk only; `zynthian_qt_main.py` has no such hook (optional TODO) |
| 98ccefc7, 81598b1c, d2128246, 27b65fd2 | software update progress view (`zyngui/zynthian_gui_update_progress.py`, drawn by zynthian-sys' `sbin/zynthian_update_progress.py`); "Update Software" runs the update in a thread and shows it; `update_progress_task` polls `/run/zynthian_update/running`; the busy screens pause during an update; `zynthian.sh` keeps the progress display on exit 101 | merged into the Tk UI (05's admin-settings import next to it). The Qt UI has no "Update Software" (Nura updates are packages) and no progress screen: not needed on Nura (TODO only for a Qt UI on ZynthianOS) |
| 5f4a18c4 | LV2 scan: plugin info cache (`jalv/plugin_info_cache.json`, keyed by the data files' mtime/size), `is_plugin_supported()` before loading a plugin's data, rdflib imported in `get_info_from_ttl` only | the cache file's path from `zynthian_paths` (03); 06's lazy world uses it unchanged (`get_world()`); 06's own rdflib move is now upstream's |
| c391277b | preset scan: a preset's data files are loaded only once (shared bank files), `generate_presets_cache_workaround` removed | 06's `get_world()` variant of the workaround dropped with it |
| e5ea8288, 3ff19459 | native audio to MIDI converter: `zynlibs/zynaudio2midi` (JACK client "audio2midi", mono/poly, pitch bend), engine "AM" as a global processor (id -5, `state_manager.audio2midi_processor`, `audio2midi_in`), MIDI port `AUDIO2MIDI:in`, CUIA `SCREEN_AUDIO2MIDI`, a row in the MIDI input devices list (toggle, bold select: its controls, options: controls and audio inputs), `ZYNTHIAN_MIDI_AUDIO2MIDI_ENABLED`; native and integration tests | the Tk list changes ported into `zynthian_midi_config_data` (05); library and help page through `zynthian_paths`, `desktop/install.sh` installs the library (03); CUIA list (05); the Qt UI: chain control for the processor, the devices list row and options (07). nura-builds' recipes must build `zynaudio2midi` |
| f1c9be06 | the notes editor's keymap state built on demand: `keymap_name`, `get_keymap_state()` instead of `keymap_state` | ported into the moved keymap code (05: `get_keymap_state()` calls `zynthian_pated_data.keymap_state`); upstream's own `test_view_state.py` still used `keymap_state` (fails on tomita): fixed in 01 |
| 876d5e2d | aubionotes removed (service, state, list rows, autoconnect); legacy snapshots: `AUBIONOTES_ENABLED` → `AUDIO2MIDI_ENABLED`, `AUBIO:in` → `AUDIO2MIDI:in`; `midi_aubionotes_enabled` gone, `ZYNTHIAN_MIDI_AUBIONOTES_ENABLED` is the fallback of the new setting | ported into `zynthian_midi_config_data` (05: no aubio rows or service); 03's `@system_service` on the aubionotes methods dropped with them |
| 45aa64ae | #1849: an engine without state manager (webconf's ALSA mixer instance) has `chain_manager` None | no conflict |
| 5b0b6966 | #1847: the audio file widget takes a path controller for audio files (declared types wav, aiff, flac, mp3, ogg), else one without types, not just the first path controller | ported into `zynthian_audio_file_data.file_zctrl` / `find_audio_path_zctrl` (05): the Tk widget and the Qt audio file view |
| 899951fe, a76250fb, a8b68e46, 29198d95 | `.claude/skills/zynthian-lv2-plugin/` (release tags, package_pr.py, widget packages, a template fix) | none |
| edfc7535 | merge | – |
