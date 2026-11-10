# Qt UI: hardware input (encoders, switches) on zynthian kits

Analysis and plan, 2026-11-10. Context: on the Pi 4 with the V4-type kit (zyncoder-hw build
`MCP23017_ZynScreen`) the hardware works (MCP23017 interrupts fire, zyncore sets up 8 switches
and 4 encoders), but the Qt UI reads none of it. On the Duet and the desktops zyncore is the
generic `DUMMIES` build, which has no switches or encoders at all.

Sources: `zyngui/zynthian_gui.py` (control loop), `zynthian_main.py` (encoder callback),
`zyngui/zynthian_gui_config.py` (wiring, switch config, touch keypad remap),
`zyngui/zynthian_wiring.py` (switch MIDI set-up, shared with Qt), zyncoder (`zyncoder.c`,
`zynpot.c`, `zyncontrol_vx.c`, `zyncontrol_v5.c`, `zyncontrol_none.c`, `CMakeLists.txt`),
zynthian-sys `config/wiring-profiles/`, `config/zynthian_envars_V4.sh`.

## 1. How the Tk UI reads the hardware

### zyncore (C)

- **Build per wiring layout.** `CMakeLists.txt` picks a control file per
  `ZYNTHIAN_WIRING_LAYOUT`: `zyncontrol_vx.c` for the MCP23017/MCP23008 layouts (V4,
  ZynScreen, custom), `zyncontrol_v5.c` (V5), `zyncontrol_z2.c` (Z2), `zyncontrol_mini_v2.c`,
  and `zyncontrol_none.c` for `DUMMIES` / `TOUCH_ONLY`. `zyncore.py` loads the kit's build
  from `ZYNTHIAN_LIB_DIR/hw/<layout>/libzyncore.so` first (Nura's zyncoder-hw).
- **Switches** (`zyncoder.c`): the MCP23017 interrupt (wiringPi ISR thread, one per INTA/INTB
  pin) or a GPIO ISR calls `update_zynswitch()`: debouncing (< 1 ms ignored), the push sets
  `push=1` and a timestamp, the release stores the duration in `dtus`. **MIDI events of a
  switch are sent right there, in C** (`send_zynswitch_midi`: CC, note, program change, clock,
  transport, CV/gate via zynaptik), once `setup_zynswitch_midi()` configured them. There is no
  switch callback: the UI polls `get_zynswitch(i, long_us)`, which returns 0 once after a push,
  the duration once after the release, the running duration once if the switch is held longer
  than `long_us` (and then forgets the press: the release returns nothing), else -1.
- **Encoders** (`zyncoder.c`, `zynpot.c`): the ISR decodes the quadrature, scales by the
  encoder's `step` (`setup_behaviour_zynpot(i, step)`: `step > 0` fixed, `0` speed-based
  acceleration, up to ×4 below 40 ms per detent) and calls the callback set with
  `setup_zynpot_cb(cb)` as `cb(i, delta)`, **from the ISR thread**. The default step after
  `setup_zyncoder()` is 1.
- **Counts**: `get_num_zynswitches()` is the length of `ZYNTHIAN_WIRING_SWITCHES` (`vx`; pins
  of -1 count but aren't set up), 30 on V5 (keys 4–23, encoder pushes 24–27, EXT 28–29; 0–3
  unused), 34 on Z2. `get_last_zynswitch_index()` is the last *enabled* switch.
  `get_num_zynpots()` the encoders set up.
- **DUMMIES / TOUCH_ONLY** (`zyncontrol_none.c`, no `zyncoder.c` linked): `get_num_zynswitches()`
  = 28, `get_last_zynswitch_index()` = -1, `get_num_zynpots()` = 0, and the library has **no
  `get_zynswitch`, `setup_zynpot_cb`, `setup_zynswitch_midi`** (checked with `nm -D` on the
  local build). 28 only gives the UI 24 custom switch slots for the touch keypad.
- **Zynaptik** (CV/gate in/out, ADS1115/MCP4728) and **Zyntof** (VL53L0X distance sensors)
  run entirely in zyncore (their own threads); the UI only configures them
  (`setup_zynaptik_cvin/cvout`, `setup_zyntof`) and has the CUIAs for volts/octave and note 0.

### The Tk UI (Python)

| Thread | What it does |
|---|---|
| ISR (C) → `zynpot_cb` (`zynthian_main.py`, ctypes `CFUNCTYPE`) | adds the delta to `zynpot_dval[i]` under `zynpot_lock`, sets `zynpot_event` |
| `zynpot` thread (`zynpot_thread_task`) | waits for the event, takes and clears each `zynpot_dval[i]`, calls `screens[current].zynpot_cb(i, d)` **directly in that thread** (not Tk's main loop), sets the event flag (power save) |
| `Control` thread (`control_thread_task`), every 10 ms | `zynswitches()`: for each switch up to `last_zynswitch_index` (custom ones only if they have UI actions: MIDI switches are C-only), `get_zynswitch(i, long_us)`; result → `cuia_queue.put(("zynswitch", (i, timing(dtus))))` with `P` for 0, else `S` / `B` / `L` by `zynswitch_bold_us` (300 ms) / `zynswitch_long_us` (2 s). Also OSC receive, and `power_save_check()` every ~110 ms |
| `CUIA` thread (`task_cuia_thread`) | the switch state machine: `P` starts the press (or runs the push action and auto-repeats it every 150 ms after 3 intervals), `R` (keys, touch keypad) is timed here, `S`/`B`/`L` dispatch to `zynswitch_short/bold/long(i)`; a press held past the long time fires `L` from here (autolong); the push-rotate state (below) |

Dispatch (`zynswitch_short/bold/long/push`): the screen's `switch(i, t)` first (True:
handled); then the four standard switches (0: –/chain manager/help, 1: back/root/power,
2: MIDI learn/ZS3/snapshot, 3: `switch_select('S'/'B')`/all sounds off); from 4
`custom_switch_ui_action(i - 4, t)`: a short press on the key of the screen shown runs its bold
action (`check_current_screen_switch`), ALT mode takes `A<t>` first, then `t`.

**Push-rotate** (`zynpot_pr_state`, `zynpot2switch`): the push of an encoder's switch sets the
state to 1; a controller turned while it is held (`zynthian_gui_controller.zynpot_cb`, X-Y)
counts it up and nudges *fine*; the release then does nothing (`PR`), and the long press is
held off. `zynpot2switch` is `[0, 1, 2, 3]` on V4-type kits, the switches whose actions are
`V5_ZYNPOT_SWITCH` on V5 (24–27).

**Encoder behaviour**: controllers set `setup_behaviour_zynpot(i, step)`: step 1 for lists /
integers with ≤ 32 values, else 0 (acceleration); the mixer, pattern editor and keyboard
screens set their own. ALT mode also nudges fine.

**Custom switch configuration** (`config_custom_switches()`): for custom switch *NN*
(`ZYNTHIAN_WIRING_CUSTOM_SWITCH_NN`, switch index NN + 3): `UI_ACTION_PUSH` (P, AP),
`UI_ACTION` / `UI_ACTION_RELEASE` (S, B, L, AS, AB, AL), or a MIDI type (`MIDI_CC`,
`MIDI_NOTE`, `MIDI_PROG_CHANGE`, clock/transport, `CVGATE_IN/OUT`, `GATE_OUT`,
`MIDI_CC_SWITCH`) with channel ("Active": the active chain's), number, value.
`zynthian_wiring.wiring_midi_setup(chan)` hands the MIDI ones to zyncore; Tk calls it at start
(`create_screens`) and on every active chain change (`cb_set_active_chain`), and webconf's
`RELOAD_WIRING_LAYOUT` re-reads all of it.

**Layouts and the touch keypad.** The graphic layout is `Z2` for Z2 / V5 / TOUCH_ONLY, else
`V4` (`ctrl_order`). `ZYNTHIAN_UI_TOUCH_NAVIGATION` (`v5_keypad_left/right`; forced for
TOUCH_ONLY, i.e. DUMMIES) shows Tk's touch keypad (`zynthian_gui_touchkeypad_v5`: key *k* sends
`zynswitch k+4,P/R`). With touch navigation and fewer than 24 switch pins,
`zynthian_gui_config` **remaps at import, before `init_zyncore()`**: it loads the `v5` wiring
profile over the environment (custom switches 1–26: the keypad's actions) and rewrites
`ZYNTHIAN_WIRING_SWITCHES` to `pins[0:4] + 24 × -1 + pins[4:8]` (Z2 layout: `24 × -1 +
pins[0:8]`), so the `vx` build reports 32 switches, the keypad owns 4–27 and a V4 kit's four
extra switches move to 28–31 (custom 25–28; the `v4_touch_stage` / `v4_touch_studio` profiles
give those program changes 1–4). The V4 envars ship `ZYNTHIAN_UI_TOUCH_NAVIGATION=""`: no
keypad, no remap, 8 switches.

**LEDs**: `zynthian_wsleds_v5` / `_z2` (WS281x strips on V5 and Z2) and
`zynthian_wsleds_v5touch` (the touch keypad's key colours). V4-type kits have none.

## 2. What the Qt UI has today

- **Init**: `zynthian_qt_main.py` imports `zynthian_gui_config` (so the touch keypad remap above
  runs too) and calls `init_zyncore()`: counts, custom switch actions, zynaptik/zyntof config,
  switch timing are all set as in Tk.
- **Switch timing and dispatch** (`ZynUI._cuia_task`, a thread): `zynswitch i,P/R` from the
  keypad (`pushSwitch`), key bindings and OSC; push actions with auto repeat; autolong;
  `ZYNPOT i,d[,P|R]` with repeat. Dispatch in the GUI thread (`_cuiaRequested`, queued):
  `cuia__zynswitch` → `zynswitch(i, t)` (standard four, the table of Tk's defaults) or the
  custom actions (bold on the current screen's key, ALT); `cuia__zynpot` → the screen's
  `zynpot(i, d)`, else the select encoder moves the list / navigates.
- **Per-screen hooks** (parity work): `zynpot` (chain control, mixer, launcher, chain
  manager), `switch` (chain control, mixer, launcher, chain manager, ZS3, bank/preset, engine),
  `switch_select`, `show_menu`, `back` (Tk's `back_action`), `cuia_v5_zynpot_switch`, `zynpot_abs`.
- **Keypad**: `Keypad.qml` (V5 layout, always available: docked, or as an overlay from the top
  edge, whatever `ZYNTHIAN_UI_TOUCH_NAVIGATION` says), `KeypadLeds` (the v5touch colours).

**Missing** (before `qt-hw-input`; 1–4 and 6 are done there, see section 3, Implementation):

1. Nothing polls `get_zynswitch` and nothing registers `setup_zynpot_cb`: no hardware input.
2. `wiring_midi_setup()` is never called at start or on active chain change (only by
   `RELOAD_WIRING_LAYOUT`): MIDI switches, Zynaptik CV and Zyntof stay unconfigured on a kit.
3. Push-rotate (`zynpot_pr_state`, fine nudge, no action on release) and fine nudge in ALT
   mode (`ChainControl` controllers' `nudge(steps)` has no `fine`).
4. `setup_behaviour_zynpot`: never called, so every encoder runs at step 1, no acceleration.
5. Pattern editor and the overlays (value editor, keyboard, help) have no `zynpot` of their own
   (the select encoder navigates); Tk's pattern editor uses all four.
6. `_cuia_task`: an explicit `S`/`B`/`L` after a `P` leaves the press pending, so a spurious
   `L` follows 2 s later (only OSC clients sending `P` then `S` hit it today).
7. The touch keypad on a kit build: see section 4.
8. Hardware LEDs (V5, Z2), the `cv_config` screen (Zynaptik), Tk's `control_test` screen.

## 3. Design for the Qt port

### Where the loop runs

A small module `zynqt/hw_input.py` (no Qt in it, so it can be unit tested), owned by `ZynUI`,
started in `ZynUI.start()`, stopped first thing in `_do_exit()`.

- **Enabled only with a kit build**: `lib_zyncore` has `get_zynswitch` and
  `last_zynswitch_index >= 0` (switches), or has `setup_zynpot_cb` and `num_zynpots > 0`
  (encoders). DUMMIES has neither symbol and reports -1 / 0, so the Duet and desktops run
  exactly as now. `ZYNTHIAN_QT_HW_INPUT=0` turns it off for tests.
- **Switches: a Python thread polling every 10 ms**, as Tk's control thread. There is no
  switch callback in zyncore, and a Qt timer on the GUI thread would wake the render/GUI loop
  100 times a second and lag behind long frames. Cost: per cycle one ctypes call per switch
  that has UI actions (8 on the V4 kit, ≤ 30 elsewhere), about 1–2 µs each: ~0.2 % of a Pi 4
  core plus 100 GIL wake-ups/s; the Duet doesn't run it. A later improvement is a switch
  callback (or an eventfd) in zyncore, so nothing polls (an upstream zyncoder change).
- **Encoders: the zyncore callback, no polling.** As Tk: the ctypes callback (ISR thread)
  only adds the delta under a lock and sets an `Event`; a Python `zynpot` thread wakes, and
  hands over to the GUI thread. Unlike Tk it does not call the screen itself (Qt objects live in
  the GUI thread): it signals "deltas pending" once and the GUI thread takes all accumulated
  deltas when it runs (coalescing: a fast turn while the GUI is busy is one call with the summed
  delta, not a queue of stale events). No Qt call is made from the C thread. The callback object
  is kept referenced (else ctypes frees it: segfault), and set to NULL at exit before the
  interpreter goes down.

### How events enter ZynUI

- **Switches through `cuia_queue`**, so the keypad's state machine in `_cuia_task` times them
  and there is one path for keypad, keys, OSC and hardware. The poller sends `P` on the push and
  `R` on the release, with zyncore's debounced duration: `("zynswitch", (i, "R", dtus))`.
  `_cuia_task` uses that duration instead of its own clock when given. zyncore's own long
  detection is disabled (the poller passes `long_us` = 20 s, as Tk does while push-rotating),
  and `_cuia_task`'s autolong fires the long press; a release after that is ignored (the press
  is gone). This avoids a double long press (zyncore's `L` and the autolong both firing, which
  Tk's design allows: see issues).
- **Encoders straight to `cuia__zynpot(i, d)`** in the GUI thread (not through the queue: the
  queue thread adds latency and a hop per detent, and Tk doesn't route them through it either).
  The per-screen `zynpot` hooks take it from there.
- **Push-rotate**: `ZynUI.zynpot_pr_state` as Tk, with `zynthian_gui_config.zynpot2switch`. `P`
  of such a switch sets it to 1 (no push action); `cuia__zynpot` counts it up while it is > 0
  on the controller screens (chain control and its special processors, X-Y), the controller
  then nudges fine; `R` with a state > 1 does nothing; autolong waits while it is > 1. The
  state is a list of ints read by the CUIA thread and written by the GUI thread (GIL-atomic, as
  in Tk).
- **Thread safety**: everything that touches screens or Qt objects runs in the GUI thread
  (queued signals); the threads only touch zyncore, the queue, the delta list (lock) and
  `state_manager.set_event_flag()` (power save; Tk calls it from its threads too).
- **Switch MIDI**: `zynthian_wiring.wiring_midi_setup(active chain's channel)` once the start
  task is done and on `SignalBridge.activeChainChanged`, only with a kit build (DUMMIES has no
  `setup_zynswitch_midi`), wrapped in try (Tk doesn't wrap the chain-change call).
- **Encoder behaviour**: `setup_behaviour_zynpot(i, step)` when chain control assigns a knob's
  controller (Tk's rule: step 1 for ≤ 32 values / lists, else 0), and 1 elsewhere (lists,
  mixer level as Tk's mixer). Without it the kit works, only without acceleration.
- **Small kit screens** (ZynScreen 3.5", 480×320) are a separate item (qt-port-plan.md M3).

### LEDs

The V4-type kits have no LEDs (Tk starts `wsleds` only for the V5 and Z2 wiring layouts), so
nothing to do for the Pi 4 kit. **Open** for V5 / Z2: a hardware backend behind `KeypadLeds`
(which already computes Tk's colours per key) writing to the WS281x strip as
`zynthian_wsleds_v5` / `_z2` do; no kit to test with.

### Implementation

Branch `qt-hw-input` (prototype tested by the user on the Pi 4 kit 2026-11-10: works, encoder
pushes correct): `zynqt/hw_input.py` (switch poller, encoder callback), its wiring into `ZynUI`
(push-rotate, the `R` duration, the `S`/`B`/`L`-after-`P` fix, `wiring_midi_setup()` at start
and on chain change), fine nudge in chain control while push-rotating (controller screens only,
as Tk; ALT mode unchanged), encoder acceleration (`ZynUI.setup_zynpots()` after each screen
switch and on chain control's page / mode changes: the screen's `zynpot_steps()`, list screens by
their length; Tk's rules, see section 1), one `cuia_v5_zynpot_switch` (the Tk one:
`zynswitch(3, t)`, so the screen's switch hooks come first). Unit tests
`python3 -m unittest zynqt.tests.test_hw_input`. Off with the DUMMIES build (checked in the Qt
VM). `ZYNTHIAN_QT_HW_INPUT=0` off, `=log` logs every switch event and encoder delta. Not in it:
LEDs (V5/Z2), the X-Y screen's push-rotate and knobs, encoder behaviour for the chain manager
and the overlays (left as they are, as Tk leaves screens without their own).

## 4. The keypad on a kit build

The keypad sends custom switch *k* + 4 for key *k*, which matches the V5 numbering and the 24
custom slots DUMMIES reports. On a V4 build without touch navigation there are 4 custom
switches (the kit's four extra buttons, `v4_stage`: program changes): keys 0–3 trigger the
kit's buttons' actions under other labels, the other 16 do nothing.

Options:

| Option | What | Consequences |
|---|---|---|
| A. Tk parity | On a kit build show the keypad only with `ZYNTHIAN_UI_TOUCH_NAVIGATION` set (docked / overlay / Admin toggle hidden otherwise). With it set, `zynthian_gui_config`'s remap already gives 32 switches and the v5 actions, in Qt as in Tk | Nothing new to configure; webconf's touch navigation option decides as for Tk. The remap overwrites custom switches 25/26 with the v5 profile's `NONE` (an upstream bug, see issues), so with touch navigation the kit's first two extra buttons lose their actions unless that is fixed |
| B. Only the kit's switches | Show as many keys as custom switches exist | Four unlabeled keys on a V4: meaningless; no |
| C. Own actions | The keypad gets its own action table (the v5 profile's 20 key actions, or `ZYNTHIAN_TOUCH_KEYPAD_*` variables), dispatched as a separate source, independent of zyncore's switch count | Works with every build; the kit's own switch config stays untouched. New configuration that webconf doesn't know; differs from Tk; two places to edit the same V5 actions on DUMMIES unless DUMMIES keeps using the switch slots |

**Recommendation: A**, plus a fix of the remap (load the v5 profile only for the keypad's
slots 1–24, leave 25+ to the kit's profile), as an upstream candidate. Consequences:

- **Duet / desktops (DUMMIES)**: none. TOUCH_ONLY forces touch navigation, the keypad behaves
  exactly as now (docked or overlay), keys → switches 4–23 → the v5 actions.
- **V4 kit without touch navigation** (the default envars): no keypad; the four encoders and
  eight switches drive the UI as in Tk.
- **V4 kit with touch navigation** (webconf): keypad as on the Duet, the physical switches
  0–3 standard, the extra buttons at 28–31 with the `v4_touch_*` actions (after the remap fix).
  On a 480×320 screen the docked keypad takes a fifth of the width: probably overlay only.
- **V5 kit**: physical keys 4–23 and the touch keypad send the same switches (as Tk with touch
  navigation); hidden without it, as Tk.

C can still come later if the user wants a keypad on kits independent of webconf's setting.

## 5. Test plan

Without a kit:

- **Unit tests** (`uv run`, no Qt, no zyncore): the poller against a fake `lib_zyncore` (press,
  release within one poll, long hold past 20 s, switches without UI actions skipped, MIDI-only
  switches skipped); the encoder accumulator (two "ISR" threads, coalescing, exit); the
  detection (`get_zynswitch` missing → off).
- **`_cuia_task` timing**: run it against a stub object with a fake queue and a recording
  `_cuiaRequested` (short/bold/long from `R` with and without `dtus`, autolong, release after
  autolong ignored, push actions repeating, explicit `S` after `P` with no spurious `L`,
  push-rotate). Needs PySide6 for the import; on the host via the existing venv, or in the
  Qt QEMU VM.
- **DUMMIES regression** (desktop, Duet or the Qt VM): the log says hardware input is off; the
  keypad, key bindings and OSC `ZYNSWITCH` / `ZYNPOT` behave as before (the final-pass CUIA
  compare, `nura/tools/qemu_compare.sh`).
- **Emulated kit on the desktop**: none is cheap (zyncore's `vx` build needs wiringPi and I²C).
  A fake `lib_zyncore` injected with `ZYNTHIAN_QT_HW_INPUT=fake` driven by OSC would test
  the wiring into ZynUI, but adds test-only code: only if the Pi isn't available.

### Checklist for the Pi 4 kit

Start the UI with `ZYNTHIAN_QT_HW_INPUT=log` (in `~/.config/zynthian/zynthian_custom_config.sh`,
or the session's environment): each push / release and encoder turn is logged as
`Hardware input: switch i pushed / released after N ms` and `Hardware input: encoders [(i, d)]`,
so every button can be matched to its index. Short < 300 ms, bold 300 ms – 2 s, long ≥ 2 s (held:
fires at 2 s, once). Indices are zyncore's; the V4 positions are encoder/switch 0 top left,
1 top right, 2 bottom left, 3 bottom right (Tk's V4 layout: knob *i* turns the controller drawn
at its corner, `ctrl_order` 0, 2, 1, 3). Tick each box; note anything that differs from Tk.

**A. Start** (both settings)

- [ ] Log: `Hardware input: switches on (last index 7), encoders on (4)` (touch navigation on:
  last index 31)
- [ ] No `Traceback` in `~/.local/state/tinydm.log` after start, after a screen switch, at exit

**B. Encoders** (turn slowly, then fast: fast must accelerate where marked *acc*)

| Screen | Knob 0 | Knob 1 | Knob 2 | Knob 3 |
|---|---|---|---|---|
| Mixer | [ ] active chain level (*acc*) | [ ] its balance (*acc*) | [ ] main level (*acc*) | [ ] chain selection (one per detent) |
| Launcher (`SCREEN_LAUNCHER`) | [ ] as mixer | [ ] as mixer | [ ] phrase up / down | [ ] chain |
| Chain control, control mode | [ ] controller top left | [ ] top right | [ ] bottom left | [ ] bottom right |
| Chain control, select mode (SEL short) | – | – | [ ] processor | [ ] page (one per detent up to 32 pages) |
| Lists (main menu, bank, preset, snapshots, admin) | – | – | – | [ ] selection; long lists (> 32, e.g. presets) *acc* |
| Chain manager | | | | [ ] selection |
| Pattern editor | | [ ] zoom (*acc*) | [ ] row (*acc*) | [ ] step (*acc*) |

- [ ] Chain control: a controller with ≤ 32 values (a switch, a list such as a waveform) moves one
  value per detent even turned fast; a 0–127 or float controller accelerates
- [ ] Push-rotate: hold a knob's push and turn it in chain control: the controller moves fine; on
  release nothing else happens (no back / MIDI learn / select); held > 2 s while turning: no long
  press action
- [ ] Push-rotate elsewhere (mixer, lists): turning while held does what turning does, the release
  then runs the switch's action (as Tk: fine and suppression only on the controller screens)

**C. The encoder pushes (switches 0–3)**: the defaults (lists, menus, admin), then the
screens that change them (Tk's)

| Switch | Short | Bold | Long |
|---|---|---|---|
| 0 (top left) | [ ] nothing | [ ] chain manager | [ ] help, once |
| 1 (top right) | [ ] back | [ ] mixer (root) | [ ] power dialog, once |
| 2 (bottom left) | [ ] MIDI learn on / off | [ ] ZS3 (from ZS3: snapshots) | [ ] snapshots |
| 3 (bottom right) | [ ] select | [ ] bold select (the entry's options) | [ ] all sounds off |

- [ ] Mixer: 0 short the mixer toggle (`ZYNTHIAN_UI_MIXER_TOGGLE`, default record), 1 bold the
  main menu, 2 short mute of the active chain, 3 short its chain control, 3 bold its options
- [ ] Chain control: 0 short next chain, 1 bold main menu, 3 bold bank / preset; while MIDI
  learning bold on a knob's push: that controller's options

- [ ] In chain control, select (3 short) toggles control / select mode; in select mode 2 short
  opens the processor's options, 2 bold moves it
- [ ] In lists 3 short selects, 1 short goes back; in dialogs (confirm, options) 3 = yes / select,
  1 = no / back

**D. The four extra buttons (switches 4–7, custom switches 1–4)**, as configured in webconf's
wiring page; the profiles' defaults:

| Button (switch) | `v4_stage` short / bold / long | `v4_studio` short / bold / long |
|---|---|---|
| S1 (4) | [ ] PC 1 / [ ] PC 5 / [ ] all sounds off | [ ] audio file list / [ ] MIDI recorder / [ ] all sounds off |
| S2 (5) | [ ] PC 2 / [ ] PC 6 / [ ] all sounds off | [ ] launcher / [ ] pattern editor / [ ] all sounds off |
| S3 (6) | [ ] PC 3 / [ ] PC 7 / [ ] all sounds off | [ ] arrow up / [ ] arrow up / [ ] all sounds off |
| S4 (7) | [ ] PC 4 / [ ] PC 8 / [ ] TTS (Qt: "not in the Qt UI yet") | [ ] arrow down / [ ] arrow down / [ ] TTS (as left) |

- [ ] Short press on the button of the screen shown runs its bold action (`v4_studio` S2 on the
  launcher → pattern editor)
- [ ] ALT mode (from the keypad's ALT key): buttons with ALT actions run those (the profiles
  have none: the normal ones)
- [ ] One button set to a MIDI type (webconf: `MIDI_CC`, channel "Active"): the CC is sent (MIDI
  log / `aseqdump`) after start, and on the new chain's channel after changing the active chain

**E. Touch navigation** (webconf, UI options; restart the UI)

- [ ] Off (the V4 default): 8 switches; the Qt keypad as before (decision: it stays), its keys
  0–3 hit custom switches 1–4 (the extra buttons' actions), the others nothing
- [ ] On: 32 switches; the keypad's keys do the V5 actions (as on the Duet); switches 0–3 as in C;
  the extra buttons are switches 28–31 (custom 25–28): with `v4_touch_stage` / `_studio` S3/S4
  run their actions, S1/S2 nothing (the upstream remap bug, see section 1 / issues); push-rotate
  in chain control doesn't register (the same bug: `zynpot2switch` = 24–27)

**F. Load**

- [ ] `nura/tools/thread_cpu.sh` with the UI idle: the `zynswitch` thread ~0.2 % of a core, the
  `zynpot` thread 0 when nothing turns

## 6. Risks and open questions

Risks:

- ctypes callback from the ISR thread: it must never raise or block (only the lock and the
  event), and must be unset at exit; a callback during interpreter shutdown crashes (as the
  audio player's did, be63e13b).
- Timing differs from Tk by design (one long press instead of possibly two; release durations
  from zyncore, autolong from the CUIA thread, which checks every 150 ms like Tk's).
- The keypad (option A) depends on `ZYNTHIAN_UI_TOUCH_NAVIGATION` on kits: a user who had the
  Qt keypad on the Pi loses it until they enable touch navigation.
- Untested on V5 / Z2 (RV112 pots on Z2, the V5 encoder pushes as custom switches 24–27).

Questions for the user:

1. Keypad on kits: decided 2026-11-10: it stays as it is for now. Open: fix the remap's
   overwrite of custom switches 25/26 in our tree?
2. Is `ZYNTHIAN_UI_TOUCH_NAVIGATION` set on the Pi 4 (the TODO's count of 8 says no)? Which
   wiring profile does it use (`v4_stage`, `v4_studio`, custom)?
3. Push-rotate fine nudge: decided, only on the controller screens as Tk (done).
4. Encoder acceleration: decided, per controller as Tk (done).
5. OK to make the switch poller's 10 ms (Tk's) the default, and to look at a zyncore switch
   callback upstream later?
