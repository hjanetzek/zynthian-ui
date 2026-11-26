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

## BACK per screen (back_action → Qt back())

The screen's own step comes first; when it returns False the screen closes (history).

| screen | Tk `back_action` | Qt |
|---|---|---|
| any with the top-bar parameter editor | closes the editor (`zynthian_gui_base`) | the value editor is an overlay (below) |
| mixer | ends chain / phrase moving, closes the param editor, else **toggles the launcher mode** (mixer ↔ launcher; never closes) | `MixerNav.back`: the launcher (no history); move modes are overlays |
| chain control | the sub-screen's first (control: MIDI learn off), then hides the chain blocks (select mode) | `ChainControl.back`: MIDI / note learn off, then select mode off |
| chain manager | ends processor / chain moving | move modes are overlays |
| engine list | "show all" off (saves the engine info) | the same |
| bank | (none: the history) | `Bank.back`: leaves a sub-folder (`bank_subdir_info`) |
| preset | (none: the history, chain control or the bank list); **switch 1 short: `replace_screen("bank")` with more than one bank**; switch 2 short: favourites | `Preset.switch`: the same, also from the flat list (since 2026-11-26: it left the list, and the bank list was then out of reach on a V4 kit); `Preset.back`: leaves a sub-folder |
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
Qt: `cuia_bank_preset`, the same (the flat list counts as a preset list).

**Arrows.** Tk's lists have no `arrow_left` / `arrow_right`: they do nothing in the bank and
preset lists. The Qt flat preset list moves from group to group with them (and the BACK knob).

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
- `tests/unit/test_qt_modify_chain_history.py` (Qt: BACK after adding a chain or a processor).
