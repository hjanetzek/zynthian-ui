# OSC interface

zynthian's UI listens for OSC messages on **UDP port 1370** (`zynconf.ServerPort["cuia_osc"]`).
Both UIs handle CUIA messages (Callable UI Actions: the same actions the switches, MIDI
"note → CUIA" mappings and key bindings trigger); the Tk UI also has a mixer namespace. Status:
2026-11-07, branch `nura` (tomita base).

Code: Tk `zyngui/zynthian_gui.py` (`osc_init`, `osc_cb_all`, the CUIA thread
`task_cuia_thread`); Qt `zynqt/ui.py` (`_start_osc`, `_osc_cb`, `_cuia_task`, `_run_cuia`).

## /CUIA/&lt;name&gt; — run a CUIA

```
oscsend localhost 1370 /CUIA/SCREEN_ADMIN
oscsend localhost 1370 /CUIA/ZS3_LOAD s "zs3-2"
oscsend localhost 1370 /CUIA/ZYNSWITCH ss 12 S
oscsend localhost 1370 /CUIA/PROGRAM_CHANGE ii 5 0
```

- The path is case-insensitive (`/cuia/screen_admin` works too); the name is a CUIA from the
  table below.
- The arguments become the CUIA's parameters, as sent (strings or numbers; the CUIAs convert
  what they need). Text configurations use the same CUIAs as `NAME p1,p2` strings (wiring
  configuration, key bindings, MIDI note mappings).
- **Busy**: while zynthian is busy (loading a snapshot, starting engines) messages are
  dropped, not queued.
- Every CUIA except `POWER_SAVE` counts as user activity (wakes the screen from power save).
- After each message autoconnect checks the audio and MIDI routing.
- **Dispatch**: the CUIAs run in a CUIA thread, one after the other. The screen shown gets
  them first (`cuia_<name>` of the screen object, in Tk also the screen's
  `callable_ui_action`); if it doesn't handle them, the UI's own `cuia_<name>` runs. So
  e.g. `TOGGLE_PLAY` plays the pattern in the pattern editor, the MIDI file on the MIDI
  recorder screen, the audio player elsewhere.
- **Switches and encoders**: `ZYNSWITCH i,t` emulates switch `i` (0–3 the standard ones,
  from 4 the custom switches of the wiring configuration; custom switch *NN* is index
  *NN*+3) with `t` = `P` (press) / `R` (release) / `S` (short) / `B` (bold) / `L` (long); press
  and release are timed into short / bold / long, push actions run on press and repeat while
  held. `ZYNPOT i,d[,P|R]` turns encoder `i` by `d`; with `P` it repeats until `R` (keys).
- **Response** (Tk only): after a CUIA with a result, Tk sends `/cuia_response <result>` to
  **localhost:1371**, not to the sender. The Qt UI sends nothing back.

## /MIXER/… and /DAWOSC/… — mixer (Tk only, broken)

Meant for remote mixers: `/MIXER/HEARTBEAT` or `/MIXER/SETUP` registers the sender to receive
meter data (dropped after the heartbeat timeout), `/MIXER/<CHAN|BUS>/<PARAM><n> f|i` sets
`LEVEL`/`VOLUME`/`FADER`, `BALANCE`, `MUTE`, `SOLO`, `MONO` of strip `n`. On the current code
it doesn't work: the strip number is parsed from the wrong part of the path (`part2[5:]` of
`BUS/LEVEL0` instead of the parameter), and zynmixer has no OSC client functions any more
(`addOscClient` is gone from `mixer.c`), so registering fails. Not ported to the Qt UI
(see docs/upstream-candidates.md).

## Other OSC ports (internal)

Engines talk OSC to their own processes; not meant for external control:

| Port | What |
|---|---|
| 1370 | zynthian UI (this document) |
| 1371 | Tk's `/cuia_response` target |
| 6688 | LinuxSampler |
| 6693 | ZynAddSubFX |
| 9000 | Aeolus |
| 9951 | SooperLooper |
| 3000 + 10 × processor id, +1 | Pure Data patches with OSC controllers: to the patch, back to zynthian |
| random | other engines' reply servers (`zynthian_engine.osc_init`) |

(`zynconf.ServerPort` also lists the non-OSC ports: webconf 80/443, VNC 5900/5901,
Pianoteq RPC 9001.)

## CUIAs

All CUIAs of the two UIs, generated from the code (methods `cuia_<name>`; Qt's ZYNSWITCH /
ZYNPOT are handled in its CUIA thread). The description is the method's docstring, where it
has one. Regenerate with the script in the comment at the end.

| CUIA | Tk | Qt | Description |
|---|---|---|---|
| `ACTION_MIDI_UNLEARN` | ✓ | ✓ |  |
| `ADD_CHAIN` | ✓ | ✓ | Show add chain menu. |
| `ALL_NOTES_OFF` | ✓ | ✓ | Stop all playing notes. |
| `ALL_SOUNDS_OFF` | ✓ | ✓ | Stop all playing notes, sequences and audio playback. |
| `API` | ✓ |  | Access the backend API |
| `ARROW_DOWN` | ✓ | ✓ | Arrow Down action. |
| `ARROW_LEFT` | ✓ | ✓ | Arrow Up action. |
| `ARROW_NEXT` | ✓ |  | same as ARROW_RIGHT |
| `ARROW_PREV` | ✓ |  | same as ARROW_LEFT |
| `ARROW_RIGHT` | ✓ | ✓ | Arrow Right action. |
| `ARROW_UP` | ✓ | ✓ | Arrow Up action. |
| `AUDIO_FILE_LIST` | ✓ | ✓ | same as SCREEN_AUDIO_PLAYER |
| `BACK` | ✓ | ✓ | Back action. |
| `BANK_PRESET` | ✓ | ✓ | Show presets selection view. |
| `BOLD_SELECT_ACTION` | ✓ | ✓ | Bold select action. |
| `CHAIN_CONTROL` | ✓ | ✓ | Show chain control view. |
| `CHAIN_OPTIONS` | ✓ | ✓ | Show chain options. |
| `CLEAN_ALL` | ✓ |  | Remove all chains and sequences. |
| `COPY` | ✓ |  |  |
| `DISABLE_MIDI_LEARN` | ✓ | ✓ |  |
| `DISABLE_MIDI_LEARN_CC` | ✓ | ✓ |  |
| `DISABLE_MIDI_LEARN_PC` | ✓ | ✓ |  |
| `ENABLE_MIDI_LEARN` | ✓ | ✓ |  |
| `ENABLE_MIDI_LEARN_CC` | ✓ |  |  |
| `ENABLE_MIDI_LEARN_PC` | ✓ | ✓ |  |
| `EXIT_UI` | ✓ | ✓ |  |
| `HELP` | ✓ |  | Show the contextual help screen. |
| `HIDE_CURSOR` | ✓ |  |  |
| `HIDE_SIDEBAR` | ✓ |  |  |
| `HIDE_TOPBAR` | ✓ |  |  |
| `LAST_STATE_ACTION` | ✓ |  |  |
| `LAYER_OPTIONS` | ✓ |  | same as CHAIN_OPTIONS |
| `MAIN_MENU` | ✓ | ✓ | Show the main menu. |
| `MENU` | ✓ | ✓ | Show contextual menu. |
| `MIDI_LEARN_CONTROL` | ✓ | ✓ |  |
| `MIDI_LEARN_CONTROL_OPTIONS` | ✓ | ✓ |  |
| `MIDI_UNLEARN_CHAIN` | ✓ | ✓ |  |
| `MIDI_UNLEARN_CONTROL` | ✓ | ✓ |  |
| `MIDI_UNLEARN_MIXER` | ✓ | ✓ |  |
| `MIDI_UNLEARN_NODE` | ✓ | ✓ | params: processor id, controller symbol (zynthian_gui passes both as one list, which |
| `MIXER` | ✓ |  | Set the specified mixer parameter to a given value. |
| `NOP` | ✓ | ✓ |  |
| `PASTE` | ✓ |  |  |
| `POWER` | ✓ |  | Poweroff the zynthian device. |
| `POWER_SAVE` | ✓ |  |  |
| `PRESET` | ✓ |  | same as BANK_PRESET |
| `PRESET_FAV` | ✓ |  | Show the favorite presets. |
| `PROGRAM_CHANGE` | ✓ | ✓ | PROGRAM_CHANGE n[,chan] (F1-F4 on the V5 keypad), n also "+" / "-": a program change on |
| `REBOOT` | ✓ |  | Reboot the zynthian device. |
| `REFRESH_SCREEN` | ✓ |  |  |
| `RELOAD_KEY_BINDING` | ✓ | ✓ | Re-read the computer keyboard bindings (webconf saves them) |
| `RELOAD_MIDI_CONFIG` | ✓ |  |  |
| `RELOAD_WIRING_LAYOUT` | ✓ |  |  |
| `RESTART_UI` | ✓ | ✓ |  |
| `SCREEN_ADMIN` | ✓ | ✓ | Show the admin view. |
| `SCREEN_ALSA_MIXER` | ✓ | ✓ | Show the audio levels (ALSA levels) view. |
| `SCREEN_AUDIO_MIXER` | ✓ | ✓ | Show the audio mixer view. |
| `SCREEN_AUDIO_PLAYER` | ✓ | ✓ | Show the global audio player view. |
| `SCREEN_CALIBRATE` | ✓ |  |  |
| `SCREEN_CHAIN_MANAGER` | ✓ | ✓ | Show the chain manager view. |
| `SCREEN_CLEAN` | ✓ |  |  |
| `SCREEN_CONTROL` | ✓ | ✓ | same as CHAIN_CONTROL |
| `SCREEN_LAUNCHER` | ✓ | ✓ | Show the launcher view. |
| `SCREEN_MIDI_RECORDER` | ✓ | ✓ | Show the MIDI recorder/player view. |
| `SCREEN_MIXER` | ✓ | ✓ |  |
| `SCREEN_PATTERN_EDITOR` | ✓ | ✓ | Show the pattern editor view. |
| `SCREEN_SNAPSHOT` | ✓ | ✓ | Show the snapshots view. |
| `SCREEN_ZS3` | ✓ | ✓ | Show the subsnapshots (ZS3) view. |
| `SCREEN_ZYNPAD` | ✓ | ✓ |  |
| `SELECT` | ✓ | ✓ | Select entry params[0] of the shown list (as zynthian_gui: an index, no action) |
| `SELECT_ACTION` | ✓ | ✓ | Select action. |
| `SET_TEMPO` | ✓ | ✓ | Sets the global clock tempo (BPM) for the Zynthian framework. |
| `SHOW_CURSOR` | ✓ |  |  |
| `SHOW_NAVIGATION_GRID` | ✓ |  |  |
| `SHOW_SCREEN` | ✓ | ✓ |  |
| `SHOW_SIDEBAR` | ✓ |  |  |
| `SHOW_TOPBAR` | ✓ |  |  |
| `START_AUDIO_PLAY` | ✓ | ✓ | Starts the global audio playback. |
| `START_AUDIO_RECORD` | ✓ | ✓ | Starts the global audio recording. |
| `START_MIDI_PLAY` | ✓ | ✓ | Starts the MIDI (SMF) playback. |
| `START_MIDI_RECORD` | ✓ | ✓ | Starts the MIDI (SMF) recording. |
| `STOP` | ✓ | ✓ | Stops the contextual playback action. |
| `STOP_AUDIO_PLAY` | ✓ | ✓ | Stops the global audio playback. |
| `STOP_AUDIO_RECORD` | ✓ | ✓ | Stops the global audio recording. |
| `STOP_MIDI_PLAY` | ✓ | ✓ | Stops the MIDI (SMF) playback. |
| `STOP_MIDI_RECORD` | ✓ | ✓ | Stops the MIDI (SMF) recording. |
| `TAP_TEMPO` | ✓ | ✓ |  |
| `TEMPO` | ✓ | ✓ | Show the tempo screen. |
| `TEMPO_DOWN` | ✓ | ✓ |  |
| `TEMPO_UP` | ✓ | ✓ |  |
| `TOGGLE_ALT_MODE` | ✓ | ✓ |  |
| `TOGGLE_AUDIO_PLAY` | ✓ | ✓ | Toggles the global audio playback. |
| `TOGGLE_AUDIO_RECORD` | ✓ | ✓ | Toggles the global audio recording. |
| `TOGGLE_MIDI_LEARN` | ✓ | ✓ |  |
| `TOGGLE_MIDI_PLAY` | ✓ | ✓ | Toggles the MIDI (SMF) playback. |
| `TOGGLE_MIDI_RECORD` | ✓ | ✓ | Toggles the MIDI (SMF) recording. |
| `TOGGLE_PLAY` | ✓ | ✓ | Toggles the contextual playback action. |
| `TOGGLE_RECORD` | ✓ | ✓ | Toggles the contextual recording action. |
| `TOGGLE_SCREEN` | ✓ |  |  |
| `TOGGLE_SEQ` | ✓ |  |  |
| `TOGGLE_SIDEBAR` | ✓ |  |  |
| `TTS_ANNOUNCE` | ✓ |  | Announce a TTS message |
| `TTS_PAUSE` | ✓ |  | Pause current TTS announcement. Do not clear queue. |
| `TTS_REGISTER` | ✓ |  |  |
| `TTS_RESUME` | ✓ |  | Resume paused TTS queue. |
| `TTS_STOP` | ✓ |  | Stop current TTS announcement. Clear queue. |
| `TTS_TOGGLE_ENABLE` | ✓ | ✓ | Toggle the TTS enabled state |
| `TTS_TOGGLE_PAUSE` | ✓ |  | Toggle TTS pause |
| `TTS_TOGGLE_PLAYBACK` | ✓ |  | Stop TTS if playing, else announce context info |
| `V5_ZYNPOT_SWITCH` | ✓ |  |  |
| `WORKFLOW_CAPTURE_START` | ✓ |  | Starts capturing workflow. |
| `WORKFLOW_CAPTURE_STOP` | ✓ |  | Stops capturing workflow. |
| `WORKFLOW_CAPTURE_TEXT` | ✓ |  | Includes a text note into the on-going workflow capture. |
| `Z2_ZYNPOT_TOUCH` | ✓ | ✓ |  |
| `ZS3_LOAD` | ✓ | ✓ |  |
| `ZS3_NEXT` | ✓ |  |  |
| `ZS3_PREV` | ✓ |  |  |
| `ZS3_SAVE` | ✓ | ✓ |  |
| `ZYNAPTIK_CVIN_SET_NOTE0` | ✓ |  |  |
| `ZYNAPTIK_CVIN_SET_VOLTS_OCTAVE` | ✓ |  |  |
| `ZYNAPTIK_CVOUT_SET_NOTE0` | ✓ |  |  |
| `ZYNAPTIK_CVOUT_SET_VOLTS_OCTAVE` | ✓ |  |  |
| `ZYNPOT` | ✓ | ✓ |  |
| `ZYNPOT_ABS` | ✓ |  |  |
| `ZYNSWITCH` | ✓ | ✓ |  |
| `ZYN_CC` | ✓ |  |  |

<!--
Regenerate the table: an ast walk over zyngui/zynthian_gui.py (class zynthian_gui) and
zynqt/ui.py (class ZynUI) collecting methods named cuia_<name> (not cuia__...) and aliases
`cuia_x = cuia_y`, with the first docstring line; mark ZYNSWITCH and ZYNPOT for Qt by hand.
-->
