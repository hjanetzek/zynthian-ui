# Chain control as a grid of pages (Qt UI)

Status: 2026-11-24, branch `electra-grid`. Layouts `grid4x6` and `grid8x6` for chain control,
next to the default `v5` layout (the page list and four controllers in a column). Inspired by the
Electra One mk2's control grid (coloured cells with name, value and a bar or arc; rows mapped to
the encoders), not a copy of its look.

## What it shows

| Layout | Columns × rows | Pages a row | Pages shown |
|---|---|---|---|
| `v5` (default) | the page list, 4 controllers in a column | – | 1 |
| `grid4x6` | 4 × 6 | 1 | 6 |
| `grid8x6` | 8 × 6 | 2 | 12 |

- A zynthian controller page keeps its four controllers together, in order, in one row (four
  cells). Pages fill the rows in order: in 8x6 page *p* is in row *p* div 2, left or right
  half. A page with fewer than four controllers has blank (recessed) cells; a processor without
  pages (no preset loaded yet) is a page with "No controllers".
- Each page has a header: its title, and its section (the processor, or "Chain" for the chain's
  controllers) at the right, with the section's colour.
- The **selected page** (the one the four encoders turn) has its header in the selection colour
  and a frame (`frameActive`) around its four cells; in 8x6 that marks one half of a row.
- **The page list** stays at the left (`controlGridList` of the width, tk 0.2) when there is room:
  not in select mode (the side chain is shown there instead), not after `HIDE_SIDEBAR`, and only
  while the cells stay at least `controlCellMinWidth` (96 px) wide. The pages the grid shows are
  marked with a bar at the list's left edge (`frameActive`).
- **The window**: six rows of the pages; it scrolls by rows to keep the selected page in view. A
  bar at the right edge shows which part of the pages is shown (only with more pages than fit).
- Pages with a **widget** (envelope, filter, drawbar, audio file, plugin widgets, euclid,
  organelle, SooperLooper, the "unsupported" notice) stay in the grid as normal cells. When the
  selected page is such a page, its widget shows **over the page's area** (its header and four
  cells; in 8x6 the row-half) for `controlGridWidgetMs` (1800 ms) after a change, then fades out
  (200 ms opacity animation, no shader). A change is: one of the page's values changing (encoder,
  cell drag or tap, MIDI or the engine: anything that reaches `ChainControl.zctrl_changed`,
  including the grid's value watcher), or the page being selected. Each further change restarts
  the timeout; the changed controller's name and value text are drawn at the top right of the
  widget (no text after a selection). One overlay at a time: the selected page's.
- The overlay is **not interactive** (`enabled: false`): touch goes to the cells beneath, so a
  drag on a cell keeps changing the value while the widget shows the result. The widgets' own
  touch (dragging the envelope or the filter curve, the Organelle's and SooperLooper's buttons,
  the Euclid sequencer) is only in the v5 layout. A widget page that isn't selected shows no
  overlay when its values change (a drag on it): chain control's widget views follow the
  selected page only.
- The overlay holds a second `ControlWidget` (`lazy: true`: each view created when first
  shown), bound to the same Python view models as the v5 layout's hidden one. The views that
  size their model (`EnvelopeView`, `FilterView`, `WaveformView`: `view.setSize`) set it again
  whenever they become visible, so the overlay's smaller size wins while it shows and the v5
  size when v5 shows. Checked at 1920x1200 in tk, classic and enterprise, 4x6 and 8x6: Helm's
  filter and envelopes, Noize Mak3r's envelope, the 1/3 octave spectrum plugin widget, the
  audio player's waveform; they draw correctly at the group's size (4x6 ~1500x170, 8x6 ~750x170
  px). Drawbar, Euclid, Organelle and SooperLooper views weren't checked at that size.

## Interaction

Encoders and keys work as in the v5 layout; only what is drawn differs.

- **Encoders**: knobs 0-3 (`ZYNPOT 0..3`) turn the selected page's four controllers (chain
  control's four controller slots, `ChainControl.controllers`, are always the selected page's);
  push-rotate fine, MIDI learn by knob push, bold push the options: unchanged.
- **Moving the selection**: as the page changes in v5: `ARROW_UP` / `ARROW_DOWN`, the SELECT knob
  in select mode, the page list, the side chain's processors (select mode). In 8x6 one step moves
  to the next half (left, right, next row left). The ends of the page list don't wrap (as v5).
- **Touch on a cell**:
  - drag up / down: changes it like an encoder (one step per 8 px, as `ControllerTouch`), on any
    page, without moving the selection;
  - tap: selects its page; a toggle switches, a trigger fires, a list steps to its next label
    (wrapping at the end), a file controller opens the file selector; a continuous controller
    only selects. While MIDI learning: selects its page and learns it;
  - long press: selects its page and opens the controller's options (MIDI learn, X-Y, chain
    controller, ...), as the controller column's long press;
  - wheel: nudges it.
- **Touch on a page header**: selects the page (no value change). A tap on the selected processor
  without pages opens its banks / presets, as in the page list.
- **Scroll bar**: a tap above or below the thumb scrolls by six rows, a drag moves the window; the
  wheel over headers and gaps scrolls by a row.
- Everything else as v5: the side chain in select mode, chain options, MIDI learn (the banner, the
  cells' bindings blink "??#??"), processor moves, transport keys.

## The model (`zyngui/zynthian_control_grid_data.py`)

UI independent (no Qt, no Tk), so other consumers can share it later (e.g. mapping the grid onto a
controller's pad grid). Nothing of that is built.

- `GridPage(key, title, section, section_index, zctrls, empty)`: one controller page.
- `LAYOUTS`: `GridLayout(name, columns, rows, pages_per_row)` for `grid4x6`, `grid8x6`.
- `ControlGrid`: `pages`, `layout`, `first_row` (the window), `selected` (a page index),
  `selected_row`, `selected_half`, `selected_zctrl` (the anchor: the selected page's first
  controller, for views with other row widths), `cells` (rows × columns `GridCell`s in reading
  order; cell id = row · columns + column).
- `GridCell`: `row`, `column`, `id`, `slot` (0-3 in its page), `page` (-1: none), `zctrl`, and
  `kind` (`empty`, `float`, `integer`, `list`, `toggle`, `trigger`, `path`), `name`, `value`,
  `value_text` (the zctrl's label for its value), `fraction` (0..1), `items` (a list's labels and
  values), `enabled` (has a controller, not read-only). The functions behind them (`cell_kind`,
  `cell_value_text`, `cell_fraction`, `cell_origin`, `cell_list_index`, `cell_items`) are shared
  with the Qt cells.
- Events (`add_listener(cb)`): `("structure", None)` pages, layout or window changed (cells hold
  other controllers), `("state", None)` only the selection changed, `("values", cells)` from
  `poll(watcher)`.
- **Values are compared, not flagged**: `ValueWatcher` (one per consumer) remembers each cell's
  controller and value and returns the changed cells. The model never reads or resets
  `zctrl.is_dirty`: chain control's four controller slots consume that flag (as before), and two
  consumers of it would steal each other's updates. Cost: 48 comparisons per 50 ms tick.
- Input methods: `select_page`, `select_row`, `select_cell` (through `on_select` when the owner
  set it: chain control selects the page and the model follows), `turn(cell, delta, fine)`,
  `press(cell)`, `release`, `touch`, `set_default`.
- Not thread safe: use it from the GUI thread.

## The Qt side

- `zynqt/screens/control_grid.py`: `ControlGridModel` (QObject, `zyn.chainControl.gridModel`)
  wraps a `ControlGrid` for QML: `cells` (48 `GridCellProxy`s, created once), `blocks` (the
  window's pages, row by row: title, section, sectionIndex, selected, empty, valid, first),
  `columns`, `rows`, `pagesPerRow`, `firstRow`, `totalRows`, `firstEntry` / `lastEntry` (the page
  list rows shown), slots `tapPage`, `scrollRows`, `scrollTo`. `GridCellProxy` is a
  `ControllerProxy` (the controller column's slot: name, value text, binding, options) plus
  `kind`, `enabled`, `origin`, `listIndex`, `listCount`, `gridName`, `valid`, `selected`,
  `sectionIndex`, and the touch slots `tapped`, `nudge`, `options`, `touched`.
- `ChainControl` (`zynqt/screens/control.py`): `controlLayout`, `gridLayout`, `gridShown`
  (a grid layout), `gridWidgetPoke(name, value)` (show the selected page's widget over it), `setThemeLayout` (from `Main.qml`), `set_layout_setting`
  (Admin). It builds the grid's pages with the page list (`_build`), selects in it on every page
  change (`setPage`), polls it (only while shown: the window's cells, at most 48, by value) in
  the 50 ms timer next to its four slots. `zctrl_changed(zctrl)` updates every slot showing a
  controller (the grid's and the column's) after a change through one of them.
- QML: `ChainControlScreen` (shared) loads `ControlGrid` (shared: layout, page list, scroll bar,
  touch) in a `Loader` that is active only in a grid layout, so v5 creates nothing new. Cells and
  pages are created once per layout (`rows × pagesPerRow` pages, four cells each); only their
  content changes. The theme looks: `ControlCell` (a cell) and `ControlGridPage` (a page's header
  and frame), touch `ControlCellTouch` (shared).

## Looks per theme

| Theme | Cell | Page header |
|---|---|---|
| tk (`ControlCell.qml`, `ControlGridPage.qml`) | Tk's controller: square `panel` plate, Audiowide, a 300° arc at the right in the section colour (from the zero of ranges across it; a list a segment at its label's place), toggles a square lit when on, triggers an empty square; 1 px gaps | `separator` bar with a section-coloured stripe at the left; selected: `select` (red) with the yellow `frameActive` frame |
| classic (`+classic/ControlCell.qml`, `+classic/ControlGridPage.qml`) | a `Panel` plate: name, value text, a bar along the bottom in the section colour (lists: a segment per label, the value's lit; toggles two segments and a lamp) | title on a section-coloured line |
| galactica (classic's files) | clipped corners (`cut`), Khand caps, the bar in 12 segments (`controlCellSegments`), amber / status colours by section | as classic |
| enterprise (classic's files) | rounded plates, pill bars and lamps, the keys' palette by section | pills filled in the section colour with dark text (`controlGridHeaderFilled`) |
| v4 | – (`controlGrid: false`: its own four-knob layout, the setting is ignored) | – |

Tokens (`ThemeBase.qml`): `controlLayout` (the default when the user chose none: `v5` in all
themes), `controlGrid` (the theme has the grid layouts; v4 false), `controlGridList`,
`controlCellMinWidth`, `controlGridGap`, `controlGridColors` (by section; empty: `select`),
`controlGridHeaderFilled`, `controlCellSegments`.

Texts stay inside the cells: names wrap on at most two lines and elide; values shrink to fit
(`Text.HorizontalFit`, down to 7-8 px) and then elide; header titles and sections elide.

## Choosing the layout

- `ZYNTHIAN_QT_CONTROL_LAYOUT` = `v5` | `grid4x6` | `grid8x6`; unset or empty: the theme's
  default (`Theme.controlLayout`, `v5` everywhere). Read at start (`ChainControl.__init__`).
- Admin > User Interface > **Chain Control Layout (...)**: Default (theme's), 4 controllers,
  Grid 4x6, Grid 8x6. Applied at once and saved in zynthian's config (`zynconf.save_config`).
  Not shown in themes without the grid (v4).
- Theme switches (Admin > Theme) keep the choice; `Main.qml` passes the new theme's default and
  `controlGrid` on every QML load.

## Performance

Measured in the QEMU VM (1280x800, tk, Helm chain, Python side incl. the synchronous QML
binding updates): a page step 1.7 ms in v5, 6.3 ms in 8x6, 6.8 ms in 4x6 (the 24 / 48 cells and
the page headers updated); the 50 ms poll 3 us in v5, 5-7 us with the grid's value watcher. The
grid's QML exists only while a grid layout is chosen (`Loader`); its pages and cells are created
once per layout. Not measured on a device yet.

## Screen sizes

- 1280x800 and 1280x720: both layouts with the page list; with the docked keypad 8x6 cells are
  ~100 px wide (the list stays while cells are at least 96 px).
- 800x480: 4x6 with the page list; 8x6 without it (cells ~95 px wide, about 50 px high): usable
  for reading and the encoders, small for touch. In galactica and enterprise (fixed classic sizes)
  the page list's large rows and the small cell texts make 800x480 cramped; tk scales.
- The page list doesn't re-scroll to the selected page when the window is resized (also v5).

## Left for later

- The widgets' own touch in the grid (the overlay is view-only), and overlays for widget pages
  that aren't selected.
- Other sizes (e.g. 6 or 8 columns with other page arrangements): add a `GridLayout` and, if a
  page should not be one row, a placement rule in `ControlGrid._fill` / `page_at`.
- Mapping the grid onto a control surface (e.g. a pad grid through DrivenByMoss): the model is UI
  independent and has the input methods and its own value watcher for that; nothing is built.
- A per-zctrl change signal (the grid polls by value, which also sees engines that write
  `zctrl.value` directly).
