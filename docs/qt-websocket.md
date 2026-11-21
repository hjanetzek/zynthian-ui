# Qt UI: the websocket API

Since 2026-11-20 the Qt UI has the websocket server of upstream's Tk UI (port 8370,
`zynconf.ServerPort["websocket"]`). The protocol, streams and message formats are the same, so a
client (webconf's virtual keypad, upstream's `zynthian-operator` Claude skill, our agents) can't
tell the two UIs apart where they show the same thing.

## Design

- `zyngui/zynthian_websocket.py` (strand 05-tkabs): upstream's websocket code, moved out of
  `zyngui/zynthian_gui.py` unchanged as the mixin `zynthian_websocket_feedback`, used by both UI
  classes (`zynthian_gui` and `zynqt.ui.ZynUI`). It holds the server (`zynthian_websocket_server`),
  client and subscription handling, the input messages (CUIA, key, MIDI), and the five feedback
  streams with their sampling, diffing and threads. `websocket_server` is imported lazily: without
  it the UI logs an error and runs without websocket (the Tk UI used to fail at import).
- The toolkit's part is a small interface the UI implements (see the module docstring):
  `websocket_run_idle` / `websocket_run_later` (calls into the UI thread: Tk `after_idle` /
  `after`, Qt `GuiCaller.post` / `QTimer.singleShot`), `screen_state_current` (screen name and
  view), `get_screen_title`, `screen_state_watch` (Tk: the select path traces), `websocket_wsleds`,
  `websocket_key_event` (Tk: xdotool) and `websocket_cuia` (default: the CUIA queue).
- Qt (strand 07-qt):
  - `zynqt/ws_state.py`: the Qt screens as Tk's views (state keys, items, titles) and
    `ScreenStateWatch`, which connects the screens' Qt signals while someone is subscribed to
    `screen_state`. Any change asks for the full state (`cb_screen_state_full`); the shared code
    compares it with the state sent and sends only the differences: the same messages as Tk's
    partial updates (a removed part, e.g. the chain blocks hidden, sends the full state, as Tk).
  - `zynqt/ws_keys.py`: `{"key": ...}` as QKeyEvents for the QML window, with the native X11
    keycode and modifier bits the key bindings use (works on Wayland, unlike xdotool).
  - CUIAs go into the CUIA queue as OSC's do: the CUIA thread, then `_cuiaRequested` to the GUI
    thread (`_run_cuia`). ZYNPOT / ZYNSWITCH with arguments the CUIA thread doesn't accept are
    dropped here with a warning naming the client (`ws_cuia_args_ok`, the thread's own parsers
    `zynpot_params` / `zynswitch_params`: numbers or number strings, "1.0" too); the thread would
    log and skip them.
  - `wsled_state`: the touch keypad's LEDs (`KeypadLeds`), in LED order as Tk's v5touch emulation.
  - The mixer meters keep DPM enabled while `dpm_state` has subscribers (as the Tk mixer).

## Streams and screens

`wsled_state`, `dpm_global`, `dpm_state`, `chain_state`: the same code and data as Tk.

`screen_state` (screen name, title, view state):

| Qt screen | Reported as (Tk) |
|---|---|
| list screens (admin, snapshot, bank, preset, chain options, routing, zs3, option, midi_chan, ...) | `zyngui_selector` {items, selected}; section titles as `> TITLE` |
| engine | `zyngui_engine` {items, selected, categories {items, selected}} |
| main_menu, add_chain | `zyngui_selector_grid` {items, selected, columns}; placeholder cells `""` |
| chain_control | `zyngui_chain_control` {chain_blocks (in select mode, MENU), zyngui_selector: the controller pages} |
| tempo, alsa_mixer, audio_player | `zyngui_selector`: the controller pages (Tk's plain control screen) |
| confirm overlay | screen `confirm`, `zyngui_confirm` {text} |
| keyboard, help overlays; busy | screen `keyboard`, `help`, `loading` only |
| mixer, launcher, pattern_editor (`pated_cc` in CC mode), chain_manager, midi_key_range, control_xy | screen and title only, as Tk |

Screen names are the Tk names (`zynqt/screen_names.py`, as `SS_GUI_SHOW_SCREEN`); the title is
the top bar's text as Tk's select path: the snapshot on the mixer / launcher, the processor's
preset path on chain control, "Chain: ..." on the chain manager, the pattern editor's title.

## Differences and gaps

- Content, not format: the Qt UI's lists differ where its screens do (e.g. admin entries, the
  theme's flat preset list with all banks, the main menu's Clean asks a confirm instead of Tk's
  "Confirm Clean" grid).
- `columns` of the grid menus is the theme's grid (v4: 3), not Tk's 4: the arrows move by it.
- Chain options, MIDI and audio routing opened from a chain block are separate screens in Qt
  (`chain_options`, `midi_config`, `audio_in`, `audio_out`), Tk's are subscreens of
  `chain_control`.
- Messages Tk shows in the title (`SS_GUI_SHOW_MESSAGE`, mixer volume toasts) are the info box in
  Qt and not in the title. Qt's value editor overlay is not reported (the screen below is).
- No controller values (neither UI reports them).
- Nura has no package with `websocket_server` yet (pip `websocket-server`, pure Python): until one
  is added to nura-builds and zynthian-ui's dependencies the Qt UI on Nura runs without websocket.
  For tests copy the module into the VM's user site-packages
  (`~/.local/lib/python3.14/site-packages/websocket_server`).
- The skill's `cuias` step needs `zynagent/zynagent_tools.py`, which isn't in upstream's tree.

## Testing

`tests/unit/test_qt_websocket.py` (Qt screen states, diffs, signal connections, threads, CUIA
input through a real server, keys, LEDs) and upstream's `tests/unit/test_websocket_feedback.py`.
The server tests skip where `websocket_server` is stubbed (the test VM's venv): run them with the
module on `PYTHONPATH`. In a QEMU VM the websocket is forwarded (`run_qemu.sh -S`,
docs/qemu-testing.md); `zynctl.py --host localhost --port PORT` then drives the Qt UI.
