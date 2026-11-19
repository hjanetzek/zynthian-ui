# Qt theme `v4`: zynthian V4 kit, 3.5" 480x320

Status 2026-11-17: implemented on branch `qt-theme-v4` (all screens reachable at 480x320 in the
QEMU VM, side by side with Tk's V4 layout; not yet checked on the Pi 4 kit). A theme for the V4-type kits (the Pi 4 kit in
`docs/qt-hardware-input.md`, 3.5" ZynScreen, 480x320), built on the base theme `tk` (the Qt UI's
base since 2026-11-16: `zynqt/qml/`). Keep the tk look and workflow; adapt the layout to the small
screen and the V4's controls. Don't copy the old Tk V4 layout one to one where it doesn't work.

## The hardware

From the wiki (Zynthian UI User Guide V1/V4) and Tk's layout `V4` (`zynthian_gui_config.py`,
`ZYNTHIAN_UI_GRAPHIC_LAYOUT=V4`, the default without Z2/V5/TOUCH_ONLY wiring):

- 480x320 landscape, resistive touch (ZynScreen). On the kit the panel is SPI: later probably
  Qt's software renderer on linuxfb (docs/qt-port-plan.md, "Raspberry Pi kits with SPI
  displays"), so **no shader effects** (`MultiEffect`, `layer.effect`) in this theme.
- Four knobs with push switches, **two on each side of the screen**:

  | Knob (Tk index) | Position | Name | Turn in the mixer | Short | Bold |
  |---|---|---|---|---|---|
  | 0 | top left | LAYER | chain level | solo | main menu |
  | 1 | bottom left | BACK | balance | mute / back | mixer (global) |
  | 2 | top right | LEARN / SNAPSHOT | main level | MIDI learn | snapshots |
  | 3 | bottom right | SELECT | chain / list select | control view | chain options |

  Long: LAYER step sequencer, BACK admin, LEARN all notes off, SELECT power off. Push durations:
  short < 0.3 s, bold 0.3–2 s, long > 2 s. (The Qt UI's switch table follows Tk's; check it
  against the V4 wiring profiles `v4_stage` / `v4_studio`.)
- Four extra buttons S1–S4 on later kits (by default MIDI program changes 1–4; webconf).
- The hardware has the controls (`ZYNTHIAN_UI_TOUCH_NAVIGATION` empty, 8 zynswitches; see
  qt-hardware-input.md), so the kit shows no on-screen keypad unless it is docked (Admin > Docked
  Touch Keypad, or a tap on the top bar's status area). Phones and other touch-only devices with
  v4 dock it.

## Layout rules

- **Controller widgets on both sides, next to their knobs** (Tk V4: `ctrl_pos` (0,0) (1,0) (0,2)
  (1,2), `ctrl_order` (0, 2, 1, 3), vertical, 23 % of the width each): knob 0 top left, 1 bottom left,
  2 top right, 3 bottom right; the list / page / main content in the middle column. Tapping a
  widget acts like pushing its knob.
- Where a screen shows what the knobs do (chain control, the mixer's selected strip, the pattern
  editor), the knob hints sit at the screen edge next to the knob.
- Top bar: Tk's rule below 800 px width (height H//10 = 32 px, title 1.1F); the title scrolls when
  too long (`ScrollingTitle.qml`). Status area as tk, narrower.
- Sizes from Tk's font formula (`tkFontSize`, `ZYNTHIAN_UI_SCALE` auto at 320 px height) as the tk
  theme does; check legibility at 480x320 and adjust tokens where tk's values don't fit.
- Every screen must reach all its entries on 480x320 (scrolling lists and grids); no element may
  depend on a touch-only control.

## Screens

- **Mixer:** tk strips, **8 strips + the main strip** visible at 480 px (narrow), scrolling with the
  selection. Knob
  hints at the edges: level (top left), balance (bottom left), main level (top right), select
  (bottom right).
- **Pads (launcher):** a **4x4 grid plus the main (master) column**: 4 chains x 4 phrases visible,
  the main strip's phrase column on the right; the view scrolls by 4 when the selection leaves it
  (chains horizontally, phrases vertically). Keep tk's pad look (colours, loop/play icons, the clip
  progress bars, the selected pad's yellow outline). Short legends (the chain's MIDI channel /
  short name).
- **Chain control:** page list in the middle column, the four controller widgets in the corners
  (two left, two right), as Tk V4; widget views (envelope, filter, audio file) take the middle
  column.
- **Lists (selector screens):** the list in the middle or the full width; the info pane only if it
  fits (probably not at 480 px: show the info text another way or drop it, decide per screen).
- **Main menu / add chain:** 3 columns (Tk's rule below 800 px), scrolling.
- **Pattern editor:** the grid as big as possible, the knob functions at the edges; no toolbar (tk).
- **Top bar, keypad:** the docked keypad as in every theme (off by default, `ZYNTHIAN_QT_KEYPAD`).
  Docked at 800x480 the content fits beside it (the mixer's 8 strips, chain control with the
  hints). At 480x320 it still fits but is tight: the keypad takes a fifth of the width and a sixth
  of the height, the strips get ~45 px, the labels get small; usable, not comfortable.

## Implementation

Files (`zynqt/qml/+v4/` unless noted):

- `Theme.qml`: tk's tokens (a copy of `zynqt/qml/Theme.qml`: keep the two in step), plus
  `tkAutoScale: false` (F is `ZYNTHIAN_UI_FONT_SIZE` unscaled, as Tk on a V4 kit: 14 there;
  Nura's session sets `ZYNTHIAN_UI_SCALE=auto`, which would give F = 7 at 320 px; a number as the
  scale still applies), `infoWidth: 0.23` (Tk's V4 `ctrl_width`), `dialogScale: 0.6`.
- `KnobHints.qml`: what the knobs do, in a column at each edge (upper half: the top knob, lower
  half: the bottom one; text along the edge, 0.7 F). A tap on a hint pushes that knob's switch
  with Tk's timing (short < 0.3 s, bold to 2 s, long): touch access to the switch functions
  without the keypad. Only v4's own files use it (no base version).
- `ChainControlScreen.qml`, `Controller.qml`: Tk's V4 layout: slot i at `ctrl_pos[i]` (0 top
  left, 1 bottom left, 2 top right, 3 bottom right), 23 % of the width, half the height each, a
  1 px gap; page list and widgets in the middle column; the side chain left of everything in
  select mode. Controllers drawn as Tk's vertical arc (`on_size_arc`, vertical case).
- `MixerScreen.qml` (hints + `V4Mixer.qml`), `V4Mixer.qml`: tk's mixer (a copy of
  `zynqt/qml/MixerScreen.qml`: keep in step) with 8 strips + main by default (Tk counts the main
  strip in "visible strips": 9; the admin's setting still applies), strips 48 px wide at 480 px:
  buttons, meters and the two-line vertical labels still fit. Launcher mode: 4 chains x 4 phrases
  + the main column, paged by 4 when the selection leaves the view (the last chain page ends
  with the last chain). Hints: level, balance (launcher: phrase), main, select (launcher: chain).
- `SelectorHints.qml`: the knob hints on list screens that set `knobHints` (the flat preset
  list: "group" on knob 1, "preset" on knob 3), the list and the info pane between them; other
  lists have no hints and keep their layout.
- `Theme.qml` `flatPresetList: true`: the preset list shows all banks (groups) as section titles
  with their presets under them, for sfizz and LV2 plugins (docs/qt-theming.md has the details).
  The BACK knob (knob 1, bottom left; unused in Tk's lists) turns from group to group, SELECT
  (knob 3) moves entry by entry, so all groups are reachable from the list itself (on the Pi the
  bank list was only reachable with a short push of BACK, which users didn't find).
  A short push of BACK leaves the list (no bank level); the BANK_PRESET CUIA still opens the bank
  list.
- `PatternEditorScreen.qml`: tk's `PatternEditorView` between the hints; the texts from
  `pattern_editor.py` `knobHints(editMode, ccMode)` (zoom, note, step; per edit mode and in the CC
  view).
- Shared, unchanged for tk and classic (scenes AE 0): `ThemeBase` tokens `tkAutoScale`,
  `dialogScale` (Main.qml's dialogs and the keyboard); `InfoPane`: Tk's half-size
  icon at the top left when the side is narrow (`get_icon`); `PatternEditorScreen.qml` split into
  the screen (a frame) and `PatternEditorView.qml` (tk's editor).

Fixes found on the way (Python, all layouts; identical with the Z2 layout):

- Chain control: knob i turns slot i (Tk's `zynthian_gui_control`); it went through `ctrl_order`,
  so on V4 knobs 1 and 2 were swapped.
- Launcher: the phrase knob is `ctrl_order[2]` as Tk (knob 1 on V4), not always knob 2.
- `zynConfig` (font size, scale, main menu columns) is read before the state manager's
  `load_config()` rewrites the environment from `zynthian_envars.sh`: the custom config's values
  reach the themes.

Decisions and deviations:

- Lists keep Tk V4's info pane (23 % of the width, half-size icon, Tk's font rule): it fits and is
  what Tk shows; long entries elide.
- Mixer: 8 + main (user's decision, replacing "about 5"); the knob hints cost 2 x 16 px.
- Pads: always 4 x 4 (the admin's visible launchers don't apply in v4).
- Presets: one flat list with the banks as section titles (sfizz, LV2), the BACK knob turns
  through the banks; Tk V4 has two levels (banks, then presets; BACK push from the presets to
  the banks). Other engines keep the two levels.
- The tempo screen keeps the Qt tempo view (decided deviation of tk).
- Dialogs (confirm, value editor, help, busy, info) and the on-screen keyboard: tk's, scaled by
  0.6.

Open:

- The selector counter under the info pane (bank / MIDI file) elides its label ("MIDI ...") where
  Tk shrinks the font.
- Hints show what turning does; what a push does is only known from the hardware labels.
- Check on the Pi 4 kit: legibility of 0.7 F hints and 48 px strips, resistive touch on the hints
  and the 42 x 31 px keyboard keys, linuxfb (no shader effects are used in `+v4/`).

## Selecting it

`ZYNTHIAN_QT_THEME=v4` (directory `zynqt/qml/+v4/` on top of the base; selectors per
`zynqt/theme.py`). On the kit the kiosk / `zynthian-fb` session sets it with the kit's config.

## Testing

QEMU at 480x320: `tools/qemu_compare.sh -g -R 480x320 start` (both VMs; `-W PORT` when the
webconf ports 8100/8101 are taken). The Tk VM with Tk's own V4 layout as the reference: in
`~/.config/zynthian/zynthian_custom_config.sh` `ZYNTHIAN_UI_GRAPHIC_LAYOUT=V4`,
`ZYNTHIAN_UI_TOUCH_NAVIGATION=""`, `ZYNTHIAN_WIRING_LAYOUT=MCP23017_ZynScreen` (the VMs' DUMMIES
wiring counts as TOUCH_ONLY, which forces Tk's touch keypad; the Python side only, no kit
hardware), and a real kit's sizes: `ZYNTHIAN_UI_FONT_SIZE=14`, `ZYNTHIAN_UI_SCALE=1`. The Qt VM:
the same plus `ZYNTHIAN_QT_THEME=v4` (the scale stays auto: v4 ignores it). Encoders and switches
through the CUIAs `ZYNPOT` / `ZYNSWITCH`, touch with zynthian-stuff's `vin.py` (`VIN_SIZE=480x320`).
Preview: `tools/qml_preview.py SCENE -t v4 -s 480x320` with `ZYNTHIAN_UI_FONT_SIZE=14`
(scenes in zynthian-stuff `ui-parity/tools/scenes/v4/`). Final check on the Pi 4 kit.
