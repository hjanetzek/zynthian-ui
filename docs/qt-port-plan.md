# Starting the Qt Quick port: implementation plan

Status: plan, 2026-11-05; M0 done, M1 started (`zynthian_qt_main.py`, `zynqt/`). Follows [ui-reimplementation-plan.md](ui-reimplementation-plan.md),
which chose Qt Quick (QML) with the Python backend in-process (PySide6). This plan covers how to
start: what to build first, how it runs on the Lenovo Duet, and what decides the open questions.

## Why now

- Zrythm's Qt Quick UI runs fast and draws correctly on the Duet (native Wayland, OpenGL ES on
  Panfrost), while Tk under XWayland needs glamor turned off to draw correctly
  ([nura-display.md](nura-display.md)) and takes 37–76 ms per screen switch.
- The Zrythm port (`~/bastel/github/zrythm/tools/nura`) already packages Qt 6.12 for Nura and has
  it installed on the Duet: `qt6-qtbase` (with the Wayland platform plugin),
  `qt6-qtdeclarative` (Qt Quick, Quick Controls), `qt6-qtwayland`, `qt6-qtsvg`,
  `qt6-qtshadertools`, `qt6-qtcanvaspainter`.

## What Zrythm shows on this device

Reference: `~/bastel/github/zrythm`, `tools/nura/postmarketos-ui-zrythm/` and `src/gui/`.

- **Session:** a native Wayland client (`QT_QPA_PLATFORM=wayland`, no XWayland), in labwc. The
  session script rotates the panel from its DRM "panel orientation" (`drm_info` + `wlr-randr
  --transform 90`) and sets output scale 2: 1920×1200 becomes 960×600 logical pixels, close to
  the 1024×600 that zynthian's layouts are made for.
- **Rendering:** Qt's default RHI backend (OpenGL ES 3.1 on Panfrost); `QSG_RHI_BACKEND=vulkan`
  as an option.
- **Meters:** plain QML `Rectangle`s with a gradient, their height bound to a level property of a
  C++ object (`Meter.qml`, `MeterProcessor`); no custom drawing.
- **Dense drawing** (waveforms, MIDI clips, grids, spectrum): C++ items on Qt Canvas Painter
  (`QCanvasPainterItem` and `QCanvasPainterItemRenderer`, new in Qt 6.12), drawn on the GPU in the
  render thread.
- **Touch:** lists scroll by touch with `Flickable`/`ListView`; drag handlers that must not move
  the list need care (see the commits "scroll by touch" in Zrythm's history).

## Decisions

1. **PySide6, in-process.** The engine side (`zyngine`, state and chain managers, controllers,
   the zynlibs) stays as it is, in the same process. QML views bind to Python `QObject`s and list
   models. Engine callbacks arrive on other threads; they become Qt signals, delivered to the GUI
   thread as queued connections.
2. **PySide6 must match the device's Qt (6.12).** Alpine's `py3-pyside6` is 6.11.1, built
   monolithically against all of Qt 6.11 (3D, WebView, Location, …) and pulls in Qt 6.11 modules
   next to the device's 6.12 base, plus libclang. PySide and Qt modules use Qt's private API,
   which is tied to the minor version. So: package PySide6 6.12 for Nura, with only the modules
   needed (below).
3. **Native Wayland in the existing cage kiosk.** One full-screen window, no plugin windows: cage
   is enough (labwc is for Zrythm's plugin windows). cage rotates the panel but leaves the output
   scale at 1; the kiosk script sets it with `wlr-randr` for the Qt UI (`ZYNTHIAN_OUTPUT_SCALE`,
   default 1.5: 1280×800 logical pixels on the Duet). This takes XWayland and its glamor problem
   out of the picture.
4. **Side by side with the Tk UI.** A new entry point `zynthian_qt_main.py`; the launcher picks
   it with `ZYNTHIAN_UI=qt`. The Tk UI stays the default until the Qt UI covers everyday use.
   `zynthian_gui_config` only creates Tk when the program is `zynthian_main.py`, so the Qt entry
   point can use the existing configuration as it is.
5. **QML in logical pixels**, laid out for 960×600 to 1280×800 (scale 2 or 1.5 on the Duet; 1024×600
   on other screens), scaling by the output scale; no per-widget scale factors as in the Tk UI.

## Layout

```
zynthian_qt_main.py          entry point: QGuiApplication, QQmlApplicationEngine, backend start
zynqt/
  app.py                     start-up and shutdown (state manager, snapshot, MIDI, autoconnect),
                             signal handlers, the main loop
  ui.py                      ZynUI: the object the engine side sees as zynthian_gui_config.zyngui
                             (screens, current_screen, show_screen, CUIA dispatch)
  bridge.py                  zynsigman -> Qt signals (queued into the GUI thread)
  models/                    QObjects and QAbstractListModels: chains, processors, controllers,
                             presets/banks, snapshots, mixer strips, list screens
  input.py                   zynswitch/zynpot callbacks, keyboard, OSC CUIA (port 1370)
  qml/
    Main.qml                 window, top bar, screen stack, V5 touch keypad
    components/              List, InfoPane, Controller (knob/slider), Fader, Meter, Keypad, ...
    screens/                 MainMenu, Mixer, ChainControl, Selector, ...
nura/pyside6/APKBUILD        PySide6 6.12 for Nura (see Packaging)
```

## Milestones

Each milestone ends with something that runs on the Duet and on the desktop.

### M0: spike (1–2 weeks)

Goal: decide that PySide6 + Qt Quick works on the Duet, and how fast.

- Package PySide6 6.12 for Nura (see Packaging) and install it on the Duet. Fallback if that
  fails or takes too long: a C++ Qt Quick front end that embeds CPython (pybind11) and builds
  like Zrythm against the system Qt; decide at the end of M0.
- A mock app, no zynthian backend: a mixer with 16 strips (fader, mute/solo, two meters each,
  fed by a 60 Hz timer), a list with 200 items and an info pane (kinetic scrolling), the V5
  touch keypad.
- Run it in the cage kiosk as a native Wayland client: rotation, scale 2, touch (taps, list
  scrolling, fader drag), multitouch on two faders.
- Measure: CPU of the app and of cage while the meters run (target: under 10 % of a core, Tk
  today: zynthian 22 % on the mixer), frame times (`QSG_RENDER_TIMING=1`), start-up time and
  memory, idle CPU with nothing changing (should be close to 0).
- Check the threaded render loop is used (`QSG_INFO=1`) and Python stays out of the frame path:
  meters update through property bindings, not Python per frame.

Exit: numbers in this document; PySide6 or the C++ fallback chosen.

**Results (2026-11-05).** PySide6 6.12.0 built for Nura (`nura/pyside6`, 8 modules) and
installed on the Duet; the spike (`zynqt/spike/`) ran there as a native Wayland client in labwc
(Zrythm's session, Zrythm paused), Qt Quick on OpenGL ES 3.1 (Panfrost), threaded render loop.
Measured with the `performance` governor and the spike pinned to the A73 cores (4–7); CPU in % of
one core:

| | render thread | Python (GUI thread) | labwc |
|---|---|---|---|
| idle, nothing changing | 0 % (no frames drawn) | 0 % | 0 % |
| screen switch every second | 1 % | 0.4 % | 0.1 % |
| 32 meters at 30 Hz | 4.7 % | 4.1 % | 2.5 % |
| 32 meters at 60 Hz | 9.2 % | 7.9 % | 5.1 % |

- Frame rate 58–60 fps; a screen switch is on screen in the next frame or two (1–5 ms with
  `performance`, 2–25 ms with `schedutil`), against 37–76 ms per switch in the Tk UI.
- First frame 330–460 ms after start (mock app).
- A meter update costs ~1 ms of Python, 0.9 ms of it in QML bindings. Two things mattered:
  read a Python list property once per update into a QML property (every read converts the whole
  list: 5.7 ms per update before), and draw meters without `clip` (clipping breaks the scene
  graph's batching: half the render thread time without it).
- Under `schedutil` (the default of Zrythm's Duet package) the same work shows about twice the
  CPU time: the clock stays low.

Decision: PySide6 in-process, as planned; meters at 30 Hz. If the meters need to get cheaper, a
small C++ item reading zynmixer's DPM data directly (no Python per frame) is the next step.

### M1: backend in a Qt process (1–2 weeks)

- `zynthian_qt_main.py` starts the backend like `zynthian_gui.start_task` and
  `zynthian_headless.py`: control I/O configuration, state manager, last-state or default
  snapshot, MIDI, autoconnect, busy state. The Qt event loop runs in the main thread; the engine
  threads stay as they are.
- `ZynUI` as `zynthian_gui_config.zyngui`: the engine side calls into the UI in ~20 places
  (`get_alt_mode`, `current_screen`, `screens[...]` in the controller drivers for the sequencer).
  First as stubs that log; the controller drivers that need the sequencer screens stay disabled
  until those screens exist.
- `bridge.py`: register for the zynsigman signals the views need (chain manager, processors,
  mixer, state manager) and re-emit them as Qt signals.
- CUIA over OSC (port 1370) dispatched to `ZynUI`, so the Qt UI can be driven like the Tk UI from
  the start (testing with `oscsend`).
- Clean exit on SIGTERM (stopping tinydm), which the Tk UI under X11 doesn't do reliably.

Exit: the Qt app loads the last snapshot, engines play, OSC CUIAs reach it; window shows a
status bar (busy, xruns, audio levels from zynmixer).

### M2: first screens (3–4 weeks)

The screens used every day, in this order:

1. **Mixer**: strips from the chain manager, fader, balance, mute/solo/rec, meters. Levels come
   from zynmixer (`update_dpm_states` into its `dpm` array): read in a Qt timer at frame rate in
   Python (one call for all strips), exposed as properties the meter `Rectangle`s bind to. If
   that costs too much Python time, a small C++ QML item reads the zynmixer library directly.
2. **List screens** (selector + info pane): main menu, admin, engine/bank/preset selection,
   chain options, audio/MIDI routing, options and confirm dialogs. One QML component; the data
   comes from list providers (below).
3. **Chain control**: chain sidebar, controller pages, the four controllers (knob/slider), the
   processor list.
4. **Top bar, touch keypad, keyboard** (text entry).

**List providers.** The Tk selector screens mix list logic (`fill_list`, `select_action`, back
actions) with Tk widgets (`zynthian_gui_selector` is a `tkinter.Frame`). Move that logic, screen
by screen as it is ported, into UI-independent classes that produce `list_data` and handle
selection; the Tk screens keep working on top of them, and the Qt list model wraps the same
classes. This keeps both UIs in step and is worth proposing upstream (testable without a
display).

Exit: everyday use (load a snapshot, add a chain, pick a preset, mix, tweak controllers) works
with the Qt UI on the Duet, by touch.

**Status (2026-11-05).** On the desktop and the Duet (as a native Wayland client in labwc):
mixer, chain control (with sidebar: chain options, MIDI/audio routing, processor options), adding
chains (type, engine, MIDI channel, bank, preset), snapshots, ZS3, tempo, audio levels, admin
settings (all desktop entries except ZynVoice), MIDI devices and their options, recording and
transport keys, audio and MIDI player, chain manager, moving chains and processors, MIDI CC and note
range/transpose, on-screen keyboard, the V5 keypad with the wiring configuration's switch actions.
M3 started: the launcher (mixer in launcher mode) with its phrase menu, the pattern editor
(notes, CC view, chord entry; QML items), the waveform view of audio file processors (QML Shape).
Not ported yet: ZynVoice, the pattern editor's block selection/copy and finer note parameters, SMF
import/export, arranger (sooperlooper widget postponed: better as the LV2 plugin, see nura-lv2-plugins.md).

Measured on the Duet (performance governor, A73 cores), the UI as it is now:

| | Qt UI | Tk UI (labwc, XWayland) |
|---|---|---|
| Screen switch (mixer, main menu, chain control, admin, snapshots), after the first visit | 4–7 ms to the presented frame | 16–40 ms |
| First visit of a screen | 12–50 ms | 10–209 ms |
| Mixer while playing (meters at 30 Hz) | GUI thread 4.8 %, render thread 4.8 %, labwc 2.8 % | |

The Tk UI under labwc draws at 960×565 (its XWayland window is scaled up by the compositor), the
Qt UI at 1920×1200; in cage at full resolution the Tk UI took 37–76 ms per switch. Two things
mattered for the Qt numbers: one QML view per selector screen, kept while hidden, and model
updates in place instead of resets (the main menu grid took ~290 ms when its delegates and
images were recreated on every switch). `ZYNTHIAN_QT_TIMING=1` logs the switch times.

**Next steps** (2026-11-05):

1. Qt UI as the Duet's kiosk (`kiosk-session zynthian`, see nura/README.md) and everyday use.
2. Remaining M2 gaps: ZynVoice (needs a TTS engine on the device). PipeWire integration of the
   audio routing (hardware ports, main output, numbering; see docs/upstream-candidates.md) is
   only patched over so far. Move list logic out of the Tk screens into shared modules where it
   isn't trivial, as for snapshots and MIDI config.
3. Touch (postponed; multitouch faders already work): swipe vs. tap in lists, long-press timing,
   drag sensitivity.
4. M3: launcher (9f3d00c8), phrase menu (ee070fcf), pattern editor notes (1b575e6a, plain QML
   items: measure on the Duet before deciding on a C++ item), CC view and chords (3a6778ac).
   Waveform view (9e603dc5), envelope and filter (786a9315), plugin widgets. Next:
   pattern editor block selection/copy/paste; arranger. Euclidean sequencer (af8f6395) and Organelle widgets done.
5. Upstream: split the shared modules into self-contained commits, fix the bugs noted in
   [upstream-candidates.md](upstream-candidates.md), pytest for the shared modules.

### M3: towards parity

As in [ui-reimplementation-plan.md](ui-reimplementation-plan.md), phases 3–4: launcher/zynpad,
pattern editor, arranger, engine widgets (audio file, envelope, filter, …), MIDI learn flows,
hardware kits (encoders, switches, LEDs), small screens. Dense views (pattern editor, waveforms,
meters if needed) as C++ items on Qt Canvas Painter, as in Zrythm, registered as a QML module the
Python app imports.

## Raspberry Pi kits with SPI displays

Older kits drive small SPI displays (zynthian-sys overlays: `piscreen2r`, ILI9486 480×320;
`pitft28-resistive`, ILI9341 320×240 at `speed=32000000,fps=20`). Research only, not measured yet.

**The bottleneck is the SPI bus, not rendering.** A full 480×320 RGB565 frame is 300 KB; at 32 MHz
(about 4 MB/s) that is at most ~13 full frames per second, ~26 at 64 MHz. Rendering such a small
screen is cheap either way; what matters is how much of the screen goes over the bus per update.

| Path | How | SPI traffic |
|---|---|---|
| GL on the SPI display | `eglfs_kms` on the display's DRM device; Mesa's `kmsro` pairs the display-only driver with the Pi's GPU (v3d), renders into a buffer the driver reads and sends | Qt Quick's GL renderer draws whole frames and reports no damage: every frame goes over the bus in full; with meters running the bus saturates (~13 fps) |
| GL offscreen, own blit | `QQuickRenderControl` into an FBO, read back, compare with the last frame, write changed rectangles to the framebuffer | partial, but custom code for a screen that is cheap to render anyway |
| Software renderer | `QT_QUICK_BACKEND=software`, `QT_QPA_PLATFORM=linuxfb:fb=/dev/fbN` (plain fbdev, **not** `QT_QPA_FB_DRM=1`) | Qt Quick repaints and writes only changed regions; fbtft and the DRM drivers' fbdev emulation track the written lines (deferred I/O) and send only those |

- Qt's linuxfb in DRM mode double-buffers with full page flips and passes no damage
  (`qlinuxfbdrmscreen.cpp` in Qt 6.12: `drmModePageFlip`, no `drmModeDirtyFB`): full frames again.
- A compositor (cage) on the SPI display doesn't help with GL rendering (Qt reports the whole
  window as damaged); only with the software renderer would partial damage reach the display, and
  then the compositor is only an extra layer.

**Recommendation:** the software renderer with linuxfb on `/dev/fbN` for SPI kits; GL (eglfs or
Wayland) for HDMI/DSI kits and the Duet. Choose the backend at start by display type.

**Limits of the software renderer** (keep the QML working with both, branch on `GraphicsInfo.api`):

- no shader effects: no `MultiEffect` or `layer.effect`. The icon tinting of the themes
  ([qt-theming.md](qt-theming.md), branch `qt-theme-galactica`) needs pre-tinted icons there
  (tinted once in Python and cached);
- no Qt Canvas Painter (it needs the RHI): the C++ items planned for dense views (waveform, pattern
  editor) need a QPainter fallback (`QQuickPaintedItem`) on these kits;
- Shapes work (clipped corners, arcs), drawn on the CPU.

**The Tk UI stays as the fallback** for these kits until the software path is measured on one and
the small screens have their own layouts (320×240 and 480×320 are far below the 960×600–1280×800
the QML is laid out for). `ZYNTHIAN_UI=tk` keeps working as it does today.

Test to settle it: the mixer with running meters on an SPI kit, software renderer vs GL
(`kmsro`): frame rate, CPU, and the bytes the SPI driver sends.

## Packaging

- **`nura/pyside6/`**: start from aports' `py3-pyside6` recipe (it builds shiboken6 and PySide6),
  set the version to 6.12.x to match the Qt 6.12 recipes in Zrythm's `tools/nura/qt6/`, and
  limit the modules (`MODULES=Core;Gui;Qml;Quick;QuickControls2;OpenGL;Svg`, plus `Network` if
  needed). The shiboken generator needs libclang at build time, only in the build chroot; under
  pmbootstrap it runs in qemu, which is slow but a one-time cost. Check that PySide6 6.12
  supports Python 3.14 (the Duet's Python).
- **Qt packages**: depend on Zrythm's Qt 6.12 packages, built in the same pmbootstrap work
  directory or shared through its local repository. Once Alpine ships Qt 6.12 and a matching
  PySide6, drop both copies.
- **Kiosk**: `postmarketos-ui-zynthian` gets the Qt launcher (environment:
  `QT_QPA_PLATFORM=wayland`, `QT_WAYLAND_DISABLE_WINDOWDECORATION=1`, optional
  `QSG_RHI_BACKEND`), `ZYNTHIAN_UI=qt|tk` in a defaults file as Zrythm's `/etc/default/zrythm`,
  and a restart loop like `zrythm-kiosk`.

## Development setup

- Desktop: PySide6 from PyPI through uv (`uv pip install pyside6`; the wheels bundle their own
  Qt), running against the desktop install from `desktop/`. Develop QML with live reloading
  (`QQmlApplicationEngine` reloading on file change, or `qml` preview for components).
- Keep the QML to what PySide6/Qt 6.11 and 6.12 both have (no Canvas Painter from QML), so the
  desktop wheels and the device run the same code.
- Device: `nura/deploy.sh` for packages; for QML and Python, copy files and restart the session
  as now. Screenshots with grim (native Wayland, no XWayland detour).
- Tests: list providers and models with pytest, without a display; QML with `qmltestrunner` where
  useful.

## Risks and open questions

- **PySide6 6.12 for musl/aarch64**: not packaged anywhere yet; the build (libclang, qemu) may
  need patches. Fallback: the C++ front end embedding CPython (M0 decides).
- **Python in the GUI thread**: model updates and property changes run Python. Keep per-frame
  work out of Python (meters, animations in QML or C++); batch model updates.
- **Threading**: the backend calls UI code from its threads today (tkinter marshals the calls
  into its thread). Under Qt every such call must go through a signal or
  `QMetaObject.invokeMethod`; calling QObjects from other threads directly crashes at random.
- **The engine side imports `zyngui`**: 25 files in `zyngine`/`zynautoconnect` use
  `zynthian_gui_config` (mostly settings, ~20 calls into the UI object). `ZynUI` covers this for
  now; moving the settings out of `zyngui` (phase 1 of the earlier plan) is the clean fix.
- **Upstream**: upstream is Tk; the Qt UI is a fork unless upstream wants it. The list providers
  and the clean backend boundary are useful upstream either way.
- **Scale in cage**: solved: cage takes an output scale from `wlr-randr`, fractional values work
  (1.5 is the default; checked on the Duet).
- **SPI display kits**: GL rendering sends full frames over the SPI bus; the software renderer
  with partial updates fits better, but lacks shader effects and Canvas Painter. The Tk UI stays
  the fallback there (see "Raspberry Pi kits with SPI displays").
