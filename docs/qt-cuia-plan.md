# Remaining CUIAs in the Qt UI: plan

Status 2026-11-07. The Tk UI has 126 CUIAs, the Qt UI 74 (table: docs/osc-interface.md). This
plan covers the 52 missing ones. Rules: as Tk does it (read `zyngui/zynthian_gui.py`
`cuia_<name>` and what it calls), backend logic shared where it isn't trivial, a CUIA the Qt
UI can't do yet shows a short info instead of "not in the Qt UI" (`ZynUI.show_info`).
Implement in `zynqt/ui.py` (`cuia_<name>`) or, where the shown screen decides, as
`cuia_<name>` on the screen object (ZynUI tries the screen first, `_run_cuia`).

## 1. Backend actions (direct)

| CUIA | Do |
|---|---|
| RELOAD_MIDI_CONFIG | `state_manager.reload_midi_config()` (webconf sends it) |
| RELOAD_WIRING_LAYOUT | as Tk `reload_wiring_layout`: `zynconf.load_config()`, `zynthian_gui_config.config_custom_switches()` (+ zynaptik/zyntof config), zynswitch MIDI setup (webconf sends it) |
| ZS3_NEXT, ZS3_PREV | `state_manager.load_next_zs3` / `load_prev_zs3` (as Tk, cycle param) |
| CLEAN_ALL | confirm, then as Tk (`clean_all`), mixer screen after |
| LAST_STATE_ACTION | save or delete the last state as Tk's admin `last_state_action` |
| ZYN_CC | as Tk (CC to the active chain / zynswitch MIDI) |
| ENABLE_MIDI_LEARN_CC | as Tk: learn a CC for the controller given |
| TOGGLE_SEQ | as Tk (start/stop the sequencer / phrase) |
| ZYNAPTIK_CVIN_SET_*, ZYNAPTIK_CVOUT_SET_* | as Tk (lib_zyncore calls) |
| ZYNPOT_ABS | `zynpot_abs` on the screen if it has it, else chain control: set controller i to the absolute value |
| V5_ZYNPOT_SWITCH | as Tk (V5 encoder push: bold = X-Y touchpad if both axes set, else as switch) |
| API | read what Tk does; port if UI-independent |

## 2. Navigation and screens

| CUIA | Do |
|---|---|
| ARROW_NEXT, ARROW_PREV | as Tk (next/previous in lists, chain in mixer) |
| PRESET, PRESET_FAV | preset list / favourites of the current processor (`show_screen("preset")`, favourites mode) |
| LAYER_OPTIONS | chain options of the active chain |
| MIXER | as Tk (alias of the mixer screen CUIA) |
| COPY, PASTE | screen CUIAs as Tk (pattern editor: copy / paste pattern via clipboard params; elsewhere nothing) |
| HELP | a help view if feasible (Tk shows HTML help: `zynthian_gui_help`); else info |

## 3. System

| CUIA | Do |
|---|---|
| POWER, REBOOT | confirm (unless param CONFIRM, as Tk), save last state as Tk, then power off / reboot: on ZynthianOS as Tk; on desktop (`zynconf.desktop_mode`) info only; on Nura through logind (`loginctl poweroff` / `reboot`, no root needed for the session user) — detect, don't guess |
| POWER_SAVE | screen blanking: a black QML overlay that the next input (touch, key, switch, CUIA) removes; `state_manager.last_event_ts` as Tk; `POWER_SAVE 0` wakes |
| WORKFLOW_CAPTURE_START/STOP/TEXT | as Tk if UI-independent (capture log), else info |

## 4. Display (Tk layout features)

SHOW/HIDE_TOPBAR (hide the top bar), SHOW/HIDE_CURSOR (mouse cursor on the window),
SHOW/HIDE/TOGGLE_SIDEBAR (chain control's processor sidebar), TOGGLE_SCREEN, REFRESH_SCREEN
(nothing needed: no-op), SCREEN_CALIBRATE and SCREEN_CLEAN (Tk touchscreen tools: info),
SHOW_NAVIGATION_GRID (Tk's grid overlay: info or a simple equivalent).

## 5. Speech

TTS_ANNOUNCE, TTS_PAUSE, TTS_REGISTER, TTS_RESUME, TTS_STOP, TTS_TOGGLE_PAUSE,
TTS_TOGGLE_PLAYBACK: no TTS in the Qt UI yet (ZynVoice postponed): info / no-op, one helper.

## Done when

All 126 names exist in `ZynUI` (or the screen objects), the table in docs/osc-interface.md is
regenerated (all ✓ for Qt), each group tested in the desktop preview where it shows something.
