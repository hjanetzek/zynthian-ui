# Navigation: the screen history and BACK (Tk's rules, the Qt UI's mapping)

How zynthian's Tk UI (`zyngui/zynthian_gui.py`) moves between screens and what BACK does, and how
the Qt UI (`zynqt/ui.py`) maps each rule. Checked side by side in the compare VMs (Qt 2242, upstream
Tk 2243) on 2026-11-26.

## The history

**Tk.** `screen_history` is a stack of screen names that **includes the screen shown** (its top).
`show_screen(screen, hmode)`:

| hmode | used by | what |
|---|---|---|
| `SCREEN_HMODE_ADD` (default) | `show_screen`, `show_modal` | the screen is pushed; if it is in the history already, the history first **ends where it was** (`prune_screen_history(soft=True)`): BACK from it never returns to itself (chain control after a preset was chosen leaves chain control, not the preset list). Shown again on top: nothing changes |
| `SCREEN_HMODE_REPLACE` | `replace_screen` | the top is replaced (BACK skips the current screen): bank → preset with a single bank, preset → chain control after choosing, preset ↔ bank (switch 1, BANK_PRESET) |
| `SCREEN_HMODE_RESET` | `show_screen_reset` | the history is only this screen: CUIA `SHOW_SCREEN`, `SCREEN_MIXER`, BACK:B, switch 1 bold, a new chain (`modify_chain`), start-up |
| `SCREEN_HMODE_NONE` | | not recorded: the empty preset list's options (`cuia_bank_preset`), the pattern editor's info lists |

Also: `purge_screen_history(name)` removes every entry of a screen (the preset list chosen:
`"bank"`, so BACK from chain control doesn't return to the banks); `reset_screen_history()`.

`close_screen()` removes the current screen and everything above it (`prune(soft=False)`), pops the
previous one and shows it (ADD); an empty history, a missing screen, the mixer or the launcher
become `"root"`, which is the mixer or the launcher, whichever was shown last
(`mixer.launcher_mode`). `back_screen()` = the screen's `back_action()` first (True: handled),
else `close_screen()`.

**The options list** (`"option"`, `zynthian_gui_option`) is one screen that every caller
configures anew (pattern options, admin settings, bank / preset / snapshot options, ...). Choosing
an entry closes it (`close_on_select`, the default) before the callback runs, so a callback that
shows another screen shows it over the opener. Since 2026-11-26 (strand 01, `SHARED_SCREENS`) an
options list shown again **drops the older entry** from the history instead of ending the history
there; before, pattern editor → MENU (its options) → MENU (the main menu) → Admin → Touch
Navigation: BACK or choosing the current value returned to the pattern editor.

**Qt.** `screen_history` holds the **previous** screens only (not the current one; at most 20);
`show_screen(name, history=True)` pushes the current screen, then ends the history at `name` if it
is in it (Tk's prune). `replace_screen` = `history=False` (Tk's REPLACE: the current screen isn't
recorded), `show_screen_reset` (RESET), `purge_history` (purge), `close_screen` (pop; the mixer
without history). `NO_HISTORY_SCREENS = ("option",)`: the options list is never recorded, so a
screen shown from it returns to its opener and the next options list can't cut the history at an
old one (4c3e840ca: the same bug as Tk's above, reported as "Controller Settings > Hardware
Setup > LED Brightness: BACK went to the step sequencer").

## BACK, the inputs

| input | Tk | Qt |
|---|---|---|
| CUIA `BACK` (V5 BACK key, `BACK S` / `BACK B`, websocket, OSC) | `cuia_back`: `B` → `show_screen_reset("root")`; else `back_screen()`. The screen's `cuia_back` comes first (the mixer: `B` = chain manager) | `cuia_back`: the same; the screen's `cuia_back` first (`_run_cuia`, `MixerNav.cuia_back`) |
| switch 1 short (V4 / Z2 kits' BACK, keyboard Escape / Backspace = `ZYNSWITCH 1`) | the screen's `switch(1, "S")` first, else `back_screen()` | `zynswitch(1, "S")`: the screen's `switch()` first (not while a dialog is shown), else `back()` |
| switch 1 bold | screen `switch` first (chain control, chain manager, mixer: main menu; pattern editor: edit history), else `show_screen_reset("root")` | the same (`MixerNav.switch`, `ChainManager.switch`, chain control, pattern editor) |
| switch 1 long | power menu | power menu |
| title bar tap on the options list | `back_screen()` | (not checked) |

So in Tk the kit's BACK switch and the V5's BACK key differ where a screen overrides
`switch(1, "S")`: only the **preset list** does (below).

**A custom switch's short press on its own screen** (Tk: `custom_switch_ui_action`,
`check_current_screen_switch`, "BIG ÑAPA"): a short press runs the key's **bold** action when the
bold action is `BANK_PRESET` and the bank list, the preset list or the audio player is shown, when
the short action ends with the shown screen's name (`CHAIN_CONTROL` in chain control,
`SCREEN_ZS3` in the ZS3 list, `SCREEN_AUDIO_MIXER` in the mixer, `SCREEN_LAUNCHER` in the
launcher), or when it is `MENU` in the main menu or the chain manager. It comes before ALT's
actions. On a V5 (and the Duet's keypad, the same v5 profile) the CTRL key (`CUSTOM_SWITCH_03`:
short `CHAIN_CONTROL`, bold `BANK_PRESET`) therefore walks chain control → the presets → the banks
→ back, as the V5 manual says ("Short press CTRL button to access the bank list. Short press CTRL
again to exit bank/preset selection"). Qt: `cuia__zynswitch` with `keypad_leds.current_screen_switch`
on the Tk screen names (`get_current_screen`); the F-key labels use the same rule. Until
2026-11-26 the Qt UI lacked the `BANK_PRESET` clause and "menu" in the chain manager: short CTRL
in the preset list reopened chain control, and on the Duet (no switch 1, no knobs) the bank list
was out of reach.

## BACK per screen (back_action → Qt back())

The screen's own step comes first; when it returns False the screen closes (history).

| screen | Tk `back_action` | Qt |
|---|---|---|
| any with the top-bar parameter editor | closes the editor (`zynthian_gui_base`) | the value editor is an overlay (below) |
| mixer | ends chain / phrase moving, closes the param editor, else **toggles the launcher mode** (mixer ↔ launcher; never closes) | `MixerNav.back`: the launcher (no history); move modes are overlays |
| chain control | the sub-screen's first (control: MIDI learn off), then hides the chain blocks (select mode) | `ChainControl.back`: MIDI / note learn off, then select mode off |
| chain manager | ends processor / chain moving | move modes are overlays |
| engine list | "show all" off (saves the engine info) | the same |
| bank | (none: the history) | the same: BACK leaves the list, also from a sub-folder (`Bank.up_level`, Tk's `browse_back`, is BANK_PRESET's and ARROW_LEFT's step) |
| preset | (none: the history, chain control or the bank list); **switch 1 short: `replace_screen("bank")` with more than one bank**; switch 2 short: favourites | `Preset.switch`: the same, also from the flat list (since 2026-11-26: it left the list, and the bank list was then out of reach on a V4 kit); BACK leaves the list, also from a sub-folder; switch 1 shows the banks from a sub-folder too (as Tk); `Preset.up_level` (`browse_back`) is BANK_PRESET's and ARROW_LEFT's step |
| ZS3 | PC learning off, ends ZS3 moving | the same |
| pattern editor (pated) | clears the selected notes, leaves block / multi edit mode, else the history | `PatternEditor.back`: the same |
| key range | MIDI learn off (then the history); SELECT goes back too | (QML screen, not checked) |
| file selector | up a directory (inside the root dirs) | the same |
| help | back in its link history, closes the link selection | an overlay: BACK closes it |
| info (command output) | kills the command | (no such screen) |
| options list | (none) | (none) |
| controller settings (Qt only: Admin > Controller Settings) | (Tk has no such screen) | up a level: setting list → categories → drivers, then the history |

**BANK_PRESET** (the PRESET key): from the bank list back (or up a sub-folder); from the preset
list up a sub-folder, else the bank list (more than one bank, REPLACE) or back; elsewhere the
presets if there is a preset list, else the banks, else the empty preset list's options.
Qt: `cuia_bank_preset`, the same (the flat list counts as a preset list). The sub-folder steps
(`Bank.up_level`, `Preset.up_level`) go up one folder, as Tk's `browse_back` (the parent's info,
the folder left selected). Only BANK_PRESET (and ARROW_LEFT, below) takes them: BACK and switch 1
behave as in a list without folders, as Tk's (until 2026-11-26 Qt's BACK went up the folders
first, and left every folder at once). In the audio player's file lists BANK_PRESET keeps the
audio player (Tk's `is_shown_audio_player`: the current processor; Qt switched to the active
chain's processor there until 2026-11-26).

## Arrows left / right in lists (a Qt experiment, navigation only)

The rule for the Qt UI is Tk's behaviour (the user, 2026-11-26: "it should always work like tk
does. using additional unused keys is ok where it makes sense (the arrow buttons are an
experiment)"). The arrows in lists are such an addition: they only navigate, they never do
what Tk's keys wouldn't.

**Tk.** The lists have no `arrow_left` / `arrow_right`: they do nothing in the bank and preset
lists, the menus and the options list.

**Qt** (`SelectorScreen.navigate`), in a list (`kind` "list", no categories):

- **ARROW_LEFT** goes one level back: in a bank / preset sub-folder up one folder (the screen's
  `up_level()`, BANK_PRESET's `browse_back` step), else as switch 1 short (Tk's BACK on the kits):
  the screen's `switch(1, "S")` first (the preset list, flat or not → the bank list with more
  than one bank), else `ui.back()` (the screen's `back()`: the controller settings' levels, up a
  file selector directory; then the history: the bank list → where it came from, e.g. chain
  control; the options list → its opener, as it is never recorded). So in a preset folder:
  ◀ up the folders, then the bank list, then back.
- **ARROW_RIGHT** enters the selected entry, as SELECT short, **only when it opens a level** (a
  submenu, another list, a folder) and changes nothing (`SelectorScreen.enters(index)`: the
  entry's `level` flag, `entry(..., level=True)`; the data-row screens override it). Anywhere
  else it does nothing: it never loads a preset or a snapshot, runs an option, toggles or picks a
  setting, starts a test or a move.

What ▶ enters:

| screen | ▶ enters | ▶ does nothing on |
|---|---|---|
| Admin | Controller Settings, Hotplug USB Audio | the toggles (Program Change => ZS3, ...), the value pickers (Global Transpose, Main Output, Theme, Touch Navigation, ...), Test MIDI / Audio, Restart UI, Exit |
| controller settings | a controller, a category | a setting (its editor) |
| chain options | Add MIDI-FX / Audio-FX processor (the engine list), Chain controller pages... | Remove, Clean MIDI Learn, Move, Rename, Export, Remove chain |
| processor options | Presets, Insert MIDI / Audio Processor | Bypass, Plugin GUI, Move, Replace, Reload, Remove, Randomize, Clean MIDI-learn, Info |
| bank list | a bank, the favourites, a sub-folder | the empty list's hint (scan again) |
| preset list | a sub-folder (the audio player's folders) | a preset (flat list: nothing) |
| snapshots | a snapshot bank | "..", New Bank, Save as new snapshot, a snapshot (its options load it) |
| file selector | a directory | a file |
| options list, ZS3, MIDI channel, routing, MIDI CC, MIDI recorder | (nothing) | every entry |

Why: the touch keypads have no switch 1 (the Duet: the docked keypad, V5 layout, no knobs). Their
BACK key sends the BACK CUIA, which leaves the preset list as in Tk, and the user found no way back
to the bank list ("I'm ok if we use the arrow left, right buttons to go back from and into a
menu"). Tk's own way there, CTRL short in the preset list (above), is mapped too.

Unchanged (as before, and as Tk where it has the screen):

- grids (the main menu, add chain): left / right move;
- category lists (the engine list, `set_categories`): left / right switch the category;
- the overlays first (`ui._navigate`): help, processor / chain moving, the value editor (left /
  right step), the keyboard, the confirm dialog;
- the screens with their own `navigate` (not lists): mixer (`MixerNav`), launcher, chain control,
  chain manager, pattern editor, X-Y control.
- The **flat preset list** moved from group to group with left / right before; now left is the
  bank list and right does nothing (a preset). Groups: the group knob (knob 1, `GROUP_KNOB`) and
  touch scrolling.

The `SelectorScreen` subclasses: none overrides `navigate` except `Preset` (the group jumps, now
removed); `Engine` has categories; `MainMenu` and `AddChain` are grids. `Bank`, `Preset` and
`ZS3` have a `switch` (only `Preset` takes switch 1); `FileSelector`,
`ControllerSettings`, `Engine` (show all off) have a `back`, `Bank` and `Preset` an `up_level`
(their sub-folders); left takes those steps. `Bank`,
`Preset`, `Snapshots` and `FileSelector` override `enters`; `Admin`, `ControllerSettings`,
`ChainOptions` and `ProcessorOptions` flag their level entries. `ARROW_PREV` / `ARROW_NEXT` are
ARROW_LEFT / RIGHT (as in Tk).

**The snapshot list** keeps Tk's behaviour: its bank level is an entry (".."), not a `back()`, so
inside a bank BACK and ◀ leave the snapshots (Tk's BACK does the same); ▶ doesn't take "..".

## Dialogs and modal screens

In Tk the confirm dialog, the keyboard, the info and loading screens are screens of their own
(in the history); in Qt they are overlays, closed first by BACK in this order: help, processor
moving, chain moving, value editor (cancel), keyboard (cancel), confirm (No); then the screen's
`back()`; then `close_screen()`. A value chosen in the value editor (Tk: the param editor in
the top bar) returns to the screen below; the options list closes before its action runs
(`Options.select_action`: `ui.back()`, then the action).

## Tests

- `tests/unit/test_screen_history_options.py` (Tk: an options list shown again),
- `tests/unit/test_qt_controller_settings_stay.py` (Qt: settings chosen / BACK after the pattern
  editor's menu),
- `tests/unit/test_qt_preset_back_to_banks.py` (Qt: switch 1 in the preset list, flat or not),
- `tests/unit/test_qt_modify_chain_history.py` (Qt: BACK after adding a chain or a processor),
- `tests/unit/test_qt_custom_switch_screen.py` (Qt: a custom switch's short press on its screen,
  the V5's CTRL key),
- `tests/unit/test_qt_list_arrows.py` (Qt: left / right in lists, grids, category lists; what
  ▶ enters),
- `tests/unit/test_qt_preset_subdirs.py` (Qt: the bank / preset sub-folders: BANK_PRESET and
  ARROW_LEFT up one folder, BACK and switch 1 as Tk).
