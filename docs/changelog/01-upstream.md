# Changelog: 01-upstream, fixes for upstream

What strand 01 of `main` changes, newest entry first. The strand holds self-contained fixes that
apply directly on origin/tomita; it is offered upstream as zynthian/zynthian-ui#617 (branch
`hjanetzek:upstream-fixes` = `strand/01-upstream`). Its commits carry no Claude-Session lines and
the strand has no changelog commit of its own (it would land in the pull request): this file is a
changelog commit in strand 10, below 10's own. See [README.md](README.md).

## 2026-11-28: rebased onto tomita 046817e4: "tests: test_view_state: the keymap state from get_keymap_state()" dropped (upstream 511edda9 made the same change); see rebase-onto-tomita-2026-11-28.md

## 2026-11-28: zs3: SS_ZS3_LIST signal, change_zs3_id(), ZS3_DELETE CUIA

- `013c8eec2` zs3: SS_ZS3_LIST signal, change_zs3_id(), ZS3_DELETE CUIA

## 2026-11-27: rebased onto tomita 26c42c46: conflicts in the vanished-device and snapshot-merge commits (upstream's two-channel audio to MIDI converter, its router-output fix 9f5a87c3); the screen history test with an RLock as zynthian_gui (7b6fbaa2); see rebase-onto-tomita-2026-11-27b.md

## 2026-11-27: rebased onto tomita 5b0b6966: conflict in CHAIN_OPTIONS (upstream's audio2midi screen), the legacy snapshot import-cycle commit fixed for 876d5e2d's AUDIO2MIDI_UID; nothing dropped, see rebase-onto-tomita-2026-11-27.md

## 2026-11-27: test_view_state: the keymap state from get_keymap_state() (upstream f1c9be06)

- `603420a04` tests: test_view_state: the keymap state from get_keymap_state()

## 2026-11-26: Tk: an options list shown again keeps the screen history (BACK from Admin's settings)

- `19f34f7ab` zynthian_gui: an options list shown again doesn't end the screen history at an older one

## 2026-11-26: rebased onto tomita e2f423d33: no conflicts, nothing dropped; the ENABLE_MIDI_LEARN_CC / MIDI_UNLEARN_NODE docstrings use "Params:" (upstream's test_cuia_docstrings.py, dd012ced); see rebase-onto-tomita-2026-11-26.md

- `f4795be27` zynthian_gui: ENABLE_MIDI_LEARN_CC and MIDI_UNLEARN_NODE find the controller by processor id and symbol

## 2026-11-26: chain controllers: the snapshot-merge and purge fixes; UI-zmip notes reach pattern recording; Tk "Record from MIDI" again

- `b2a255aad` Chain controllers: removing a processor no longer drops all of them
- `f25176791` Snapshot merge: map the chain controllers' processor ids
- `d62e2518b` autoconnect: notes played through the UI zmip reach zynseq's pattern recording
- `b5caf98bd` Tk pattern editor: "Record from MIDI" in the pattern options with touch navigation

## 2026-11-24: Organelle widget: V4 kits' select mode and AUX switches; the push of those switches no longer taken

- `d1a5ba63f` Organelle widget: the select mode and AUX switches on V4 kits
- `c9958226b` Organelle widget: don't take the push of the select mode and AUX switches

## 2026-11-21: rebased onto tomita 3dbab929d: no conflicts, nothing upstream took (pull requests #618, #619 still open); see rebase-onto-tomita-2026-11-21.md

## 2026-11-21: jalv's output decoded with errors="replace": an invalid UTF-8 byte no longer ends its reading

- `7b80d0b73` jalv engine: an invalid UTF-8 byte in jalv's output doesn't stop its reading

## 2026-11-20: rebased onto tomita 0c1098a68: the APC40 mk2 end() and Behringer Motor reset_feedback() fixes (de6ea448, 6a360d91) dropped: upstream's CC feedback broker (d6d08865) rewrote both drivers and removed the code they fixed; the import-cycle fix's conflict with the broker import resolved; see rebase-onto-tomita-2026-11-20c.md

- `2eab4a98c` zyngine: break the state manager <-> chain manager / legacy snapshot import cycle

## 2026-11-20: An engine that fails to start (jalv exits or hangs before its prompt) fails the processor add cleanly: no hang, no empty chain

- `751a71be2` Chain manager: an engine that fails to start fails the processor add cleanly
- `57ad510d6` jalv engine: a jalv that exits or hangs at start fails the engine start
- `8f55b6d69` GUI: a new chain whose processor fails to start isn't left empty
- `f9d74a3f7` jalv engine: the output thread stops when jalv ends
- `f4517e60c` zynthian_lv2: test_lv2_plugin() returns when jalv ends before its prompt

## 2026-11-20: the strand when the changelog started

52 commits on tomita `6e0527a45`, written 2026-11-02 to 2026-11-20.

- **zynmixer:** no invalid free or stale buffers with solo, sends and period changes; no deadlock
  under pipewire-jack when a strip or send is removed; the Python binding calls the functions
  libzynmixer has (`5d278b167`, `7bda80c4a`, `fa6a3af0b`).
- **zynseq bindings:** restypes for uint8_t, bool and int16_t results, the `offset` typo, the
  CHANNEL_CHARS comma, save_pattern, transport client ids, reset()/setState() clear the selected
  pattern, zynseq.h without undefined functions (`4302d5ff7`, `8a46e9b93`, `a60b6cf03`,
  `fcf3daf92`, `852bdf8e7`, `842e1ff83`, `7f76f8d86`, `7a4b85008`, `a68afb48c`).
- **Native code:** printf formats for 64-bit sizes and 32-bit ARM (`4ac28fdc7`, `2e23b4ea8`);
  invalid escape sequences in Python string literals (`a65495b7f`).
- **Snapshots:** the oldest legacy formats load (87 of 366 shared snapshots failed in the
  converter), LinuxSampler SFZ chains load with sfizz, a vanished MIDI device no longer fails a
  load, load progress in the state manager, bankless mode and bank deletion select the right bank,
  the state manager import cycle broken (`0e3ed53ca`, `f873d3175`, `1fcdded08`, `340d243ec`,
  `0c5d9a06b`, `c39fee0e8`, `2eab4a98c`).
- **Engines:** interactive shells with TERM=dumb, Aeolus and setBfree end the busy state when their
  start fails, Aeolus opens its OSC server first, presets whose id is a list, the plugin UI type
  from lilv, the audio player's exit crash, ALSA mixer start-up (`0bc35032d`, `72c165d09`,
  `9cfaec445`, `8ab36d522`, `22f9f7c24`, `cd49ecd20`, `af3c12066`, `eb09e0604`).
- **Tk UI and CUIAs:** MIXER/ZYNPOT_ABS with string arguments, SELECT without index, MIDI learn
  CUIAs by processor id and symbol, CHAIN_OPTIONS, MENU on special processors, pattern editor and
  ZS3 cursors, MIDI recorder rows, randomize within min/max, the 4-column main menu's MIDI Output
  (`fb8621da2`, `586ab20e8`, `f4795be27`, `2acd58a0b`, `529ce7d8c`, `f6b8e8f3b`, `690001a5c`,
  `beffa25cd`, `775898a3a`, `dea5d3d3f`).
- **Controller drivers and widgets:** launchpad_pro_mk2 sends mode, the samplv1 widget's module
  path (`0bf22a9cd`, `3f8429c4c`); APC40 mk2 and Behringer Motor unregistered their handlers
  correctly (de6ea448, 6a360d91: dropped in the rebase onto tomita 0c1098a6, see the entry
  there).
- **Robustness and tests:** signal manager unregister_all(), the websocket worker without WS LEDs,
  rebuild_midi_graph() releases its lock, the websocket test skipped where the server is stubbed,
  strict-xfail markers of fixed defects dropped (`b76806883`, `15890f2e7`, `6984646c3`,
  `424fa07d2`). The per-fix status is in [upstream-candidates.md](../upstream-candidates.md).
