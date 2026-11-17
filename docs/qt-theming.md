# Theming the Qt Quick UI

Status: 2026-11-15, branch `qt-tk-base` (tk is the base, `zynqt/qml/` itself; classic is an
override directory like the other themes). How the look of the Qt Quick UI (`zynqt/qml/`) is defined, how to choose a theme, and how to change or
add one.

## Choosing a theme

`ZYNTHIAN_QT_THEME` picks the theme when zynthian starts; `zynthian_qt_main.py` turns it into the
QML engine's extra file selectors (`zynqt/theme.py`) and passes the name as the context property
`zynThemeName` (for display only):

| Theme | Selectors | Look |
|---|---|---|
| `tk` (default: unset, empty or `tk`) | none: `zynqt/qml/` itself | upstream zynthian's Tk UI: its colours (`ZYNTHIAN_UI_COLOR_*`), sizes from its font size F (`ZYNTHIAN_UI_FONT_SIZE` x `ZYNTHIAN_UI_SCALE`), Tk's mixer and launcher, top bar, list rows, info pane, grid tiles, chain control, pattern editor and keypad LEDs |
| `classic` | `classic` | the Qt port's first look, zynthian's colours (as `zynthian_gui_config`): black, slate-blue plates, red selection, blue keys, Audiowide |
| `galactica` | `galactica`, `classic` | builds on classic: a battlestar CIC console: gun-metal plates with clipped corners and steel outlines, amber console text in Khand (upper case), an amber selection bar, red alerts |
| `enterprise` | `enterprise`, `classic` | builds on classic: a starship console: filled pill keys in orange, blue-gray, mauve and violet with dark labels, pill rows, mauve section headers, a curved frame (elbow) around the screens |
| `v4` | `v4` | builds on tk: the V4 kits' 3.5" 480x320 screen with two knobs on each side: Tk's V4 layout (chain control's controllers next to their knobs), the mixer with 8 strips + main, the launcher with 4 x 4 pads + main, knob hints at the edges, no on-screen keypad, F unscaled ([qt-theme-v4.md](qt-theme-v4.md)) |

A name without a directory `zynqt/qml/+<name>/` falls back to tk, with a warning in the log.

On the Duet (or in the QEMU VM): `export ZYNTHIAN_QT_THEME=enterprise` in
`~/.config/zynthian/zynthian_custom_config.sh`, which the launcher (`desktop/zynthian_desktop.sh`)
reads at each start, then restart zynthian only: the CUIA `RESTART_UI` (the launcher starts it
again on exit code 102, without restarting the session). `/etc/default/zynthian` is read only at
session start (`sudo systemctl restart tinydm`); keep the theme in one of the two. On the desktop: set the
variable before `desktop/zynthian_desktop.sh` (with `ZYNTHIAN_UI=qt`) or `desktop/preview_qt.sh`.

The theme is fixed for a run: switching means restarting the UI.

## How it is built

### Theme directories (file selectors)

`zynqt/qml/` holds the shared screens and the default components, which are the tk theme (the
look of upstream zynthian's Tk UI). Each other theme has its own directory beside them,
`zynqt/qml/+<theme>/`; classic is one of them, and galactica and enterprise build on it:

```
zynqt/qml/
  ThemeBase.qml        all tokens, with classic's values (the list below)
  Theme.qml            the Theme singleton: tk = ThemeBase { tk's values }
  Panel.qml, Label.qml, TopBarRule.qml, Elbow.qml, ...                 default components
  MixerScreen.qml, TopBar.qml, InfoPane.qml, GridTile.qml, KeyFace.qml, KeyPlate.qml,
      ChainControlScreen.qml, Controller.qml, PatternEditorScreen.qml (a frame around
      PatternEditorView.qml), PatternToolbar.qml,
      LauncherPad.qml, ChainManagerMetrics.qml, SelectorControls.qml, PatternCcLane.qml,
      SelectorCategories.qml                                             tk's versions
  SelectorScreen.qml, MixerView.qml, ...                               shared screens
  +classic/Theme.qml   classic = ThemeBase {}
  +classic/MixerScreen.qml, TopBar.qml, ... (the 15 files above)       classic's versions
  +galactica/Theme.qml    ThemeBase { only the tokens galactica changes from classic }
  +galactica/KeyPlate.qml, TopBarRule.qml                               its own components
  +enterprise/Theme.qml, KeyPlate.qml, Elbow.qml
  +v4/Theme.qml (tk's values for 480x320), ChainControlScreen.qml, Controller.qml, MixerScreen.qml,
      PatternEditorScreen.qml, and its own V4Mixer.qml, KnobHints.qml
```

Until 2026-11-15 classic was the base and tk the directory `+tk/`; the files were swapped with
`git mv` (`git log --follow` finds their history).

Components split out so a theme can replace them: `KeyPlate`, `TopBarRule`, `Elbow`, `InfoPane`
(the selector's info pane), `GridTile` (main menu / add chain tiles), `MixerScreen` (a wrapper
around the shared `MixerView`; tk draws Tk's strips, also in launcher mode: the pads in place of
the faders), `LauncherPad` (a launcher pad), `TopBar` (tk replaces it whole, with the same
properties and signals), `KeyFace` (a keypad key's label; tk colours it with the LED of
`zyn.keypadLeds`), `Controller` (a controller slot; tk: Tk's arc), `PatternToolbar` (the pattern
editor's toolbar; tk: none), `ChainManagerMetrics` (the chain manager's block sizes, spacings,
margins, node text and selection outline; tk: Tk's formulas from the screen size),
`SelectorControls` (controller widgets under a selector's info pane: none by default; tk: Tk's
selector counter on the screens with `zsel_hidden = False`: bank, preset, MIDI recorder),
`SelectorCategories` (the engine screen's category list; tk: Tk's listbox2). `InfoPane` gets
`quality` / `complexity` on the engine screen (-1 elsewhere): classic writes stars and gears
above the description, tk draws Tk's big stars and gears in place of the icon.
Selector screens can also show a status line under the list (`set_status_line()`, token
`statusLine`: the ZS3 screen's "Waiting for MIDI Program Change...").

Shared parts that theme screens reuse: `ControlWidget` (chain control's page widget: waveform,
envelope, filter, plugin widgets) and `ControlOverlays` (MIDI learn banner, processor move keys),
`PatternNote` (a note of the pattern grid, its fill a property) and `PatternCcLane` (the CC
view). tk replaces `ChainControlScreen` (Tk's page list, a quarter-width controller column, the
side chain only in select mode) and `PatternEditorScreen` (Tk's grid, piano roll and play ruler)
whole with these.

With the theme's selectors (`QQmlApplicationEngine.setExtraFileSelectors`, in
`zynthian_qt_main.py`; `zynqt/theme.py` makes the list), QML loads `+<theme>/X.qml` wherever
`X.qml` is used, the `Theme` singleton of `qmldir` included. With more than one selector the first
one that has the file wins (checked with Qt 6.12): galactica's `[galactica, classic]` loads
`+galactica/X.qml`, else `+classic/X.qml`, else `X.qml`. A theme names the theme it builds on in
`BASES` of `zynqt/theme.py` (absent: tk, the base). So:

- **Values** (colours, sizes, spacing, fonts) are tokens: `+<theme>/Theme.qml` sets them on
  `ThemeBase`. Shared QML reads `Theme.<token>` and never asks which theme is running: there is no
  `Theme.name`, `isGalactica` or the like.
- **Structure** (a different shape, an extra decoration, another layout) is a component: split the
  part that differs out of the screen into its own file with the tk version in `zynqt/qml/`,
  and give the theme its version in `+<theme>/` with the same properties (classic's in
  `+classic/`, which galactica and enterprise then also get). Examples: `KeyPlate`
  (the plate of a keypad key: classic squares, galactica outlined plates with cut corners,
  enterprise filled pills), `TopBarRule` (nothing; galactica's steel rule), `Elbow` (nothing;
  enterprise's frame).
- Files in `+<theme>/` start with `import ".."`: types of `zynqt/qml/` (`Panel`, `Label`,
  `ThemeBase`, `Theme`) are not visible from the subdirectory otherwise. A theme's component must
  not use the type it replaces (`Panel` inside `+x/Panel.qml` would load itself): give the shared
  part its own name (a `PanelBase.qml`) if both need it.

### `ThemeBase.qml` and `Theme.qml`: the tokens

`ThemeBase.qml` declares every token, with classic's value and a comment; `Theme.qml` (in `qmldir`:
`singleton Theme Theme.qml`) is `ThemeBase { ... }` with tk's values in `zynqt/qml/`,
`ThemeBase {}` in `+classic/`, and `ThemeBase { ... }` with the values a theme changes in its
directory. Components read `Theme.panel`.

Why the token defaults stay classic's although tk is the base: galactica and enterprise set only the
tokens they change, on top of classic's values (sizes, fonts, keypad colours). With tk's values as
ThemeBase's defaults they would inherit tk's sizes and colours wherever they don't set a token, and
change. `ThemeBase` can't extend `+classic/Theme.qml` either (a file in `+galactica/` naming
`Theme` gets its own `Theme.qml`). So tk's values are overrides in the base `Theme.qml`, like
any theme's. A new theme on tk starts from `zynqt/qml/Theme.qml` (copy it), one on classic from
ThemeBase.

Tokens:

| Group | Tokens | Used for |
|---|---|---|
| Surfaces | `background`, `panel`, `panelHighlight`, `overlay` | window, plates, recessed plates, dialogs and messages over the screens |
| Text | `text`, `textOff`, `disabled` | normal text, secondary text, disabled entries |
| Selection | `select`, `selectText` | the current list entry, tab or tile, and the text on it |
| Section headers | `separator`, `separatorText` | list rows like "> MIDI" |
| Keypad | `keyBackground`, `keyText`, `keyBack`, `keyYes`, `keyFilled`, `keyFills`, `keyFilledText` | the V5 touch keypad: outlined keys with coloured labels, or filled keys (`keyFilled`) in `keyFills` (by key index), BACK in `keyBack`, SEL and CTRL in `keyYes`, labels in `keyFilledText` |
| Status | `meterLow`, `meterMid`, `meterHigh`, `mute`, `solo` | meters, mute and solo buttons |
| Dialogs | `dialogNo`, `dialogYes`, `dialogText` | the NO/YES buttons of confirmations |
| Outlines | `frame`, `frameActive`, `frameWidth` | the edge of plates, of the current/active one |
| Shapes | `cut`, `cutLarge`, `radius`, `panelRadius`, `pillButtons` | clipped corners (small and large plates), radius in classic, rounded plates and pill buttons |
| Frame | `elbow`, `elbowBar`, `elbowColor`, `barColors` | the enterprise frame and the top bar's segments |
| Type | `fontFamily`, `textFamily`, `fontWeight`, `caps`, `letterSpacing`, `fontScale` | display face (titles, entries, keys), text face (small and body text; `""` is Qt's default font: `Theme.textFamily` then gives `Qt.application.font.family`, since `font.family: ""` would select a monospace face), weight of the display face, upper case, spacing, a size factor |
| Icons | `tintIcons` | tint the white line-art icons in `text` (and `selectText` on the selected tile) |
| Lists, overlays | `listBackground`, `dim`, `dimBusy`, `link` | behind list rows (also below the last, and the category pane), behind the confirm and value editor dialogs, behind the busy message, links in the help pages |
| Status flags | `alert`, `warning`, `flagRecord`, `flagPlay`, `flagMidi`, `flagSeq`, `midiActivity` | the top bar's mute flag and heart (xrun, undervoltage, overtemperature), the recorder / player / sequencer flags, the MIDI "m" |
| MIDI binding | `bindChain`, `bindGlobal`, `bindXy` | a controller's binding text (chain, global or learning, X-Y axis), the MIDI learn banner |
| Markers | `marker`, `textBypassed` | the selected launcher pad, the chain or processor being moved in the chain manager; bypassed processors |
| Chain manager | `nodeMidi`, `nodeSynth`, `nodeAudio`, `nodeSpecial`, `nodeOther`, `pinnedBackground`, `divider`, `connector` | blocks by kind, the pinned (main) chains, lines between chains and nodes |
| Pattern editor | `gridRow`, `gridRowDark`, `gridRowLine`, `gridBar`, `gridBeat`, `gridStep`, `noteHue`, `noteFrame`, `selectionFill`, `selectionFrame`, `ccBar`, `ccBarCurrent`, `buttonOn`, `buttonRecord` | grid rows (black keys darker) and lines, notes (a hue, lighter with velocity), the selected block, CC bars, toolbar buttons |
| Widgets | `widgetBackground`, `widgetLine`, `widgetFill`, `widgetGrid`, `widgetWave`, `widgetOutside` | the controller page widgets: envelope and filter curves, waveform, plugin meters' background |

Sizes (classic's values; tk derives them from F): `topBarHeight`, `titleSize`, `listRowHeight`,
`listTextSize`, `listTextMargin`, `listPadding`, `infoWidth`, `categoryWidth`, `categoryInfoWidth`
(the engine screen's category list and info pane), `infoTextSize`, `gridSpacing`
(gaps between grid tiles as Tk's `zynthian_gui_selector_grid`), `gridBackground`,
`gridPlaceholders` (grids padded with empty placeholder cells to a full 4x4: classic; tk false,
as Tk). With `gridSpacing` the grid shows as many rows as columns (Tk's tile height); grids with
more rows scroll (drag, wheel; the selection kept in view) in all themes. The grid reports its
columns to the screen (`setGridLayout`), so up / down move by the columns shown.

Shared behaviour that themes get for free: the top bar's title (`ScrollingTitle`) scrolls back
and forth as Tk's when it doesn't fit (2 px every 50 ms, 1 s at each end); the pattern grids'
two-finger pinch (`PatternPinch`: the zoom follows the fingers' distance, the cell under their
centre stays under it; a theme's `PatternEditorScreen` declares it inside its grid Flickable and
makes the Flickable non-interactive while it is active).

Tk's configuration: `zynthian_qt_main.py` passes `zynConfig` (`fontSize`, `uiScale`,
`mainMenuColumns`, `v5`, `colors`: the `color_*` values of `zynthian_gui_config`, so the
`ZYNTHIAN_UI_COLOR_*` environment). `ThemeBase` computes `tkFontSize` (F) from it and the window
(`screenWidth`, `screenHeight`, set by `Main.qml`) as `zynthian_gui_config` does, `tkPx(points)`
converts Tk's point sizes to pixels (96 dpi), `tkColor(name, fallback)` reads a colour.

Theme-wide switches: `tkAutoScale` (false: `ZYNTHIAN_UI_SCALE=auto` counts as 1), `keypadEnabled`
(false: no on-screen keypad, docked or overlay), `dialogScale` (sizes of Main.qml's dialogs and
the keyboard).

Values that used to be theme conditions in the components: `tintIcons`, `listSpacing`,
`tileMargin`, `infoBackground`, `dialogFrame`, `xyFrame`, `keyboardBackground`,
`keyboardHighlight`, `keyboardHighlightText`, `keyLineHeight`.

### `Panel.qml`: plates

The background of everything that is a key, row, tab, tile, strip, controller, dialog or button.

- `color`, `borderColor`, `borderWidth` (default: `Theme.panel`, `Theme.frame`, `Theme.frameWidth`)
- `cut` (default `Theme.cut`): above 0, an octagon with clipped corners (one `ShapePath`, filled and
  outlined); 0 a `Rectangle`
- `radius`: the radius in themes without their own (`panelRadius` 0), i.e. classic's look per
  component
- `button: true` marks keys and buttons: in themes with `pillButtons` they become pills (radius half
  the shorter side)
- rounded themes (`panelRadius` > 0) round every plate

### `Label.qml`: text

A `Text` in the theme's type: `size` is the classic pixel size (scaled by `fontScale`), `title: true`
uses the display face and weight, `body: true` keeps mixed case and no spacing. Use `body` for
descriptions, messages, values with units (dB, Hz) and keyboard letters; everything else follows
`caps`.

### `+enterprise/Elbow.qml`: the enterprise frame

One filled `ShapePath` (the default `Elbow.qml` is an empty item): a horizontal arm under the top bar, joined to a wider vertical bar left of
the screens by a rounded outer and inner corner, the bar ending in a half circle. `Main.qml` shows it
when `Theme.elbow` and the top bar is shown (`HIDE_TOPBAR` hides both), and moves the screens right
by the bar; the top bar is taller then (50 + `elbowBar` - 4), with title and status above the
segments in `barColors` that continue the arm. It starts at the screens' left edge: right of the
docked keypad, at the window's edge with the overlay keypad (which covers it while shown).

### Layout parts that follow the theme

- Touch keypad: docked (beside and below the screens) or an overlay over the blurred screens
  (`KeypadBlur.qml`); the overlay keys are the docked ones with an alpha (0.55, filled keys 0.7).
- Top bar: Tk-like fixed status slots; texts are `Label`s, the icons stay ForkAwesome glyphs in
  status colours; `StatusSlot` measures its sample text in the `Label` font.
- Selector: the category pane (engine groups) on `listBackground`, the selected group inverted
  (`text` behind, `listBackground` on it); list rows and grid tiles are `Panel`s; grid placeholder
  cells are `panelHighlight` plates (invisible on black in enterprise: empty).
- Launcher pads keep the colours of the sequences (zynseq data), only the selection uses `marker`;
  piano keys of the pattern editor stay black and white.

## Adding a theme

1. Decide what it builds on: tk (the base; nothing to do) or classic (add `"mytheme": "classic"`
   to `BASES` in `zynqt/theme.py`: its selectors become `[mytheme, classic]`).
2. Create `zynqt/qml/+mytheme/Theme.qml`:
   ```qml
   pragma Singleton
   import QtQuick
   import ".."

   ThemeBase {
       background: "#101010"
       // ... the tokens that differ from classic (ThemeBase's values)
   }
   ```
   On tk, copy `zynqt/qml/Theme.qml` (tk's values) instead and change it: `Theme.qml` files don't
   extend each other, every one is `ThemeBase { ... }`.
3. Components that look different in structure: copy the one it builds on (`zynqt/qml/KeyPlate.qml`,
   or `+classic/KeyPlate.qml` on classic) into `+mytheme/`, add `import ".."`, change it; keep its
   properties. If the part you need isn't a component of its own yet, split it out of the shared
   screen first (tk and classic must stay pixel-identical).
3. Fonts: use a face installed on the Duet (`fc-list : family` there; zynthian's fonts are in
   `/usr/share/fonts/zynthian`: Audiowide, Khand, Fjalla One, Electrolize, Exo 2, Jura, Iceland, ...).
   Condensed faces need a `fontScale` above 1.
4. Check every screen with the preview (below) in the new theme, in `tk` and in `classic`: their
   look must not change.
5. Document it in the table at the top.

## Changing a component

- Plates: `Panel`, with `button: true` for keys and buttons; no `Rectangle` with its own colour.
- Text: `Label`; `body: true` where case matters.
- Colours from tokens only. If a component needs a colour no token covers, add a token to
  `ThemeBase.qml` (with the old value, which is classic's) and set it in the themes that differ
  (tk's in `zynqt/qml/Theme.qml`), instead of a literal.
- Never test the theme's name: a value is a token, a structural difference a component in
  `+<theme>/`.
- Selected entries: `select` behind, `selectText` on it (not `text`: in galactica and enterprise
  the selection is light).

## Previewing

### A single scene, offscreen

`nura/tools/qml_preview.py SCENE.qml OUT.png [-t THEME] [--mixer]` renders a QML scene (a file
importing `"@QML@"`, i.e. `zynqt/qml/`, with mock data) at 800x480 offscreen, with the theme's file
selectors (as `zynthian_qt_main.py`, from `zynqt/theme.py`; default tk), the repository's fonts and Tk's default configuration (`ZYNTHIAN_UI_SCALE=auto`);
`--mixer` adds mock mixer strips (the compare snapshot). `PREVIEW_QML_DIR` points it at another
copy of `zynqt/qml` (e.g. `git archive HEAD zynqt/qml` for a before/after check), or render "before" from a
`git worktree` of the old commit (as for the tk/classic swap: all four themes, three sizes, AE 0).
Scenes used so far are in zynthian-stuff `ui-parity/tools/scenes/` (list, grid, mixer). Compare
against Tk screenshots from the compare VM (`docs/qemu-testing.md`) with `magick ... +append`.

### The whole UI

`desktop/preview_qt.sh` runs the UI in a headless labwc at the Duet's output (1920×1200, scale 1.5)
and takes screenshots, optionally after CUIAs (it needs OSC port 1370 free):

```sh
ZYNTHIAN_QT_THEME=enterprise desktop/preview_qt.sh -o /tmp/ent.png -s "show_screen main_menu" -s "show_screen admin" -s "chain_control"
```

Fonts missing on the desktop (Khand) fall back silently. Copy them from the Duet into a directory
and point fontconfig at it for the preview only:

```sh
mkdir -p /tmp/zynfonts && scp -r jeff@kick-duet.local:/usr/share/fonts/zynthian/Khand /tmp/zynfonts/
printf '<fontconfig><include>/etc/fonts/fonts.conf</include><dir>/tmp/zynfonts</dir></fontconfig>\n' > /tmp/zynfonts.conf
FONTCONFIG_FILE=/tmp/zynfonts.conf ZYNTHIAN_QT_THEME=enterprise desktop/preview_qt.sh ...
```

The preview writes the desktop's config and `last_state.zss`. For repeatable runs point it at a copy
(`ZYNTHIAN_CONFIG_DIR=... ZYNTHIAN_MY_DATA_DIR=...`, both exported by `desktop/zynthian_desktop_env.sh`
only if unset), with a factory snapshot as `last_state.zss`, and wait for the snapshot to load
(about a minute with `003`/`009`) before sending CUIAs. Comparing classic before and after a change
with `compare -metric AE` leaves only what changes between any two runs: the CPU percentage, and a
few single pixels.

In the QEMU VM (`docs/qemu-testing.md`; Khand is installed there): `nura/tools/sync_ui.sh -V`,
`export ZYNTHIAN_QT_THEME=...` in the VM's `~/.config/zynthian/zynthian_custom_config.sh`, the
CUIA `RESTART_UI` (QML errors at load end up in `~/.local/state/tinydm.log`), CUIAs with `oscsend localhost 1370 /cuia/...` in the VM, `nura/tools/screenshot.sh -V`.

### QML hot reload (qmlpreview)

For development only, QML changes can reach the running UI without `RESTART_UI`, with Qt 6's QML
Preview (tested in the QEMU VM, 2026-11-09):

- `export ZYNTHIAN_QT_QMLPREVIEW=1` in `~/.config/zynthian/zynthian_custom_config.sh`, then
  `RESTART_UI` (`nura/tools/sync_ui.sh -V -R`). `zynthian_qt_main.py` then runs itself again as a
  child of `/usr/lib/qt6/bin/qmlpreview --verbose` (`run_under_qmlpreview()`) and waits for it;
  the child enables QML debugging and loads the QML through the symlink
  `$XDG_RUNTIME_DIR/zynthian-ui` (to `/usr/share/zynthian/zynthian-ui`). On success
  `~/.local/state/tinydm.log` shows "Starting '...zynthian_qt_main.py -qmljsdebugger=...'" and
  "Inplace updates setting confirmed as: enabled".
- `nura/tools/sync_ui.sh -V -q` copies only `zynqt/qml` (file by file, no restart, 0.2 s);
  qmlpreview sees the changed files and reloads them in the running UI within a second. Changed
  literals (sizes, colours, texts) update in place, the current screen and the Python state stay:
  that is the reliable use. Structural changes (a new item, a new file) are hit and miss: once a
  new item in the top bar updated in place; once the whole UI was rebuilt (back on the mixer, and
  QML defaults written into Python: the tempo went to 80 bpm, the active chain to main); once
  (a new item in ChainManagerScreen.qml while it was shown) the UI crashed, and the launcher
  started it again (exit 2). A new file isn't picked up: `RESTART_UI`. After a reload the log
  shows a few "<Unknown File>: Unable to assign [undefined] to ..." (harmless). Python changes
  still need `RESTART_UI`.
- Why it is done this way (each one broke it once):
  - qmlpreview always exits with 0, whatever the UI's exit code; the launcher would end the
    session on `RESTART_UI` (102). The child writes its exit code to a file
    (`ZYNTHIAN_QT_EXIT_FILE`) and the waiting parent returns it.
  - The preview service never asks qmlpreview for files under Qt's prefix
    (`QLibraryInfo::PrefixPath`, `/usr` with the system's Qt): from `/usr/share/zynthian` nothing
    was watched or reloaded. Hence the symlink (to the whole tree: the QML uses `../../icons`).
  - The launcher (`desktop/zynthian_desktop.sh`) is unchanged: a running launcher keeps the
    script it started with (`sync_ui.sh` moves a new one over it), so a launcher change only
    takes effect after a session restart.
  - qmlpreview appends `-qmljsdebugger=...` after the program, so the script is started
    directly (executable, `#!/usr/bin/python3`); `qmlpreview python3 script.py` breaks. The tool
    must be Qt 6's (package `qt6-qtdeclarative-dev`); a Qt 5 `qmlpreview` silently does nothing.
  - `zyninject.sh` and the other tools take the newest zynthian process (the child), not the
    waiting parent.
- The log gets a "Could not open file ...+<theme>/X.qml" line per file selector probe; harmless.
- Never in production: the QML debug server can control the UI. Without the variable nothing
  changes.
- The component preview has a live mode for the same: `/usr/lib/qt6/bin/qmlpreview
  ./nura/tools/qml_preview.py SCENE.qml --live [-t THEME]` (a window instead of a PNG; zynqt/qml
  files reload, the scene itself is a copy and doesn't). On the host this was flaky (Qt 6.12:
  the child started once, later not).

On the Duet: copy the changed files into `/usr/share/zynthian/zynthian-ui` (as in
`docs/performance-measurement.md`), restart the session, `nura/tools/screenshot.sh`.

## Performance

Measured on the Duet for the meters and lists (`docs/performance-measurement.md`); keep to it:

- no `clip` on items that update often (meters): clipping breaks the scene graph's batching;
- `Panel` with cut corners is a `Shape` (triangulated when its size changes, not per frame); fine
  for keys, rows and plates, but don't put one inside each meter segment;
- `MultiEffect` (icon tint) renders each icon into a layer: fine for menus and info icons, not for
  things that animate;
- colours bound to state (selection, pressed) are cheap; prefer them to extra items.

## Open

- Only the screens of `zynqt/qml/` are themed; new screens should use `Panel`/`Label` from the start.
- The plugin widgets (`PluginWidgetView`: tuner, meters), `EuclidSeqView`, `SooperLooperView` and
  `OrganelleView` follow the Tk widgets' colours; only their backgrounds are tokens so far.
- The mixer's meters use `meterLow`/`Mid`/`High` only; a segmented (LED) meter style would be a token
  and a variant of `Meter.qml`.
- The kiosk sessions export `ZYNTHIAN_QT_THEME` from `/etc/default/zynthian`; on the zynthian kits
  zynthian-kit sets it (v4 for 480x320 panels), elsewhere it is set by hand.
