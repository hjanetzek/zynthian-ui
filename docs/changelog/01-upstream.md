# Changelog: 01-upstream, fixes for upstream

What strand 01 of `main` changes, newest entry first. The strand holds self-contained fixes that
apply directly on origin/tomita; it is offered upstream as zynthian/zynthian-ui#617 (branch
`hjanetzek:upstream-fixes` = `strand/01-upstream`). Its commits carry no Claude-Session lines and
the strand has no changelog commit of its own (it would land in the pull request): this file is a
changelog commit in strand 10, below 10's own. See [README.md](README.md).

## 2026-11-20: rebased onto tomita 0c1098a68: the APC40 mk2 end() and Behringer Motor reset_feedback() fixes (de6ea448, 6a360d91) dropped: upstream's CC feedback broker (d6d08865) rewrote both drivers and removed the code they fixed; the import-cycle fix's conflict with the broker import resolved; see rebase-onto-tomita-2026-11-20c.md

- `5a6665378` zyngine: break the state manager <-> chain manager / legacy snapshot import cycle

## 2026-11-20: An engine that fails to start (jalv exits or hangs before its prompt) fails the processor add cleanly: no hang, no empty chain

- `5aec8eb26` Chain manager: an engine that fails to start fails the processor add cleanly
- `cb164ca40` jalv engine: a jalv that exits or hangs at start fails the engine start
- `92f700483` GUI: a new chain whose processor fails to start isn't left empty
- `89b50d3e3` jalv engine: the output thread stops when jalv ends
- `2e8e49076` zynthian_lv2: test_lv2_plugin() returns when jalv ends before its prompt

## 2026-11-20: the strand when the changelog started

52 commits on tomita `6e0527a45`, written 2026-11-02 to 2026-11-20.

- **zynmixer:** no invalid free or stale buffers with solo, sends and period changes; no deadlock
  under pipewire-jack when a strip or send is removed; the Python binding calls the functions
  libzynmixer has (`59edfeca4`, `bc317ac54`, `9da50d826`).
- **zynseq bindings:** restypes for uint8_t, bool and int16_t results, the `offset` typo, the
  CHANNEL_CHARS comma, save_pattern, transport client ids, reset()/setState() clear the selected
  pattern, zynseq.h without undefined functions (`a373f5a24`, `9f1decd8d`, `392e7b5ac`,
  `a3619f3df`, `72dfaee6f`, `50d4f9006`, `68ee07dd2`, `83a804a55`, `72b8a0c72`).
- **Native code:** printf formats for 64-bit sizes and 32-bit ARM (`17a71b849`, `6c1d604d1`);
  invalid escape sequences in Python string literals (`3205dffdf`).
- **Snapshots:** the oldest legacy formats load (87 of 366 shared snapshots failed in the
  converter), LinuxSampler SFZ chains load with sfizz, a vanished MIDI device no longer fails a
  load, load progress in the state manager, bankless mode and bank deletion select the right bank,
  the state manager import cycle broken (`0a69d4880`, `ec3ec5035`, `cf9a393c4`, `19e91696e`,
  `00b63b917`, `d0cce7389`, `5a6665378`).
- **Engines:** interactive shells with TERM=dumb, Aeolus and setBfree end the busy state when their
  start fails, Aeolus opens its OSC server first, presets whose id is a list, the plugin UI type
  from lilv, the audio player's exit crash, ALSA mixer start-up (`efb62094b`, `0a6b9fa14`,
  `96a732f8f`, `712649fad`, `a85f5bb1c`, `0a8e1e3ae`, `4be32e685`, `d32688ea2`).
- **Tk UI and CUIAs:** MIXER/ZYNPOT_ABS with string arguments, SELECT without index, MIDI learn
  CUIAs by processor id and symbol, CHAIN_OPTIONS, MENU on special processors, pattern editor and
  ZS3 cursors, MIDI recorder rows, randomize within min/max, the 4-column main menu's MIDI Output
  (`6336fd624`, `12706a538`, `89578788a`, `9ca4ad34a`, `33b80ec85`, `59e98bd8c`, `83c16a310`,
  `b4c7c0b43`, `23587bf66`, `efa786c67`).
- **Controller drivers and widgets:** launchpad_pro_mk2 sends mode, the samplv1 widget's module
  path (`578aa82d0`, `fcc653d95`); APC40 mk2 and Behringer Motor unregistered their handlers
  correctly (de6ea448, 6a360d91: dropped in the rebase onto tomita 0c1098a6, see the entry
  there).
- **Robustness and tests:** signal manager unregister_all(), the websocket worker without WS LEDs,
  rebuild_midi_graph() releases its lock, the websocket test skipped where the server is stubbed,
  strict-xfail markers of fixed defects dropped (`91325d075`, `661ec6849`, `cbc67201b`,
  `6d040ddf3`). The per-fix status is in [upstream-candidates.md](../upstream-candidates.md).
