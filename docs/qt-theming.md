# Theming the Qt Quick UI

Status: 2026-11-09, branch `qt-theme-galactica` (rebased onto `main`, the tomita-based Qt port). How
the look of the Qt Quick UI (`zynqt/qml/`) is defined, how to choose a theme, and how to change or
add one.

## Choosing a theme

`ZYNTHIAN_QT_THEME` picks the theme when zynthian starts; `zynthian_qt_main.py` passes it to QML as
the context property `zynThemeName`:

| Theme | Look |
|---|---|
| `classic` (default) | zynthian's colours (as `zynthian_gui_config`): black, slate-blue plates, red selection, blue keys, Audiowide |
| `galactica` | a battlestar CIC console: gun-metal plates with clipped corners and steel outlines, amber console text in Khand (upper case), an amber selection bar, red alerts |
| `enterprise` | a starship console: filled pill keys in orange, blue-gray, mauve and violet with dark labels, pill rows, mauve section headers, a curved frame (elbow) around the screens |

On the Duet (or in the QEMU VM): `export ZYNTHIAN_QT_THEME=enterprise` in `/etc/default/zynthian`
(sourced by the kiosk session, `/usr/libexec/zynthian/zynthian-session.sh`), then
`sudo systemctl restart tinydm`. On the desktop: set the
variable before `desktop/zynthian_desktop.sh` (with `ZYNTHIAN_UI=qt`) or `desktop/preview_qt.sh`.

The theme is fixed for a run: switching means restarting the UI.

## How it is built

Three pieces; screens and components use only these, no colours, fonts or radii of their own.

### `Theme.qml`: the tokens

A QML singleton (`qmldir`: `singleton Theme Theme.qml`). It holds one `QtObject` per theme
(`classic`, `galactica`, `enterprise`) with the same set of properties, selects one as `p` by
`name`, and exposes each property as `Theme.<token>` (`readonly property color panel: p.panel`).
Components read `Theme.panel`, never `Theme.galactica.panel`.

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

`isGalactica` and `isEnterprise` exist for the few places where a theme differs in layout, not
only in values (key margins, the top bar's rule and segments). Prefer a token: a new theme should
not need edits in the components.

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

### `Elbow.qml`: the enterprise frame

One filled `ShapePath`: a horizontal arm under the top bar, joined to a wider vertical bar left of
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

1. Copy a theme block in `Theme.qml` (`property QtObject mytheme: QtObject { ... }`) and give every
   token a value; QML reports a missing one as `undefined` at runtime, not at load.
2. Add it to the selection of `p` (`name === "mytheme" ? mytheme : ...`), and an `isMytheme` only if
   a component really needs it.
3. Fonts: use a face installed on the Duet (`fc-list : family` there; zynthian's fonts are in
   `/usr/share/fonts/zynthian`: Audiowide, Khand, Fjalla One, Electrolize, Exo 2, Jura, Iceland, ...).
   Condensed faces need a `fontScale` above 1.
4. Check every screen with the preview (below) in the new theme and in `classic`: classic's look
   must not change.
5. Document it in the table at the top.

## Changing a component

- Plates: `Panel`, with `button: true` for keys and buttons; no `Rectangle` with its own colour.
- Text: `Label`; `body: true` where case matters.
- Colours from tokens only. If a component needs a colour no token covers, add a token to all
  themes (with the old value in classic), instead of a literal.
- Selected entries: `select` behind, `selectText` on it (not `text`: in galactica and enterprise
  the selection is light).

## Previewing

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

In the QEMU VM (`docs/qemu-testing.md`; Khand is installed there): `nura/tools/sync_ui.sh -V -r`,
`export ZYNTHIAN_QT_THEME=...` in the VM's `/etc/default/zynthian`, `sudo systemctl restart tinydm`,
CUIAs with `oscsend localhost 1370 /cuia/...` in the VM, `nura/tools/screenshot.sh -V`.

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
- The kiosk package doesn't know the theme yet: `ZYNTHIAN_QT_THEME` in `/etc/default/zynthian` is set
  by hand (export it there).
