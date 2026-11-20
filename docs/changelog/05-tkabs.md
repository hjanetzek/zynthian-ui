# Changelog: 05-tkabs, toolkit-independent UI logic

What strand 05 of `main` changes, newest entry first: the UI logic of Tk screens and widgets moved
into modules both UIs (Tk and Qt) use, `zyngui/zynthian_*_data.py` and friends, with the Tk
screens calling them. Needs strands 02 and 03. Marker `strand/05-tkabs`; this file is the strand's
last commit (see [README.md](README.md)). The curated upstream offer of this work is the separate
branch `tk-ui-abstraction`.

## 2026-11-20: rebased onto tomita 0c1098a68: upstream's SysEx identity driver autoload (07793ae7) ported into the shared MIDI config module (both UIs): identity requests in midi_config_list(), device_drivers() by device ID, identity and generic, driver_description() with the identity note; see rebase-onto-tomita-2026-11-20c.md

- `42337d654` MIDI config, audio out screens: lists and actions as modules
- `723d699a3` Audio input list, ALSA input controls, MIDI device drivers as module functions

## 2026-11-20: Websocket server and feedback streams as a toolkit-independent mixin

- `bdb1e89d0` zyngui: websocket server and feedback streams in a toolkit-independent mixin

## 2026-11-20: Tests robust in upstream's CI: CUIA list import with zyncoder from ZYNCODER_DIR, envelope drag polygons without nested pytest.approx

- `15af32a72` tests: CUIA list import check finds zyncoder via ZYNCODER_DIR (upstream's CI)
- `6bbb953df` tests: envelope drag polygons compared without nested pytest.approx

## 2026-11-20: the strand when the changelog started

39 commits on strand 04, written 2026-11-05 to 2026-11-19.

- **Screens:** snapshot files, MIDI config and audio out lists, admin settings, MIDI recorder list,
  chain graph, audio inputs and ALSA controls, launcher pads and phrases, wiring, file browser
  roots, init_zyncore() (`3668b7c64`, `42337d654`, `9612306ff`, `cd86a557d`, `0f8e36f3b`,
  `723d699a3`, `c6df308eb`, `a06422173`, `402d52a94`, `70bec77d6`).
- **Pattern editor:** keymaps, note tables, chords, per-note parameters, SMF import/export
  (`abb20d299`, `4c2b7c7a2`, `8fbaba274`, `990c3969b`).
- **Widgets:** audio file, envelope and filter, plugin widgets, tempo and radio, EuclidSeq,
  Organelle (with the kits' knob mapping), SooperLooper, drawbar, X-Y touchpad, MIDI learn,
  transport keys, engine_widget() (`68c6ebf52`, `9699f4914`, `8a6a57695`, `86dd34380`,
  `2a778e58d`, `03c9db9fa`, `61798e363`, `a39e52ed5`, `cc4eb766a`, `5a6445e13`, `8a4b31896`).
- **CUIA list** in its own module, importable without the Tk UI, with upstream's categories
  (`d898f8e4c`, `0dac72315`). Docs: [qt-cuia-plan.md](../qt-cuia-plan.md).
- **Upstream changes carried into the moved code:** all-channel MIDI chains in the output list,
  curved envelopes, the gxgraphiceq widget name (`b64ba7c09`, `0e3ab38ae`, `bff763d07`). Docs:
  [rebasing-onto-upstream.md](../rebasing-onto-upstream.md) ("Upstream changes lost in moved
  code").
