# Changelog: 05-tkabs, toolkit-independent UI logic

What strand 05 of `main` changes, newest entry first: the UI logic of Tk screens and widgets moved
into modules both UIs (Tk and Qt) use, `zyngui/zynthian_*_data.py` and friends, with the Tk
screens calling them. Needs strands 02 and 03. Marker `strand/05-tkabs`; this file is the strand's
last commit (see [README.md](README.md)). The curated upstream offer of this work is the separate
branch `tk-ui-abstraction`.

## 2026-11-26: rebased onto tomita e2f423d33: one conflict in zynthian_gui_pated_notes.py: upstream's keymap screen state (7f25f8f3) ported into zynthian_pated_data (build_keymap, keymap_state; the Tk screen keeps its get_custom_keymap hook); see rebase-onto-tomita-2026-11-26.md

- `d898e4203` Pattern editor: keymaps and note tables in zyngui/zynthian_pated_data.py

## 2026-11-26: upstream's new CUIAs VNC_START, VNC_STOP, SET_PATTERN_JSON in the CUIA list

- `75ebbeaff` CUIA list: VNC_START, VNC_STOP and SET_PATTERN_JSON from upstream

## 2026-11-26: chain controllers with positions and named pages (model, Tk, stock drivers); the control grid model (chain control's pages as cells, the shared selection) and the controller settings logic

- `2f4718646` Chain controllers with positions and named pages
- `0e2445a33` Chain controller pages in the Tk UI and the controller drivers
- `e500e7245` Control grid model: chain control's pages as a grid of cells, the shared selection (UI independent)
- `03a915198` Controller settings: shared logic for the settings of controller drivers

## 2026-11-24: Organelle keys for the touch keypad and V4 kits (shared mapping)

- `79078e652` Organelle keys: the touch keypad's and V4 kits' switches, SEL, F-key labels

## 2026-11-20: rebased onto tomita 0c1098a68: upstream's SysEx identity driver autoload (07793ae7) ported into the shared MIDI config module (both UIs): identity requests in midi_config_list(), device_drivers() by device ID, identity and generic, driver_description() with the identity note; see rebase-onto-tomita-2026-11-20c.md

- `2bdc9ae15` MIDI config, audio out screens: lists and actions as modules
- `051b3f5e5` Audio input list, ALSA input controls, MIDI device drivers as module functions

## 2026-11-20: Websocket server and feedback streams as a toolkit-independent mixin

- `cfd365516` zyngui: websocket server and feedback streams in a toolkit-independent mixin

## 2026-11-20: Tests robust in upstream's CI: CUIA list import with zyncoder from ZYNCODER_DIR, envelope drag polygons without nested pytest.approx

- `f702dffdc` tests: CUIA list import check finds zyncoder via ZYNCODER_DIR (upstream's CI)
- `43b5c6809` tests: envelope drag polygons compared without nested pytest.approx

## 2026-11-20: the strand when the changelog started

39 commits on strand 04, written 2026-11-05 to 2026-11-19.

- **Screens:** snapshot files, MIDI config and audio out lists, admin settings, MIDI recorder list,
  chain graph, audio inputs and ALSA controls, launcher pads and phrases, wiring, file browser
  roots, init_zyncore() (`cc878e859`, `2bdc9ae15`, `2109942b1`, `9ffa85f81`, `8737c42ed`,
  `051b3f5e5`, `a72ca752f`, `0ad0cdf87`, `051500307`, `198ef52ef`).
- **Pattern editor:** keymaps, note tables, chords, per-note parameters, SMF import/export
  (`d898e4203`, `08eb11aad`, `cb198389e`, `50a853710`).
- **Widgets:** audio file, envelope and filter, plugin widgets, tempo and radio, EuclidSeq,
  Organelle (with the kits' knob mapping), SooperLooper, drawbar, X-Y touchpad, MIDI learn,
  transport keys, engine_widget() (`8dfc303d3`, `3637f4ea1`, `cba2c8b56`, `97279cbd4`,
  `c4efc2017`, `caa998e68`, `23b012edf`, `6ab7e6569`, `d415a2947`, `f144864a2`, `f8344eb7e`).
- **CUIA list** in its own module, importable without the Tk UI, with upstream's categories
  (`d702385a3`, `825336ede`). Docs: [qt-cuia-plan.md](../qt-cuia-plan.md).
- **Upstream changes carried into the moved code:** all-channel MIDI chains in the output list,
  curved envelopes, the gxgraphiceq widget name (`473db7687`, `bc231d476`, `61eab4a41`). Docs:
  [rebasing-onto-upstream.md](../rebasing-onto-upstream.md) ("Upstream changes lost in moved
  code").
