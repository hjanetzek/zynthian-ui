# Reimplementing the zynthian UI with Qt Quick or JUCE

Status: planning draft, 2026-11-03. Context: running zynthian on Nura (postmarketOS) on a
Lenovo Duet (1920×1200, Mali-G72/Panfrost, ARM), see `nura/`.

## Why

The UI is Tkinter. Profiling on the Duet (`nura/tools/`) showed:

- Most UI time is Python + Tcl overhead of many small canvas commands, not drawing. Several
  hot spots were fixed (title scroll timers, icon caching, mixer rebuilds), but the model
  stays: every visual change is a Tcl command string, parsed and executed in the main thread.
- Tk draws in software through Xlib. Under Wayland it goes Tk → XWayland → compositor; images
  with alpha are blended by reading back the background. There is no GPU path, and Tk has no
  Wayland backend.
- Tk has no synchronized, vsync'd frame presentation. Screens are built by deleting and
  recreating canvas items, and changes reach the screen as they happen: partial updates are
  visible (flicker), and there is no way to present a complete frame at once.
- Touch is emulated pointer input; multitouch needs a separate evdev reader (`multitouch.py`).
- Other threads (status, LEDs) call Tk; tkinter marshals the calls into the main thread, which
  hides the cost and makes deadlocks easy (seen while profiling).

A toolkit that renders retained scenes on the GPU and presents whole frames would fix these at
the root.

## What there is to replace (measured)

| Part | Size |
|---|---|
| `zyngui/` | 83 files, ~38,000 lines; 74 screens and widgets |
| Tk usage | 50 files, ~1,300 lines of direct Tk calls; 50 canvases, 14 frames, 11 labels, 2 listboxes |
| Canvas API used | ~15 methods (`create_*`, `itemconfig` ~300×, `coords` ~130×, tags, `tag_bind`), 163 event bindings, 41 `after()` timers |
| Largest screens | mixer 2,900 lines, pattern editor 4,000 (base + notes), arranger 1,300, audio file widget 1,200, organelle widget 1,000, chain manager 1,000, control 1,000 |
| Interfaces to the rest | 121 CUIA actions (`zynthian_gui.cuia_*`, also over OSC port 1370), ~70 signals (`zynsigman`), the processor/controller model (`zynthian_controller`) |
| Coupling engine → UI | 15 files in `zyngine`, `zynautoconnect` import `zyngui`: mostly settings in `zynthian_gui_config` (MIDI services, hotplug, …), ~20 direct calls into the UI object |

The engine side (`zyngine`, the zynlibs, zyncoder) is UI-independent apart from that coupling.
Most of the UI work is hand-drawn screens; standard widgets are few.

## Options

### A. Qt Quick (QML) with the Python backend in-process (PySide6)

- Python stays: `zyngine`, state and chain managers, controllers run unchanged in the same
  process. QML views bind to Python models (`QObject` properties, signals, `QAbstractListModel`).
- Rendering: Qt Quick scene graph, OpenGL ES (Panfrost) or Vulkan, threaded render loop,
  vsync'd frames, no flicker by design. Native Wayland (`qt6-qtwayland`), so no XWayland; also
  runs on X11, eglfs (no compositor at all), and desktops.
- Touch and multitouch are native (pointer handlers, flickables with kinetic scrolling).
- Availability: Alpine edge packages `py3-pyside6` 6.11, `qt6-qtdeclarative`, `qt6-qtwayland`.
- Custom drawing (meters, pattern grid, waveforms, envelopes): QML `Shape`/`Canvas` for simple
  cases; for dense or fast ones (DPM meters, piano roll, waveform) `QQuickPaintedItem` (software,
  cached) or a `QSGNode`-based item (GPU). The latter is C++ for the best result; PySide6 can
  do `QQuickPaintedItem` and simple scene-graph nodes.
- Threading: QML only in the GUI thread; background threads emit Qt signals (queued
  connections). That replaces tkinter's hidden marshalling with explicit, cheap events.
- Costs: PySide6 adds ~100–150 MB on disk with Qt; startup a few seconds on ARM; Python
  overhead remains for logic, but drawing and animation leave the interpreter.

### B. JUCE (C++) as a separate process

- The UI becomes a C++ application. The Python backend stays as a headless process
  (`zynthian_headless.py` exists as a starting point), controlled over the existing OSC CUIA
  interface plus a new state/notification protocol (OSC or a socket with JSON/msgpack).
- Rendering: JUCE's software renderer or its OpenGL context. Note from the Kick port on the
  same device: JUCE's OpenGL renderer still rasterizes paths largely in software and uploads
  textures; a full-screen redraw at 1920×1200 took ~60 % of a core. Fast is possible, but only
  with careful component caching; it is not a scene graph.
- Touch: JUCE handles multitouch (with the XInput2 patch used for Kick); no native Wayland
  backend in JUCE 7/8 (runs on XWayland).
- Advantages: one native binary, no Python in the UI, real-time-friendly; know-how from Kick.
- Costs: a protocol for everything the UI shows (chains, processors, controllers, presets,
  sequencer state, meters, files) and does (121 CUIAs and more), kept in sync with the Python
  side; two languages to maintain; the largest effort.

### C. Incremental: Tk canvas API on Qt (for comparison)

A compatibility layer implementing the ~15 canvas methods, tags and bindings on
`QGraphicsScene` with an OpenGL viewport, so existing screens run with few changes. 3–6 weeks
for the layer; GPU compositing and Wayland, but Tk's semantics (tags, font metrics, Listbox,
`after`) leak through, and the "rebuild everything" patterns of the screens remain. Useful
only as a stopgap; not considered further.

## Recommendation

Option A, Qt Quick with PySide6, in-process:

- keeps the whole Python backend, upstream changes there merge as before;
- gets GPU rendering, vsync'd frames, native Wayland and multitouch;
- allows running the Tk UI and the Qt UI side by side during migration (same backend, two
  front ends selectable at start), screen by screen;
- C++ only where needed (custom scene-graph items for meters and editors), optional.

JUCE makes sense if the goal is a native C++ product UI anyway (e.g. shared with Kick), and the
headless backend with a protocol is wanted for other reasons (remote UIs, web UI).

## Plan for option A

### Phase 0: spike (1–2 weeks)

- PySide6 + QML app on the Duet (cage and eglfs), 60 fps check with a mock mixer: 16 strips
  with animated DPM meters, a list with kinetic scrolling, the V5 touch keypad.
- Measure CPU (target: < 10 % of a core idle, smooth meters), startup time, memory.
- Decide the meter/editor drawing approach (QML vs `QQuickPaintedItem` vs C++ `QSGNode`).

### Phase 1: backend boundary (2–3 weeks)

- Move UI settings out of `zynthian_gui_config` into a UI-independent config module, so
  `zyngine` no longer imports `zyngui` (the 15 files above).
- Replace the ~20 direct calls from the engine into the UI object by signals (`zynsigman`).
- Define a front-end interface: the CUIA dispatch (`zynthian_gui.cuia_*`) moves into a
  UI-independent controller class that both front ends use; screens become views on it.
- Start option: `ZYNTHIAN_UI=tk|qt`.

### Phase 2: models and core screens (6–10 weeks)

Python `QObject` models for chains, processors, controllers, presets/banks, snapshots,
sequencer state, MIDI devices; QML views:

- topbar/status, V5 touch keypad (as a QML component), loading/busy overlay;
- selectors (lists with icons and info pane): main menu, admin, engine, bank, preset,
  file selectors, options/confirm dialogs, keyboard;
- mixer with chain strips, faders, DPM meters, launchers (custom item for meters);
- control screen with the controller widgets (knobs/sliders, xy).

At the end of this phase zynthian is usable with the Qt UI for everyday use.

### Phase 3: editors and widgets (8–12 weeks)

- pattern editor (notes, CC), arranger, zynpad/launcher grid;
- engine widgets: audio file/waveform, envelope, filter, tempo, euclidean sequencer,
  sooperlooper, spectrum, organelle, NAM, AIDA-X, tunaone, chord analyzer;
- help viewer (QtWebEngine is heavy; Qt's `TextEdit`/`Text` with a subset of HTML may do).

### Phase 4: parity and polish (4–6 weeks)

- MIDI learn flows, TTS hooks, encoder/hardware input (zynpots, switches) on real ZynthianOS
  kits, small screens (480×320, 800×480), keybindings, power save;
- packaging for Nura and ZynthianOS (PySide6 on Raspberry Pi OS: Debian packages exist);
- retire the Tk UI or keep it as a fallback.

### Effort

| Phase | Weeks (one experienced developer) |
|---|---|
| 0 spike | 1–2 |
| 1 backend boundary | 2–3 |
| 2 core screens | 6–10 |
| 3 editors, widgets | 8–12 |
| 4 parity, polish | 4–6 |
| **Total** | **~5–8 months** |

For option B, add the protocol and headless backend work (~1–2 months) and the C++ rewrite of
all logic that lives in the Tk screens today: roughly **8–12 months**.

## Risks and open questions

- Upstream: zynthian upstream is Tk-based; a second front end is a fork unless upstream wants
  it. Phase 1 (backend boundary) is useful upstream on its own and should be proposed there.
- Raspberry Pi: Qt Quick on Pi 4/5 with the V3D driver works well; on a Pi 3 it is tight.
  Small screens need their own QML layouts (the Tk UI scales one layout).
- PySide6 on ZynthianOS (Debian/Raspberry Pi OS) and on musl (Alpine) must be tested early.
- Real-time safety: the UI is not in the audio path (engines and zynlibs are), so a Python UI is
  acceptable; meter data should be pulled at frame rate from the zynmixer libraries, not pushed.
- Custom drawing performance in pure Python/QML for the pattern editor and meters: decide in
  the spike whether C++ items are needed.
- Hardware kits (encoders, switches, LEDs) must keep working; their handling is in zyncoder and
  `zynthian_gui.py` today and moves to the front-end-independent controller in phase 1.
