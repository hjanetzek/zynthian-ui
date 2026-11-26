# Upstream tomita changes, 3dbab929 → e2f423d3 (seen 2026-11-26)

What changed in zynthian upstream `tomita` between our previous base (`3dbab929d`) and
`origin/tomita` at `e2f423d33`, the base of the rebase described in
`docs/rebase-onto-tomita-2026-11-26.md`: 17 commits (one merge, 140b584d), 2026-11-22..24.
The last column says what a change means for this repository.

| Commit | Change | Impact here |
|---|---|---|
| b0b6dd8b | Tk CUIAs `VNC_START`, `VNC_STOP` (category system): the state manager's `start_vncserver` / `stop_vncserver` | the CUIA list (05) and the Qt UI (07) got them |
| dd012ced | CUIA docstrings: params are positional, a "Params:" section (not "Keyword Args:"); `tests/architecture/test_cuia_docstrings.py` | two docstrings of strand 01 adapted (ENABLE_MIDI_LEARN_CC, MIDI_UNLEARN_NODE) |
| 62b407e3 | zynseq: `setState` reuses `setPattern`'s loader, `setPattern` resets the undo history; `pattern.schema.json`; pated_base | no conflict |
| 53147dca | zynseq `setState`: sequences loop by default, an explicit `repeat` 0 is kept | snapshot behaviour: sequences without `repeat` loop |
| cb79f1a7 | zynseq `state.schema.json` + tests; `jsonschema` in requirements-dev.txt | the test VM installs py3-jsonschema (09) |
| a950bf5b | zynseq: single patterns as JSON (`getPatternState`, `setPattern`), CUIA `SET_PATTERN_JSON` (category hardware) | CUIA list (05), Qt UI (07) |
| 0ed7fd28 | the Tk pattern editors report a `screen_state` (websocket feedback): pattern, cursor, editor values | merged into the Tk screens; the Qt pattern editor has its own screen state (zynqt/ws_state.py), not aligned yet |
| 7f25f8f3 | the Tk notes editor reports its keymap (`keymap_state`: name, named keys of a custom map) | ported into the moved keymap code (05, `zynthian_pated_data.keymap_state`, `build_keymap`) |
| 6536965e | zynseq.py: `set_pattern_json` KeyError without patterns | no conflict |
| e2f423d3 | APC40 mk2: a chain without mixer processor no longer raises KeyError | merges with the chain controller pages' slot change (05) |
| a2e23db2, 51ae4c85, 461d8022, 7ee0c1f4, c805d2c5, 4786587e | `.claude/skills/` (zynthian-lv2-plugin, zynthian-operator) | none |
