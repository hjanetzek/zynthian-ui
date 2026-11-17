# Qt theme `v4`: zynthian V4 kit, 3.5" 480x320

Status 2026-11-17: design, not implemented yet. A theme for the V4-type kits (the Pi 4 kit in
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
- No on-screen keypad: the hardware has the controls (`ZYNTHIAN_UI_TOUCH_NAVIGATION` empty, 8
  zynswitches; see qt-hardware-input.md).

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
- **Top bar, keypad:** no on-screen keypad in this theme.

## Selecting it

`ZYNTHIAN_QT_THEME=v4` (directory `zynqt/qml/+v4/` on top of the base; selectors per
`zynqt/theme.py`). On the kit the kiosk / `zynthian-fb` session sets it with the kit's config.

## Testing

QEMU at 480x320: `nura/tools/qemu_compare.sh -R 480x320` (both VMs). The Tk VM with Tk's own V4
layout as the reference (`ZYNTHIAN_UI_GRAPHIC_LAYOUT=V4`, or V4 wiring); encoders and switches
through the CUIAs `ZYNPOT` / `ZYNSWITCH` (the VMs have no kit hardware). Final check on the Pi 4 kit.
