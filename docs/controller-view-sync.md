# Controller view sync: the JAM's modes and step window on zynthian's screens

Status: plan agreed with the DrivenByMoss core (dbm-surface-link) on 2026-11-25. The zynthian
side (zynthian-ui and the zynthian adapter of drivenbymoss-rust) is implemented against the
agreed names. The core and JAM side is on drivenbymoss-rust `controller-view-sync` (3aac720,
7d74087: the window also with the host's step grid, which zynthian's adapter is); checked end to
end with the JAM in-process against the adapter (backends/zynthian/tests/test_views.py JamTest:
STEP sends view 2 and the window 0.0+2.0 beats, notes 36..47; NAV RIGHT 2.0+2.0; NAV UP notes
48..59; SONG view 0).

## Goal

With a Maschine JAM run by DrivenByMoss (DBM) as a zynthian ctrldev driver:

1. **SONG** (the JAM's session view, the clip launcher) shows zynthian's **pads view** (the
   launcher, "zynpad").
2. **STEP** (the JAM's sequencer views) shows zynthian's **pattern editor** with the pattern the
   JAM edits: the cursor clip, i.e. the selected phrase's sequence of the selected track's chain.
3. The pattern editor shows the **steps and notes the JAM shows**: the JAM's page of steps (start,
   length) and its rows (the lowest and highest note of the scale or drum rows). It follows when
   the user pages, changes the step size or scrolls the octave or the drum pads on the JAM.

## How Bitwig does it

Checked in the Java DrivenByMoss (`~/bastel/github/DrivenByMoss`) and in DBM's Bitwig host
(`drivenbymoss-rust/backends/bitwig/`):

- **The controller's modes do not switch Bitwig's views.** Only explicit layout functions do:
  on the JAM Shift + SONG toggles the Arrange and Mix panel layouts
  (`MaschineJamSessionViewCommand`, `IApplication.setPanelLayout`); other controllers have
  layout or pane buttons (Push / SL "Frame", Launchpad project view, Flexi, OSC, footswitch:
  `setPanelLayout`, `toggleNoteEditor`). The Rust core sends these as `ApplicationLayout`,
  `ApplicationLayoutStep`, `ApplicationToggleNoteEditor`; zynthian leaves them unhandled.
- **Bitwig's note editor does not follow the controller's window.** The sequencers edit the
  launcher cursor clip (`createLauncherCursorClip(steps, rows)`), the clip the note editor shows,
  but `scrollToStep`, `scrollStepsPageForward/Backwards`, `setStepSize` (and `scrollToKey`,
  which DBM doesn't use) move only the API's virtual step window. Bitwig's API cannot scroll or
  zoom the editor (`ClipLauncherSlot.showInEditor` only opens a clip; DBM doesn't call it).

So this is a feature beyond Bitwig. The concepts that map: "the cursor clip" is the pattern of
the cursor slot (the adapter's `ZynseqClip`, the one zynthian's pattern editor edits too), and a
view change is a host event like a panel layout change, sent only for explicit user actions.

## Mapping JAM view to zynthian screen

The core reports the view the user picked (`ControllerView`, a coarse kind usable by other
controllers too):

| Kind | JAM | zynthian |
|---|---|---|
| Launcher | SONG | pads view: CUIA `SCREEN_ZYNPAD` (not `SCREEN_LAUNCHER`, which in the launcher opens the pad's editor); nothing if the launcher is shown |
| Sequencer, DrumSequencer | STEP (each press, also cycling the sequencers) | pattern editor of the cursor slot: CUIA `SCREEN_PATTERN_EDITOR`; nothing if it already shows that pattern |
| Play, Mixer, Device, Other | pad modes, mixer modes, CONTROL | nothing (for now) |

`SCREEN_PATTERN_EDITOR` opens the active chain's sequence in the selected phrase, in the Qt UI
and in Tk, from the launcher (its `edit_pad`) and elsewhere. That is the adapter's cursor slot
(`ZynLauncher.selected_sequence()`): the core's slot and track selection are zynthian's selected
phrase and active chain. Nothing switches without a cursor slot (an audio or effect chain, the
main chain).

## The window: controller to zynthian

The core reports the visible window of its note grid (`ClipEditWindow`): `start`, `length` in
beats, `low`, `high` as MIDI notes (inclusive). The adapter passes it to the UI with the CUIA
`PATTERN_EDITOR_WINDOW start length low high pattern` (Qt UI only; Tk has no such CUIA yet and
the adapter doesn't send it there). The pattern editor:

- converts beats to steps with the pattern's steps per beat (zynseq's resolution; never changed):
  first step `round(start * spb)`, steps `max(1, round(length * spb))`;
- zooms so the steps and the rows fit (one zoom for the step width and the row height, so the
  closer of the two; within the grid's limits: at most 8 steps or 6 rows fill the grid; the zoom
  is kept with the pattern as the knob's zoom is), scrolls the first step to the left edge (8 JAM
  steps over 13 rows of a scale: the 8 steps and 6 more after them);
- maps the notes to its rows (the chain's keymap: chromatic or the drum map): the lowest row with
  a note >= `low` to the highest with a note <= `high`; centred if they fit, else the lowest at the
  bottom (the bottom row is stored as the pattern's reference note, as the user's scrolling);
- moves the cursor into the window if it was outside (the knobs then edit there).

A window for a pattern the editor doesn't show is kept and applied when the editor loads that
pattern. A window for another pattern than the one shown, while the editor is shown, means the
JAM's clip changed (track or slot selected on the JAM): the adapter first shows the new pattern
(`SCREEN_PATTERN_EDITOR`).

**Only controller to zynthian.** The JAM's window is discrete (pages of 8 or 16 steps, rows by
scale and octave or by pads), zynthian's is continuous (touch scrolling, pinch, any zoom). A
reverse sync would round in both directions and fight the user's scrolling. Possible later: a
host request (`ClipEditWindowRequest {start, low}`) that the core snaps to its page and octave.

## The protocol (agreed with dbm-surface-link)

- `ControllerView = 0x8D01` (group 0x8D "controller"), feature `ControllerViews`, payload the
  view kind (Launcher 0, Play 1, Sequencer 2, DrumSequencer 3, Mixer 4, Device 5, Other 6; open
  for later kinds: the host ignores unknown kinds). Sent **only when the user picks a view with a
  button** (SONG, STEP, pad and mixer mode buttons), also when the view stays the same; never on
  start, preferred-view recall, track change, refresh or settings change.
- `ClipEditWindow = 0x8750`, feature `ClipEditWindow`: `start: f64, length: f64` (beats),
  `low: i32, high: i32` (MIDI notes, inclusive). Sent after the `ControllerView` of a sequencer
  view, on every real window change (page, step size, octave or scale scroll, drum pad offset)
  and when the edited clip changes while a sequencer view is active; deduplicated. Drum
  sequencer: low..high are the visible pads' keys, also notes the drum map lacks.
- Both go only to hosts that declare them handled: the adapter handles them only with zynthian's
  UI (a ctrldev with its state manager), so Bitwig, the reference host and zynthian without a UI
  are unaffected.

## Edge cases

- **No clip / no pattern:** a cursor slot without a pattern opens the editor as a tap on its pad
  does (the editor's own handling). No cursor slot (audio chain, main chain): no switch, the window
  is ignored.
- **Empty sequence:** shown as any pattern; the window applies (the JAM's grid is empty too).
- **Pattern longer than the JAM's page:** the editor zooms to the page and scrolls to its start;
  the rest stays reachable by scrolling. A page beyond the pattern's end (the JAM pages past the
  clip length) scrolls to the end: the editor's grid ends with the pattern.
- **Scale mode on the JAM vs the editor's chromatic rows:** the JAM's 8 rows of a scale span more
  than 8 semitones; the editor shows the whole span low..high chromatically, zoomed out until it
  fits (then more steps than the JAM's page are visible, the page starting at the left). A span
  beyond the smallest zoom: the lowest row at the bottom. A drum map: the rows of the notes in
  the range.
- **Different step sizes:** the JAM's 1/16 on a 4-steps-per-beat pattern is one step per JAM
  step; other sizes give fractional windows (rounded to steps).
- **zynthian elsewhere:** a window while the editor is hidden only updates the stored window;
  it never switches screens.

## Not stealing the screen

The user plans split views on large screens, and touch-screen use must not be overridden by the
controller's refreshes. So screens switch **only on the view buttons** (the core sends
`ControllerView` for explicit presses only), and the window changes the editor only while it is
shown (or when it loads that pattern). Page and scroll presses on the JAM while zynthian shows
another screen don't switch it. A split view later can apply the window to an editor pane
without switching screens.

## Implementation

- zynthian-ui: `zynqt/screens/pattern_editor.py` (`show_window`, the stored window, `viewWindow`
  for QML), `zynqt/qml/PatternEditorView.qml` (`applyWindow`), `zynqt/ui.py`
  (`cuia_pattern_editor_window`).
- Adapter (drivenbymoss-rust `backends/zynthian/ctrldev/dbm_zynthian/`): `views.py` (`ZynViews`:
  the kinds to CUIAs, the window), `commands.py` (the handlers, registered only with the UI),
  the driver base sets its UI.
