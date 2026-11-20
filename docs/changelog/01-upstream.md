# Changelog: 01-upstream, fixes for upstream

What strand 01 of `main` changes, newest entry first. The strand holds self-contained fixes that
apply directly on origin/tomita; it is offered upstream as zynthian/zynthian-ui#617 (branch
`hjanetzek:upstream-fixes` = `strand/01-upstream`). Its commits carry no Claude-Session lines and
the strand has no changelog commit of its own (it would land in the pull request): this file is a
changelog commit in strand 10, below 10's own. See [README.md](README.md).

## 2026-11-26: Tk: an options list shown again keeps the screen history (BACK from Admin's settings)

- `1d3055f70` zynthian_gui: an options list shown again doesn't end the screen history at an older one

## 2026-11-26: rebased onto tomita e2f423d33: no conflicts, nothing dropped; the ENABLE_MIDI_LEARN_CC / MIDI_UNLEARN_NODE docstrings use "Params:" (upstream's test_cuia_docstrings.py, dd012ced); see rebase-onto-tomita-2026-11-26.md

- `e9ea8e71e` zynthian_gui: ENABLE_MIDI_LEARN_CC and MIDI_UNLEARN_NODE find the controller by processor id and symbol

## 2026-11-26: chain controllers: the snapshot-merge and purge fixes; UI-zmip notes reach pattern recording; Tk "Record from MIDI" again

- `2256d8866` Chain controllers: removing a processor no longer drops all of them
- `c439cc6e9` Snapshot merge: map the chain controllers' processor ids
- `389d8eb06` autoconnect: notes played through the UI zmip reach zynseq's pattern recording
- `7440ef363` Tk pattern editor: "Record from MIDI" in the pattern options with touch navigation

## 2026-11-24: Organelle widget: V4 kits' select mode and AUX switches; the push of those switches no longer taken

- `f4843c84d` Organelle widget: the select mode and AUX switches on V4 kits
- `34e1fe6d0` Organelle widget: don't take the push of the select mode and AUX switches

## 2026-11-21: rebased onto tomita 3dbab929d: no conflicts, nothing upstream took (pull requests #618, #619 still open); see rebase-onto-tomita-2026-11-21.md

## 2026-11-21: jalv's output decoded with errors="replace": an invalid UTF-8 byte no longer ends its reading

- `d3e2aa316` jalv engine: an invalid UTF-8 byte in jalv's output doesn't stop its reading

## 2026-11-20: rebased onto tomita 0c1098a68: the APC40 mk2 end() and Behringer Motor reset_feedback() fixes (de6ea448, 6a360d91) dropped: upstream's CC feedback broker (d6d08865) rewrote both drivers and removed the code they fixed; the import-cycle fix's conflict with the broker import resolved; see rebase-onto-tomita-2026-11-20c.md

- `acdd51380` zyngine: break the state manager <-> chain manager / legacy snapshot import cycle

## 2026-11-20: An engine that fails to start (jalv exits or hangs before its prompt) fails the processor add cleanly: no hang, no empty chain

- `74a78968f` Chain manager: an engine that fails to start fails the processor add cleanly
- `8a2354efb` jalv engine: a jalv that exits or hangs at start fails the engine start
- `464ff6e3d` GUI: a new chain whose processor fails to start isn't left empty
- `c86b77e55` jalv engine: the output thread stops when jalv ends
- `9d01967f6` zynthian_lv2: test_lv2_plugin() returns when jalv ends before its prompt

## 2026-11-20: the strand when the changelog started

52 commits on tomita `6e0527a45`, written 2026-11-02 to 2026-11-20.

- **zynmixer:** no invalid free or stale buffers with solo, sends and period changes; no deadlock
  under pipewire-jack when a strip or send is removed; the Python binding calls the functions
  libzynmixer has (`c6e11e60d`, `4098682a3`, `2df8a5e47`).
- **zynseq bindings:** restypes for uint8_t, bool and int16_t results, the `offset` typo, the
  CHANNEL_CHARS comma, save_pattern, transport client ids, reset()/setState() clear the selected
  pattern, zynseq.h without undefined functions (`faf97fdfb`, `ad01e18f4`, `6f2e024ec`,
  `98f64f072`, `30b9bcabb`, `f660343aa`, `d54bf3805`, `8f4374a47`, `04971dfc3`).
- **Native code:** printf formats for 64-bit sizes and 32-bit ARM (`805cbe6b4`, `8b4faa721`);
  invalid escape sequences in Python string literals (`18ae12bba`).
- **Snapshots:** the oldest legacy formats load (87 of 366 shared snapshots failed in the
  converter), LinuxSampler SFZ chains load with sfizz, a vanished MIDI device no longer fails a
  load, load progress in the state manager, bankless mode and bank deletion select the right bank,
  the state manager import cycle broken (`d4b2b4010`, `158772d33`, `75c105609`, `e4fda9c44`,
  `4e84e2ae6`, `06e28ba88`, `acdd51380`).
- **Engines:** interactive shells with TERM=dumb, Aeolus and setBfree end the busy state when their
  start fails, Aeolus opens its OSC server first, presets whose id is a list, the plugin UI type
  from lilv, the audio player's exit crash, ALSA mixer start-up (`1f0d3bafe`, `9b3775b21`,
  `89169dde3`, `2924b1759`, `0b52cf633`, `6683b91ac`, `45db12bd6`, `0234400f7`).
- **Tk UI and CUIAs:** MIXER/ZYNPOT_ABS with string arguments, SELECT without index, MIDI learn
  CUIAs by processor id and symbol, CHAIN_OPTIONS, MENU on special processors, pattern editor and
  ZS3 cursors, MIDI recorder rows, randomize within min/max, the 4-column main menu's MIDI Output
  (`d147201f3`, `b29fe401c`, `e9ea8e71e`, `2353054ca`, `08f4c463a`, `45cc706f6`, `e8065ea67`,
  `9a88a256c`, `914596d40`, `b85535322`).
- **Controller drivers and widgets:** launchpad_pro_mk2 sends mode, the samplv1 widget's module
  path (`7b73ebf37`, `293bcc38a`); APC40 mk2 and Behringer Motor unregistered their handlers
  correctly (de6ea448, 6a360d91: dropped in the rebase onto tomita 0c1098a6, see the entry
  there).
- **Robustness and tests:** signal manager unregister_all(), the websocket worker without WS LEDs,
  rebuild_midi_graph() releases its lock, the websocket test skipped where the server is stubbed,
  strict-xfail markers of fixed defects dropped (`8fe84d1bb`, `b811de35b`, `999700ed9`,
  `0c38f6f8b`). The per-fix status is in [upstream-candidates.md](../upstream-candidates.md).
