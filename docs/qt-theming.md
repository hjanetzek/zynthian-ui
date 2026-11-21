# Theming the Qt Quick UI

Status: 2026-11-18, branch `theme-behaviour` (every theme behaves as tk: overrides are looks,
see "Behaviour is tk's in every theme"); Admin > Theme switches at run time; tk is the
base, `zynqt/qml/` itself, since 2026-11-15; classic is an override directory like the other themes. How the look of the Qt Quick UI (`zynqt/qml/`) is defined, how to choose a theme, and how to change or
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
| `enterprise` | `enterprise`, `classic` | builds on classic: a starship console: filled keys with one corner radius (a quarter of the smallest key side) in orange, blue-gray, mauve and violet with dark labels, pill rows, mauve section headers, a curved frame (elbow) around the screens |
| `v4` | `v4` | builds on tk: the V4 kits' 3.5" 480x320 screen with two knobs on each side: Tk's V4 layout (chain control's controllers next to their knobs), the mixer with 8 strips + main, the launcher with 4 x 4 pads + main, knob hints at the edges, the keypad only when docked, F unscaled ([qt-theme-v4.md](qt-theme-v4.md)) |

A name without a directory `zynqt/qml/+<name>/` falls back to tk, with a warning in the log.

### Admin > Theme

Admin > SCREEN > **Theme (<running theme>)** opens the list of themes: Default, then every
directory `zynqt/qml/+<name>/` with a `Theme.qml` beside the base tk (`available_themes()` in
`zynqt/theme.py`, so a new theme shows up by itself; its info text is in `DESCRIPTIONS` there).
The user's choice is checked. Choosing another one asks "Switch to theme X?", saves it and
switches **at run time**: zynthian keeps running (engines, chains, audio, the sequencer, the
current screen and selection); only the QML is loaded again (below). The Admin entry and this
list work in every theme, v4 at 480x320 included.

Where the choice is stored (`save_theme()` in `zynqt/theme.py`):

- `export ZYNTHIAN_QT_THEME="<name>"` in `~/.config/zynthian/zynthian_envars.sh`
  (`zynconf.save_config`, as the other Admin settings and webconf), or in
  `zynthian_custom_config.sh` if that file exports the variable itself: it is sourced last, a
  value in `zynthian_envars.sh` would have no effect then.
- **Default** removes the user's value from both files, so the system's theme applies again: the
  one in `/etc/default/zynthian` (the kit's: `zynthian-kit` writes `v4` there on V4 kits), else
  tk. The launcher keeps a variable it once exported (it sources the config files in its own
  shell), so removing the line alone would keep the old theme at the next start: Default also
  writes one line, marked `# zynthian: Admin > Theme > Default, for one start`, into
  `zynthian_envars.sh`, `export ZYNTHIAN_QT_THEME="<the system's>"` or
  `unset ZYNTHIAN_QT_THEME`; the UI removes that line when it starts (`drop_once_lines()`), and
  the launcher's variable then holds the system's value.

Precedence at each UI start (the launcher `desktop/zynthian_desktop.sh` sources these in order,
the last one wins):

1. the session's environment: the kiosk sessions export `ZYNTHIAN_QT_THEME` from
   `/etc/default/zynthian` when the session starts (`zynthian-session.sh`); on the desktop, what
   the launcher was started with;
2. `~/.config/zynthian/zynthian_envars.sh` (Admin > Theme, webconf);
3. the MIDI profile;
4. `~/.config/zynthian/zynthian_custom_config.sh` (by hand; Admin > Theme updates the line there
   if it exists).

By hand: `export ZYNTHIAN_QT_THEME=enterprise` in `zynthian_custom_config.sh`, then restart
zynthian only: the CUIA `RESTART_UI` (Admin > Restart UI; the launcher starts it again on exit
code 102, without restarting the session). `/etc/default/zynthian` is read only at session start
(`sudo systemctl restart tinydm`). On the desktop: set the variable before
`desktop/zynthian_desktop.sh` (with `ZYNTHIAN_UI=qt`) or `desktop/preview_qt.sh`.

### Runtime switch

The theme only matters when the QML loads (file selectors); all state is in Python (`ZynUI`,
the models). `QmlFrontend` in `zynthian_qt_main.py` holds the QML side: the engine (a
`QQmlApplicationEngine` with the theme's selectors and the context properties), its window and
the window's event filters (key bindings, user activity). `ZynUI.switch_theme(name, done)` (after
the current event: a QML handler may be the caller) makes it:

1. delete the window and the engine with `deleteLater()` and wait for the engine's `destroyed`:
   the old window is gone before the new one exists (eglfs and linuxfb allow one window; a short
   black frame). Not deleted synchronously from Python: destroying a window waits for its render
   thread, which may wait for the GIL the caller holds (Python slots on `frameSwapped`, painted
   items); `QWindow.hide()` from Python hung that way. The engine is a child of the application
   so that dropping its Python wrapper never deletes it synchronously either;
2. create a new engine with the new selectors (a new engine, not `clearComponentCache()`: the
   `Theme` singleton has to be created again), load `Main.qml`, install the filters again. QML
   shows the current screen and selection from `ZynUI`'s state;
3. on a QML error (no root object) fall back to `RESTART_UI`: the choice is saved by then, so the
   next start loads it (or the user picks another theme).

Under qmlpreview (`ZYNTHIAN_QT_QMLPREVIEW=1`, hot reload) the switch is a `RESTART_UI`: the preview
service is attached to the first engine.

Tested in the QEMU VM (cage, v4 at 480x320, 2026-11-17): 30+ switches through all themes with
chains and the MIDI test file playing; same process, tempo, active chain and mixer levels kept,
the PipeWire nodes kept running, key bindings and touch work in the new window, no QML warnings.
Each switch leaves about 0.35 MB of resident memory behind (Qt's caches, the allocator), which
doesn't matter for a setting changed now and then. Not tested on eglfs or linuxfb.

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
  ChainControlScreen.qml, PatternEditorScreen.qml (+ PatternEditorView.qml, PatternCcLane.qml),
      SelectorControls.qml, TopBarState.qml, TopBarTitleTouch.qml, ControllerTouch.qml
                                                    shared behaviour and content (all themes)
  MixerScreen.qml, TopBar.qml, InfoPane.qml, GridTile.qml, KeyFace.qml, KeyPlate.qml,
      Controller.qml, ChainNode.qml, ControlPageRow.qml, PatternToolbar.qml (none),
      LauncherPad.qml, ChainManagerMetrics.qml, SelectorCategories.qml   tk's looks
  SelectorScreen.qml, MixerView.qml, ...                               shared screens
  +classic/Theme.qml   classic = ThemeBase {}
  +classic/TopBar.qml, MixerScreen.qml (MixerView), InfoPane.qml, GridTile.qml, KeyFace.qml,
      KeyPlate.qml, Controller.qml, ChainNode.qml, ControlPageRow.qml, PatternToolbar.qml,
      LauncherPad.qml, ChainManagerMetrics.qml, SelectorCategories.qml   classic's looks
  +galactica/Theme.qml    ThemeBase { only the tokens galactica changes from classic }
  +galactica/KeyPlate.qml, TopBarRule.qml                               its own components
  +enterprise/Theme.qml, KeyPlate.qml, Elbow.qml
  +v4/Theme.qml (tk's values for 480x320), ChainControlScreen.qml, Controller.qml, MixerScreen.qml,
      PatternEditorScreen.qml, SelectorHints.qml, and its own V4Mixer.qml, KnobHints.qml
```

Until 2026-11-15 classic was the base and tk the directory `+tk/`; the files were swapped with
`git mv` (`git log --follow` finds their history).

### Behaviour is tk's in every theme

Since 2026-11-18 (branch `theme-behaviour`; the inventory is in zynthian-stuff
`ui-parity/theme-behaviour.md`) every theme behaves as tk: what taps, swipes, keys and knobs do,
which screens and actions are reachable, what is shown (titles, values, labels, indicators, LEDs)
and the Python calls are the same. A theme changes only the look. So:

- **Shared, not overridden** (one file for all themes): `ChainControlScreen` (layout, content,
  touch; looks from `ChainNode`, `ControlPageRow`, `Controller` and the tokens
  `controllerColumn`, `controllerGap`, `sideChainBackground`), `PatternEditorScreen` (the theme's
  `PatternToolbar` above the shared `PatternEditorView` and `PatternCcLane`, colours from the
  grid tokens), `SelectorControls` (the selector counter), `TopBarState` (what the top bar shows:
  the title per screen, the inverted edit mode title, the tempo on the mixer),
  `TopBarTitleTouch` (the title's tap: root / mixer <-> launcher, bold or long press: main menu;
  no other gestures), `ControllerTouch` (a controller's drag, tap, long press, wheel). v4
  keeps its own `ChainControlScreen` and `PatternEditorScreen` (frames, the knob hints) and uses
  the shared touch.
- **Look-only overrides** (same properties, same data, no handlers of their own): `InfoPane`,
  `GridTile`, `SelectorCategories`, `KeyPlate`, `KeyFace` (classic draws the key's LED,
  `zyn.keypadLeds.lit` / `colors`, as a light; tk colours the label with it), `Controller` (the
  touch is `ControllerTouch`; the content tk's: `tkValueText`, names with spaces, no arc on path
  controllers, read-only and select mode dimmed), `ChainNode`, `ControlPageRow`, `LauncherPad`,
  `ChainManagerMetrics`, `TopBarRule`, `Elbow`, `Theme`.
- **Full copies kept, with tk's behaviour ported** (keep them in step with tk's): `+classic/TopBar.qml`
  (uses `TopBarState` and `TopBarTitleTouch`; only the status area's long press, all sounds off,
  is its own) and `MixerView.qml` (classic's mixer: tk's touch and content from
  `MixerScreen.qml`, listed in its header comment).
- **Extras** a theme may have where tk has nothing (they must not change what tk's gestures do):
  classic's pattern toolbar, the mixer's move buttons, balance drag and double tap, the CPU /
  battery / mute slots.

A change to behaviour goes into the shared file (or into tk's file and the copies above).

Components split out so a theme can replace them: `KeyPlate`, `TopBarRule`, `Elbow`, `InfoPane`
(the selector's info pane), `GridTile` (main menu / add chain tiles), `MixerScreen` (a wrapper
around the shared `MixerView`; tk draws Tk's strips, also in launcher mode: the pads in place of
the faders), `LauncherPad` (a launcher pad), `TopBar` (a theme replaces it whole, with the same
properties and signals, and shows `TopBarState`'s content with `TopBarTitleTouch` on the title), `KeyFace` (a keypad key's label; tk colours it with the LED of
`zyn.keypadLeds`, classic draws it as a light; properties `key`, `label`, `subLabel`, `radius`),
`Controller` (a controller slot; tk: Tk's arc; with `ControllerTouch` and property `dimmed`),
`ChainNode` (a node of chain control's side chain), `ControlPageRow` (a row of its page list),
`PatternToolbar` (the pattern editor's toolbar; tk: none), `ChainManagerMetrics` (the chain manager's block sizes, spacings,
margins, node text and selection outline; tk: Tk's formulas from the screen size),
`SelectorControls` (Tk's selector counter under a selector's info pane, all themes, on the
screens with `zsel_hidden = False`: bank, preset, MIDI recorder),
`SelectorCategories` (the engine screen's category list; tk: Tk's listbox2), `SelectorHints`
(what the knobs do on a list screen, from the screen's `knobHints`, by knob index: none by
default, with `leftInset` / `rightInset` 0; v4: `KnobHints` at the edges, the list and the info
pane moved in by a hint column). `InfoPane` gets
`quality` / `complexity` on the engine screen (-1 elsewhere): classic writes stars and gears
above the description, tk draws Tk's big stars and gears in place of the icon.
Selector screens can also show a status line under the list (`set_status_line()`, token
`statusLine`: the ZS3 screen's "Waiting for MIDI Program Change...").

Shared parts that theme screens reuse: `ControlWidget` (chain control's page widget: waveform,
envelope, filter, plugin widgets) and `ControlOverlays` (MIDI learn banner, processor move keys),
`PatternNote` (a note of the pattern grid, its fill a property) and `PatternCcLane` (the CC
view). `ChainControlScreen` (Tk's page list, the controller column, the side chain only in select
mode) and `PatternEditorScreen` (Tk's grid, piano roll and play ruler) are shared by all themes;
v4 frames them in its own copies.

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
| Keypad | `keyBackground`, `keyText`, `keyBack`, `keyYes`, `keyFilled`, `keyFills`, `keyFilledText`, `keyRadius` | the V5 touch keypad: outlined keys with coloured labels, or filled keys (`keyFilled`) in `keyFills` (by key index), BACK in `keyBack`, SEL and CTRL in `keyYes`, labels in `keyFilledText`; `keyRadius`: one corner radius for all keys, as a part of the keypad's smallest key side (`Keypad.keyMinSide`, side and bottom keys; 0.5 would make the smallest keys pills; enterprise 0.25: rounded plates, all with the same corners, whatever the aspect ratio; 0: the theme's KeyPlate decides). Layout: the bottom row's two keys below the side columns (left-handed ◀ ▼, right-handed ▼ ▶) are as wide as the columns, the other eight share the rest (at least 3/4 of a tenth of the width each; below that the two get what is left) |
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
| Pattern editor | `gridRow`, `gridRowDark`, `gridRowLine`, `gridRowLineTonic`, `gridBar`, `gridBeat`, `gridStep`, `gridBarWidth`, `noteHue`, `noteFrame`, `selectionFill`, `selectionFrame`, `ccBar`, `ccBarCurrent`, `buttonOn`, `buttonRecord` | row bands (black keys darker; tk transparent: none) and lines (the tonic's), step lines (bars, beats, steps; the bar's width), notes (a hue, lighter with velocity; tk -1: Tk's grey by velocity, selected blue, the moving copy green), the selected block, CC bars, toolbar buttons |
| Pattern playhead | `playheadLineWidth`, `playheadColor`, `playheadTailColor`, `playheadTailSteps`, `playheadTailOpacity`, `playheadTailCurve`, `playheadLineOnTop`, `playheadFps` | the playhead line across the grid and the CC view (width, colour; default `select`), its gradient tail (colour, length in steps, alpha at the line, fade curve: alpha = opacity x t^curve), the line over the notes (the tail is always behind them), updates per second (0: every frame). See "Pattern editor playhead" below |
| Chain control | `controllerColumn`, `controllerGap`, `sideChainBackground` | the controller column's part of the width (tk 0.25), the gap below each controller, the side chain's background |
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

Theme-wide switches: `tkAutoScale` (false: `ZYNTHIAN_UI_SCALE=auto` counts as 1), `dialogScale` (sizes of Main.qml's dialogs and
the keyboard), `flatPresetList` (true: the preset list shows all banks, each under a section
title, with their presets, and the BACK knob (knob 1) moves from bank to bank; false, the
default: Tk's bank list, then the bank's presets. On in v4, off in tk and classic).

`flatPresetList` in detail (`zynqt/screens/chain_screens.py`, `Preset`): `SelectorScreen.qml`
reports the token to its screen (`setFlatPresetList`); Python decides the content. The flat list
applies to engines whose preset lists are cheap to read for every bank (`FLAT_PRESET_ENGINES`:
sfizz, which scans its bank directories, and LV2 plugins, whose presets are in memory), with more
than one bank, outside the favourites view and sub-folder browsing; other engines (FluidSynth,
whose preset list loads the SoundFont into the synth, ZynAddSubFX, LinuxSampler, ...) keep Tk's
two levels. Section titles are separators (not selectable, drawn as the other section titles);
the current preset is selected (else the first preset of the current bank) with its section
title in view (the screen's `sectionIndex`; a jump to a group puts its title at the top:
`showSection`). Choosing a preset of another bank sets that bank first, as the bank list does.
Knob 1 (`GROUP_KNOB`) turns to the next / previous group's first preset (back from inside a
group: its first preset first), ARROW_LEFT / RIGHT do the same; knob 3 still moves entry by
entry. Switch 1 short (BACK) leaves the list as BACK leaves any list: there is no bank level (Tk
goes to the bank list); the BANK_PRESET CUIA still opens the bank list (bank options), and a bank
chosen there shows the flat list at that bank. A new chain opens the flat list instead of the
bank list. Cost: sfizz ~30 us per preset to scan (1200 presets in 40 banks: 45 ms in the QEMU
VM); the presets of directory banks are cached while the directory's mtime stays the same (the
current bank is always read again), so the list opens again in ~5 ms; LV2 (Dexed, 1600 presets
in 51 banks) ~5 ms; the QML view creates only the visible rows.

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
- `cornerRadius` (default -1): from 0, this radius (at most half the shorter side) over all of the
  above; the keypad keys of themes with `keyRadius` use it

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
docked keypad, else at the window's edge.

### Layout parts that follow the theme

- Touch keypad: docked (beside and below the screens) or not shown; nothing else (the overlay
  keypad was removed 2026-11-18). `ZYNTHIAN_QT_KEYPAD="docked"` shows it, any other value (`off`,
  the former `overlay`) doesn't; a tap on the top bar's status area (as Tk's) and Admin > Docked
  Touch Keypad switch it at run time and save it. `KeyPlate` has the properties `fill`,
  `pressed`, `minSide`; `KeyFace` `key`, `label`, `subLabel`, `radius`. In the classic themes
  (fixed sizes) the docked keypad leaves too little room at 480x320; tk and v4 scale with it.
- Keypad labels are shrunk to fit their key (`Text.Fit`), for narrow keys and large font sizes.
- F-key labels: F1-F4 show what they do now as their `label` and their name ("F1", with the ALT
  LED "F5") as a small `subLabel` (tk: top left in the LED colour; classic and galactica: top left,
  the key's LED a light at its top centre; enterprise: top right, clear of the corner, the LED a
  dot at the top left). The text comes from Python,
  `zyn.keypadLeds.functionLabels` (`zynqt/keypad_leds.py`, a list by key index, "" for none),
  updated with the LEDs (100 ms) when the wiring, ALT or the screen changes: the screen's own
  action for the key first (a screen's `fkey_labels()` {zynswitch: label}, as its `switch()` takes
  the key; the pattern editor with ALT: "CLIP 1", "CLIP 2", "BLOCK", "CC" / "NOTES"; not under a
  dialog), else the custom switch's UI action of the wiring configuration
  (`ZYNTHIAN_WIRING_CUSTOM_SWITCH_08/12/16/20`: push, else short, else bold action; with ALT the
  ALT ones; a short press on the shown screen's own key: its bold action), shortened by
  `cuia_label()`: "PROGRAM_CHANGE 1" "PROG 1" (the V5 profile: PROG 1-4, with ALT PROG 5-8),
  "ZS3_LOAD 3" "ZS3 3", "TOGGLE_AUDIO_RECORD" "AUD REC", longer ones on two lines of at most 8
  characters. MIDI custom switches get no label: the touch keys only send switch CUIAs. Themes only
  place and style the two texts.
- Top bar: Tk-like fixed status slots; texts are `Label`s, the icons stay ForkAwesome glyphs in
  status colours; `StatusSlot` measures its sample text in the `Label` font.
- Selector: the category pane (engine groups) on `listBackground`, the selected group inverted
  (`text` behind, `listBackground` on it); list rows and grid tiles are `Panel`s; grid placeholder
  cells are `panelHighlight` plates (invisible on black in enterprise: empty).
- Launcher pads keep the colours of the sequences (zynseq data), only the selection uses `marker`;
  piano keys of the pattern editor stay black and white.

### Pattern editor playhead

A deliberate deviation from Tk in every theme (the user's request, 2026-11-21): Tk moves a
step-wide block in the selection colour along the play ruler, step by step. The Qt UI draws a thin
vertical line across the grid (and the CC view) that moves smoothly, with a gradient tail behind it
(to the left, the direction of travel); the ruler keeps a small marker in the line's colour (it
moves with the line and stays at the position when stopped, where the line is hidden).

- **Position:** `PatternEditor._poll` (every 40 ms, as before) reads the sequence clock
  (`getSequencePlayPosition`) and divides it by the pattern's clocks per step, as
  `getPatternPlayhead` does but with the fraction and for this screen's sequence: `playPosition`
  (steps), `stepRate` (steps per second: tempo x steps per beat / 60, 0 while starting, stopped or
  when the clock hasn't moved for two polls: a paused transport), `playLength` (the sequence's
  length in steps: where it wraps).
- **Interpolation** (`PatternEditorView`, `clock`): every frame (`FrameAnimation`) or
  `playheadFps` times a second (`Timer`) the line is extrapolated from the last poll. A new poll
  doesn't move it: the difference to the extrapolation fades out over 150 ms (no jump, no drift);
  the extrapolation stops 120 ms after the last poll; it wraps at `playLength`; a difference over
  max(1 step, 150 ms) snaps (start, a jump). Tempo changes show as a short catch-up, a pause as a
  stop (with a fade back of up to 120 ms of motion).
- **Drawing:** `PatternPlayhead.qml`, plain `Rectangle`s with a horizontal `Gradient` (five stops),
  no shaders (the software renderer draws it). In the grid the tail is behind the notes and the
  line above them, so dense patterns stay readable. Near step 0 the tail continues at the pattern's
  end. Positions are rounded to whole pixels; only the line, the tail and the ruler marker change
  per frame, the grid isn't laid out again.
- **Values:** tk, classic and v4 a short, subtle tail (0.75 steps, alpha 0.22 at the line, linear);
  galactica and enterprise a radar sweep (3 steps, alpha 0.5 / 0.45, curve 2.2: bright at the line,
  a long faint afterglow) in their colours (galactica amber `#ffd27a` / `#f0ad3c`, enterprise
  blue-gray `#d9e0e3` / `#bbc6cb`); v4 updates 20 times a second.
- **Cost** (QEMU VM, zynthian pinned to one core with `taskset`, the editor playing at 120 BPM,
  60 notes): v4 at 480x320 with the software renderer, GUI thread / compositor: before 2.3 % /
  0.8 %, every frame 9.8 % / 3.8 %, 30 a second 6.3 % / 2.5 %, 20 a second 5.2 % / 1.9 %. tk at
  1280x800 with OpenGL (GUI + render thread + compositor): before 3.6 %, every frame 10 %.

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
  - qmlpreview reads commands from stdin and quits (terminating the UI: "Terminating process
    ...", exit 2) when it ends. The launcher runs zynthian as a background job that gets EIO
    from the tty at once, so qmlpreview gets a pipe that stays open (2026-11-18: without it the
    UI was killed at each start until tinydm restarted the session).
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

Start-up: only what the first frame shows is created when the QML loads; the other screens, the
controller widget views, the docked touch keypad, the on-screen keyboard and the launcher pads are `Deferred` (`Deferred.qml`, a `Loader`):
created at once when they are needed (shown), else after the first frame in the background
(`Startup.ready`, set on the window's first `frameSwapped`), and then kept as before. A part that
is hidden at first goes into a `Deferred` with an inline `Component`, so the theme's file
selectors pick its type as everywhere else:

```qml
Deferred {
    anchors.fill: parent
    visible: zyn.someCondition
    needed: zyn.someCondition       // the same condition: shown means created at once
    sourceComponent: Component { SomeView { view: zyn.someView } }
}
```

Set the visibility on the `Deferred` (the item inside follows it), give the item no size of its
own (it takes the `Deferred`'s), and refer to ids outside the `Deferred` (the inline component
sees them), not to the item inside from outside: it may not exist yet. Code that ran on
`onVisibleChanged` also needs `Component.onCompleted` (an item created while shown never sees the
change; `Keyboard.qml`). Without `needed`, the part appears only after the background creation,
which on a slow board takes a few seconds after the first frame. Measuring: performance-measurement.md, "Start-up,
Qt UI".

## Open

- Only the screens of `zynqt/qml/` are themed; new screens should use `Panel`/`Label` from the start.
- The plugin widgets (`PluginWidgetView`: tuner, meters), `EuclidSeqView`, `SooperLooperView` and
  `OrganelleView` follow the Tk widgets' colours; only their backgrounds are tokens so far.
- The mixer's meters use `meterLow`/`Mid`/`High` only; a segmented (LED) meter style would be a token
  and a variant of `Meter.qml`.
- The kiosk sessions export `ZYNTHIAN_QT_THEME` from `/etc/default/zynthian`; on the zynthian kits
  zynthian-kit sets it (v4 for 480x320 panels); the user's choice is Admin > Theme (above).
