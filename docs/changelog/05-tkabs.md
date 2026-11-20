# Changelog: 05-tkabs, toolkit-independent UI logic

What strand 05 of `main` changes, newest entry first: the UI logic of Tk screens and widgets moved
into modules both UIs (Tk and Qt) use, `zyngui/zynthian_*_data.py` and friends, with the Tk
screens calling them. Needs strands 02 and 03. Marker `strand/05-tkabs`; this file is the strand's
last commit (see [README.md](README.md)). The curated upstream offer of this work is the separate
branch `tk-ui-abstraction`.

## 2026-11-28: rebased onto tomita 046817e4: conflicts in the wiring and websocket mixin commits (zynthian_gui's imports: zynthian_mainloop_lock, no RLock); nothing lost in moved code (upstream's busy-screen and main-loop changes are in Tk code 05 left in zynthian_gui); see rebase-onto-tomita-2026-11-28.md

## 2026-11-28: CUIA list: ZS3_DELETE (strand 01's zs3 CUIA)

- `7b2a2b2bd` CUIA list: ZS3_DELETE (category zs3)

## 2026-11-27: rebased onto tomita 26c42c46: conflicts in the MIDI config, device drivers and websocket mixin moves; upstream's two-channel audio to MIDI converter (34b22105, acee218e: outputs as devices, route action) ported into zynthian_midi_config_data, the module tests follow; see rebase-onto-tomita-2026-11-27b.md

## 2026-11-27: rebased onto tomita 5b0b6966: conflicts in the MIDI config, admin, pattern editor keymap and audio file moves; upstream's audio2midi/aubionotes list changes, keymap state on demand (f1c9be06) and #1847 ported into the shared modules, see rebase-onto-tomita-2026-11-27.md

## 2026-11-27: upstream's audio to MIDI converter and #1847: SCREEN_AUDIO2MIDI in the CUIA list; tests of the ports into the shared modules

- `465777947` CUIA list: SCREEN_AUDIO2MIDI from upstream
- `5ccbd7829` tests: upstream's audio to MIDI row and #1847 in the shared modules

## 2026-11-26: rebased onto tomita e2f423d33: one conflict in zynthian_gui_pated_notes.py: upstream's keymap screen state (7f25f8f3) ported into zynthian_pated_data (build_keymap, keymap_state; the Tk screen keeps its get_custom_keymap hook); see rebase-onto-tomita-2026-11-26.md

- `edc23bc2a` Pattern editor: keymaps and note tables in zyngui/zynthian_pated_data.py

## 2026-11-26: upstream's new CUIAs VNC_START, VNC_STOP, SET_PATTERN_JSON in the CUIA list

- `cba07b38e` CUIA list: VNC_START, VNC_STOP and SET_PATTERN_JSON from upstream

## 2026-11-26: chain controllers with positions and named pages (model, Tk, stock drivers); the control grid model (chain control's pages as cells, the shared selection) and the controller settings logic

- `1f2ca1067` Chain controllers with positions and named pages
- `6480af222` Chain controller pages in the Tk UI and the controller drivers
- `5f138dc87` Control grid model: chain control's pages as a grid of cells, the shared selection (UI independent)
- `44b3e89f0` Controller settings: shared logic for the settings of controller drivers

## 2026-11-24: Organelle keys for the touch keypad and V4 kits (shared mapping)

- `caeef5d86` Organelle keys: the touch keypad's and V4 kits' switches, SEL, F-key labels

## 2026-11-20: rebased onto tomita 0c1098a68: upstream's SysEx identity driver autoload (07793ae7) ported into the shared MIDI config module (both UIs): identity requests in midi_config_list(), device_drivers() by device ID, identity and generic, driver_description() with the identity note; see rebase-onto-tomita-2026-11-20c.md

- `d59b126da` MIDI config, audio out screens: lists and actions as modules
- `c6b87fef1` Audio input list, ALSA input controls, MIDI device drivers as module functions

## 2026-11-20: Websocket server and feedback streams as a toolkit-independent mixin

- `2bbb9a577` zyngui: websocket server and feedback streams in a toolkit-independent mixin

## 2026-11-20: Tests robust in upstream's CI: CUIA list import with zyncoder from ZYNCODER_DIR, envelope drag polygons without nested pytest.approx

- `e9657194d` tests: CUIA list import check finds zyncoder via ZYNCODER_DIR (upstream's CI)
- `10bdd1270` tests: envelope drag polygons compared without nested pytest.approx

## 2026-11-20: the strand when the changelog started

39 commits on strand 04, written 2026-11-05 to 2026-11-19.

- **Screens:** snapshot files, MIDI config and audio out lists, admin settings, MIDI recorder list,
  chain graph, audio inputs and ALSA controls, launcher pads and phrases, wiring, file browser
  roots, init_zyncore() (`9a6ce4ca9`, `d59b126da`, `15b254fd6`, `f35c3ff4b`, `5bfc11caa`,
  `c6b87fef1`, `1fb4a8742`, `0ed75f533`, `5fb2a75f1`, `e4a4f5f2a`).
- **Pattern editor:** keymaps, note tables, chords, per-note parameters, SMF import/export
  (`edc23bc2a`, `6b8d8ada6`, `089df3fc2`, `cf8dfeaa3`).
- **Widgets:** audio file, envelope and filter, plugin widgets, tempo and radio, EuclidSeq,
  Organelle (with the kits' knob mapping), SooperLooper, drawbar, X-Y touchpad, MIDI learn,
  transport keys, engine_widget() (`2f5b92010`, `f80208976`, `4c90c7231`, `6de623106`,
  `1f77bc592`, `d6b145d7a`, `c45e4afaa`, `d766fd613`, `b0da5d3d2`, `a994dedc0`, `ce41b9c27`).
- **CUIA list** in its own module, importable without the Tk UI, with upstream's categories
  (`1159b4c58`, `3b7981544`). Docs: [qt-cuia-plan.md](../qt-cuia-plan.md).
- **Upstream changes carried into the moved code:** all-channel MIDI chains in the output list,
  curved envelopes, the gxgraphiceq widget name (`62e53089e`, `ca3a862e4`, `35b45626a`). Docs:
  [rebasing-onto-upstream.md](../rebasing-onto-upstream.md) ("Upstream changes lost in moved
  code").
