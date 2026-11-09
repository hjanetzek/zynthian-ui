"""Pattern editor, notes (zynthian_gui_pated_notes): the selected launcher pad's pattern as a grid,
steps across, the keymap's notes (chromatic, a scale, or the synth's drum map) up the side.

Tap an empty cell to add a note (velocity and duration of the note-entry values), tap a note to
remove it, long press a note for its velocity and duration. Arrows move the cursor, SEL toggles
the note at the cursor. The keymap, events and new note defaults are shared with the Tk editor
(zyngui.zynthian_pated_data)."""

import os

from PySide6.QtCore import QObject, QTimer, Property, Signal, Slot

from zyngui.zynthian_pated_data import (CHORD_MODES, CHORDS, NOTE_NAMES, NOTE_PARAM_DEFAULTS, NOTE_PARAMS,
                                        STEPS_PER_BEAT, chord_intervals, default_note_evdata, load_keymap,
                                        note_events, note_label, note_muted, note_name, note_param_text,
                                        scale_names, set_note_param, stutter_muted)
from zyngui.zynthian_pated_smf import PATTERNS_DIR, SMF_EXPORT_DIR, analyze_smf, export_smf, import_smf
from zynlibs.zynseq import zynseq
from zynqt.screens.file_picker import FilePicker

# Edit modes (zynthian_gui_pated_base): what the knobs and SELECT do
EDIT_MODE_NONE = 0      # move the cursor, SELECT toggles the note
EDIT_MODE_BLOCK = 1     # select a block (knobs), copy it, move the copy, paste it
EDIT_MODE_SINGLE = 2    # the note's (or the new notes') parameters
EDIT_MODE_MULTI = 3     # duration and velocity of the selected notes
EDIT_MODE_HISTORY = 4   # undo / redo

# Parameters of the single note edit mode (EDIT_PARAM_* of zynthian_gui_pated_notes): duration,
# velocity, then NOTE_PARAMS; the titles as Tk's set_edit_title
EDIT_PARAM_TITLES = ("Duration", "Velocity", "Offset", "Stutter speed", "Stutter velo", "Stutter ramp",
                     "Play frequency", "Play chance", "Stutter frequency", "Stutter chance")
EDIT_PARAM_LAST_MULTI = 1


class PatternEditor(QObject):
    name = "pattern_editor"

    patternChanged = Signal()       # pattern, length, keymap: the whole grid
    eventsChanged = Signal()
    playheadChanged = Signal()
    cursorChanged = Signal()
    entryChanged = Signal()         # note-entry values (velocity, duration)
    ccChanged = Signal()            # CC view: mode, CC number, values
    blockChanged = Signal()         # select mode, selected block, copied buffer
    recordChanged = Signal()        # recording from MIDI
    modeChanged = Signal()          # edit mode, its parameter, the title
    zoomChanged = Signal()

    def __init__(self, ui, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.zynseq = ui.state_manager.zynseq
        self.libseq = self.zynseq.libseq
        self.pattern = 0
        self.phrase = 0
        self.sequence = 0
        self.channel = 0
        self.bpb = 4
        self.keymap = []
        self.keymap_name = ""
        self._events = []
        self._playhead = -1
        self._playing = False
        self.cursor = [0, 60]      # step, keymap row
        self.velocity = 100
        self.duration = 1.0
        self.entry_params = dict(NOTE_PARAM_DEFAULTS)   # the other note-entry values (offset, stutter, ...)
        self.chord_mode = 0         # CHORD_MODES index
        self.chord_type = 0         # CHORDS index (chord mode 1)
        self.chord_tonic = 0        # key of the diatonic chords
        self.cc_mode = False        # CC view instead of the notes
        self.cc_num = 1             # (zynthian_gui_pated_cc starts on CC1)
        self.cc_cursor = 0          # step
        self.cc_row = 60            # the value row of the cursor (zynthian_gui_pated_base: selected_cell [0, 60])
        self.cc_show_all = False    # the CC knob also offers CCs without a controller (V5 knob 0 bold)
        self.select_mode = False    # block edit mode: touch selects a block instead of adding notes
        self.edit_mode = EDIT_MODE_NONE
        self.edit_param = 0         # EDIT_PARAM_TITLES index
        self._block_start = None    # block selection with the knobs: start and end cell [step, row]
        self._block_end = None
        self._cp_offset = [0, 0]    # copied block moved by [steps, rows] (knobs)
        self.selected_events = None  # selected notes ({event key: True}, zynseq.get_pattern_selection)
        self.zoom = 0               # cell size change in pixels (knob 1), as Tk's set_grid_zoom
        self._zoom_limits = (-1000, 1000)
        self._block = None           # selected block: [step1, row1, step2, row2] (inclusive)
        self.copied = None          # copied block (its [step1, row1, step2, row2]); taps paste it
        self._pending = False       # changes without their undo snapshot yet
        self.last_smf_import = {}   # pattern: the MIDI file imported last (where the picker starts)
        # Whole patterns copied by COPY i / pasted by PASTE i (zynthian_gui_mixer's clipboard):
        # (phrase, sequence, pattern) per slot
        self.clipboard = 4 * [None]
        self._timer = QTimer(self, interval=40)
        self._timer.timeout.connect(self._poll)
        # libseq's selected pattern is only valid while the screen is shown (load() selects it):
        # before, none is selected, and a snapshot load deletes the patterns but leaves the
        # selection pointing at the old one. QML evaluates the bindings when it creates the
        # (hidden) screen: reading the pattern then crashed in Pattern::getControlValue.
        self._shown = False

    # Screen (ZynUI): shown / hidden

    def build(self):
        self._shown = True
        self.load()
        self._timer.start()

    def hide(self):
        self._shown = False
        self._timer.stop()
        # As zynthian_gui_pated_base.hide: no recording into a pattern that isn't shown, no edit
        # mode
        self.setRecording(False)
        if self.edit_mode != EDIT_MODE_NONE:
            self.set_edit_mode(EDIT_MODE_NONE)

    # Recording from MIDI (zynthian_gui_pated_base.toggle_midi_record): libseq writes the notes
    # played into the pattern while it plays; _poll shows them (isPatternModified)

    @Property(bool, notify=recordChanged)
    def recording(self):
        return bool(self.libseq.isMidiRecord())

    @Slot(bool)
    def setRecording(self, on):
        if bool(self.libseq.isMidiRecord()) != on:
            self._flush_pending()
            self.libseq.enableMidiRecord(on)
            self.recordChanged.emit()

    @Slot()
    def toggleRecording(self):
        self.setRecording(not self.libseq.isMidiRecord())

    # Transport keys here: the pattern (zynthian_gui_pated_base cuia_toggle_record / stop / play)

    def cuia_toggle_record(self, params=None):
        self.toggleRecording()
        return True

    def cuia_stop(self, params=None):
        self.libseq.setPlayState(self.zynseq.scene, self.phrase, self.sequence, zynseq.SEQ_STOPPED)
        return True

    def cuia_toggle_play(self, params=None):
        self.togglePlayback()
        return True

    # COPY / PASTE i: the whole pattern to / from clipboard slot i (zynthian_gui_pated_base
    # copy_pattern / paste_pattern)

    def cuia_copy(self, params=None):
        i = int(params[0]) if params else 0
        if 0 <= i < len(self.clipboard):
            self.clipboard[i] = (self.phrase, self.sequence, self.pattern)
            self.ui.show_info(f"Pattern {self.pattern} copied to clipboard {i + 1}")
        return True

    def cuia_paste(self, params=None):
        i = int(params[0]) if params else 0
        src = self.clipboard[i] if 0 <= i < len(self.clipboard) else None
        if src is None:
            self.ui.show_info("Nothing to paste")
        elif src[2] == self.pattern:
            self.ui.show_info("Can't paste a pattern over itself")
        elif self.libseq.isPatternEmpty(self.pattern):
            self._paste_pattern(src)
        else:
            name = self.zynseq.get_sequence_name(self.zynseq.scene, src[0], src[1])
            self.ui.confirm(f"Overwrite this pattern with {name}?", lambda: self._paste_pattern(src))
        return True

    def _paste_pattern(self, src):
        zs = self.zynseq
        self._flush_pending()
        self.libseq.copyPattern(src[2], self.pattern)
        # The sequence name too, as Tk
        zs.set_sequence_param(zs.scene, self.phrase, self.sequence, "name",
                              zs.get_sequence_name(zs.scene, src[0], src[1]))
        self.libseq.selectPattern(self.pattern)
        self._snapshot()
        self.load()

    def load(self):
        """The active chain's sequence in the selected phrase (zynthian_gui_mixer.edit_pattern)"""
        chain = self.ui.chain_manager.get_active_chain()
        zs = self.zynseq
        self.phrase = zs.phrase
        self.sequence = self.channel = chain.midi_chan if chain and chain.midi_chan is not None else 0
        try:
            self.bpb = zs.state["scenes"][zs.scene]["phrases"][self.phrase]["bpb"] or zs.bpb
        except Exception:
            self.bpb = zs.bpb or 4
        self.pattern = self.libseq.getPattern(zs.scene, self.phrase, self.sequence, 0, 0)
        self.libseq.setChannel(zs.scene, self.phrase, self.sequence, 0, self.channel)
        self.libseq.selectPattern(self.pattern)
        self.keymap_name, self.keymap = load_keymap(self.ui.chain_manager, self.channel, self.libseq.getScale(),
                                                    self.libseq.getTonic())
        self._events = note_events(self.libseq)
        # The cursor as zynthian_gui_pated_notes.load_pattern: the step kept (within the
        # pattern), the row in the middle of the view from the pattern's reference note (the
        # bottom row shown, libseq's RefNote; 16 rows shown at zoom 0)
        if self.cursor[0] >= self.steps:
            self.cursor[0] = self.steps - 1
        view_rows = 16
        offset = int(self.libseq.getRefNote()) if len(self.keymap) > view_rows else 0
        offset = max(0, min(offset, len(self.keymap) - view_rows))
        self.ref_row = offset
        self.cursor[1] = max(0, min(len(self.keymap) - 1, offset + view_rows // 2))
        self.libseq.isPatternModified()   # reset the flag
        self._pending = False
        self.selected_events = None
        self.copied = None
        # The pattern's zoom (Tk: set_grid_zoom(getPatternZoom()), within the grid's limits; a
        # pattern without one gives garbage)
        z = self.libseq.getPatternZoom()
        self.zoom = max(self._zoom_limits[0], min(self._zoom_limits[1], z)) if -1000 < z < 1000 else 0
        self.zoomChanged.emit()
        self.patternChanged.emit()
        self.eventsChanged.emit()
        self.cursorChanged.emit()
        self.ccChanged.emit()

    def _poll(self):
        step = self.libseq.getPatternPlayhead()
        playing = self.libseq.getPlayState(self.zynseq.scene, self.phrase, self.sequence) != zynseq.SEQ_STOPPED
        if step != self._playhead or playing != self._playing:
            self._playhead = step
            self._playing = playing
            self.playheadChanged.emit()
        if self.libseq.isPatternModified():
            # Changed elsewhere (MIDI recording): an undo step before the next change
            self._pending = True
            self._events = note_events(self.libseq)
            self.eventsChanged.emit()
            self.ccChanged.emit()

    # For QML

    @Property(int, notify=patternChanged)
    def steps(self):
        return self.libseq.getSteps() if self._shown else 16

    @Property(int, notify=patternChanged)
    def stepsPerBeat(self):
        return self.libseq.getStepsPerBeat() if self._shown else 4

    @Property(int, notify=patternChanged)
    def beatsPerBar(self):
        return self.bpb

    @Property(str, notify=patternChanged)
    def title(self):
        name = self.zynseq.get_sequence_name(self.zynseq.scene, self.phrase, self.sequence)
        return f"Pattern {self.pattern} ({name}) — {self.keymap_name}"

    @Property("QVariantList", notify=patternChanged)
    def rows(self):
        """Keymap rows, bottom to top: {note, name, black}"""
        return [{"note": k["note"], "name": k.get("name", ""), "black": k.get("colour") == "black"}
                for k in self.keymap]

    @Property("QVariantList", notify=eventsChanged)
    def events(self):
        """Notes: {step (with offset), row, duration, velocity, label, muted, stutter (retriggers per
        step, 0: none), stutterFx (0 flat, 1 fade-in, 2 fade-out), stutterMuted}; notes outside the
        keymap are left out"""
        row_of = {k["note"]: i for i, k in enumerate(self.keymap)}
        return [{"step": e.position + e.offset, "row": row_of[e.val1_start], "duration": e.duration,
                 "velocity": e.val2_start, "label": note_label(e), "muted": note_muted(e),
                 "stutter": e.stut_speed, "stutterFx": e.stut_velfx, "stutterMuted": stutter_muted(e),
                 "selected": bool(self.selected_events) and e.get_key() in self.selected_events}
                for e in self._events if e.val1_start in row_of]

    @Property(int, notify=playheadChanged)
    def playhead(self):
        return self._playhead

    @Property(bool, notify=playheadChanged)
    def playing(self):
        return self._playing

    @Property("QVariantList", notify=cursorChanged)
    def cursorCell(self):
        return list(self.cursor)

    @Property(str, notify=entryChanged)
    def entryText(self):
        chord = "" if not self.chord_mode else (
            f"  {CHORDS[self.chord_type][0]}" if self.chord_mode == 1 else "  Diatonic")
        extra = "".join(f"  {p['name']} {note_param_text(p, self.entry_params[p['key']])}" for p in NOTE_PARAMS
                        if self.entry_params[p["key"]] != NOTE_PARAM_DEFAULTS[p["key"]])
        return f"Vel {self.velocity}  Dur {self.duration:g}{chord}{extra}"

    # CC view (zynthian_gui_pated_cc): one CC number, a value (0..127) or none per step

    @Property(bool, notify=ccChanged)
    def ccMode(self):
        return self.cc_mode

    @Property(str, notify=ccChanged)
    def ccTitle(self):
        zctrl = self.ui.chain_manager.get_zynstep_mapped_zctrl(self.channel, self.cc_num)
        return f"CC {self.cc_num}" + (f" ({zctrl.name})" if zctrl else "")

    @Property(bool, notify=ccChanged)
    def ccInterpolate(self):
        return self._shown and bool(self.libseq.getInterpolateCC(self.cc_num))

    @Property("QVariantList", notify=ccChanged)
    def ccValues(self):
        """Per step: [value, end value, duration] or None"""
        values = []
        if not self._shown:
            return values
        for step in range(self.libseq.getSteps()):
            v = self.libseq.getControlValue(step, self.cc_num)
            if v <= 127:
                values.append([v, self.libseq.getControlValueEnd(step, self.cc_num),
                               self.libseq.getControlDuration(step, self.cc_num)])
            else:
                values.append(None)
        return values

    @Property(int, notify=ccChanged)
    def ccCursor(self):
        return self.cc_cursor

    @Slot()
    def toggleCcMode(self):
        self.cc_mode = not self.cc_mode
        if self.edit_mode != EDIT_MODE_NONE:
            self.set_edit_mode(EDIT_MODE_NONE)
        if self.cc_mode:
            self._cc_select()
        self.ccChanged.emit()
        self.patternChanged.emit()   # the title

    @Slot(int, int)
    def setCc(self, step, value):
        """Set (or add) the CC value of step; for painting with a finger"""
        if not 0 <= step < self.steps:
            return
        value = max(0, min(127, value))
        if self.libseq.getControlValue(step, self.cc_num) <= 127:
            self.libseq.setControlValue(step, self.cc_num, value, value)
        else:
            self.libseq.addControl(step, self.cc_num, value, value, 1, 0)
        self.cc_cursor = step
        self.cc_row = value
        self._pending = True    # one undo step at the end of the gesture (ccEditDone)
        self.libseq.isPatternModified()
        self.ccChanged.emit()

    @Slot()
    def ccEditDone(self):
        """End of a paint gesture: one undo step"""
        self._flush_pending()

    @Slot(int)
    def removeCc(self, step):
        if 0 <= step < self.steps and self.libseq.getControlValue(step, self.cc_num) <= 127:
            self._flush_pending()
            self.libseq.removeControl(step, self.cc_num)
            self._snapshot()
            self.libseq.isPatternModified()
            self.cc_cursor = step
            self.ccChanged.emit()

    @Slot()
    def pickCc(self):
        def label(n):
            zctrl = self.ui.chain_manager.get_zynstep_mapped_zctrl(self.channel, n)
            return f"CC {n}" + (f" ({zctrl.name})" if zctrl else "")

        def apply(n):
            self.cc_num = n
            self._cc_select()
            self.patternChanged.emit()

        self._pick("CC number", [(label(n), n) for n in range(1, 128)], self.cc_num, apply)

    # CC editor keys and knobs as zynthian_gui_pated_cc: a step and a value row cursor; knob 0
    # the CC number, knob 2 the value (of the step's event) or the row, knob 3 the step

    @Property(int, notify=ccChanged)
    def ccRow(self):
        return self.cc_row

    def _cc_value(self, step):
        v = self.libseq.getControlValue(step, self.cc_num) if self._shown else 255
        return v if v <= 127 else None

    def _cc_select(self, step=None, row=None):
        """zynthian_gui_pated_cc.select_cell: the cursor on the step's event value, else row"""
        step = self.cc_cursor if step is None else step
        step = max(0, min(self.steps - 1, int(step)))
        val = self._cc_value(step)
        if val is not None:
            row = val
        else:
            row = self.cc_row if row is None else max(0, min(127, int(row)))
        self.cc_cursor, self.cc_row = step, row
        self.ccChanged.emit()

    def nudge_cc_num(self, dval=0):
        """The next CC with a controller mapped (all CCs with cc_show_all), as nudge_cc_num"""
        cm = self.ui.chain_manager
        cc = 0 if dval == 0 else self.cc_num
        while (dval >= 0 and cc < 127) or (dval < 0 and cc > 1):
            cc += 1 if dval >= 0 else -1
            if self.cc_show_all or cm.get_zynstep_mapped_zctrl(self.channel, cc):
                self.cc_num = cc
                self._cc_select()
                self.patternChanged.emit()
                return

    def _cc_toggle(self):
        step, row = self.cc_cursor, self.cc_row
        self._flush_pending()
        if self._cc_value(step) is None:
            self.libseq.addControl(step, self.cc_num, row, row, 1, 0)
        else:
            self.libseq.removeControl(step, self.cc_num)
        self._snapshot()
        self.libseq.isPatternModified()
        self._cc_select()

    def _cc_zynpot(self, i, d):
        m = self.edit_mode
        if i == self._ctrl(0):
            if m == EDIT_MODE_NONE:
                self.nudge_cc_num(d)
        elif i == self._ctrl(1):
            self.setZoom(self.zoom + d)
        elif i == self._ctrl(2):
            if m == EDIT_MODE_NONE:
                step = self.cc_cursor
                val = self._cc_value(step)
                if val is not None:
                    new = max(0, min(127, val - d))
                    if new != val:
                        self._flush_pending()
                        self.libseq.setControlValue(step, self.cc_num, new, new)
                        self._pending = True
                        self.libseq.isPatternModified()
                self._cc_select(step, self.cc_row - d)
        elif i == self._ctrl(3):
            if m == EDIT_MODE_HISTORY:
                self.redo() if d > 0 else self.undo()
                self.ccChanged.emit()
            elif m == EDIT_MODE_NONE:
                self._cc_select(self.cc_cursor + d, None)
        return True

    def _cc_navigate(self, what):
        if what in ("left", "right"):
            if self._history_keys():
                self.redo() if what == "right" else self.undo()
                self.ccChanged.emit()
            else:
                self._cc_zynpot(self._ctrl(3), 1 if what == "right" else -1)
        elif what in ("up", "down"):
            if self._history_keys():
                self.redo_all() if what == "up" else self.undo_all()
                self.ccChanged.emit()
            else:
                self._cc_zynpot(self._ctrl(2), -1 if what == "up" else 1)
        elif what == "select":
            if self.edit_mode == EDIT_MODE_NONE:
                self._cc_toggle()
            else:
                self.set_edit_mode(EDIT_MODE_NONE)

    # Editing (undo snapshots around each change, as the Tk editor)

    def _note(self, row):
        return self.keymap[row]["note"] if 0 <= row < len(self.keymap) else None

    # Undo steps as zynthian_gui_pated_base: a pattern snapshot after each change (libseq keeps the
    # states, the first one from when the pattern was created or loaded). Changes not saved yet
    # (CC painting in progress, MIDI recording) get theirs before the next change or an undo.

    def _snapshot(self):
        self.libseq.savePatternSnapshot()
        self._pending = False

    def _flush_pending(self):
        if self._pending:
            self._snapshot()

    def _reload_events(self):
        self._events = note_events(self.libseq)
        self.libseq.isPatternModified()
        self.eventsChanged.emit()
        self.ccChanged.emit()

    def _changed(self):
        self._snapshot()
        self._reload_events()
        self.cursorChanged.emit()

    def _play_preview(self, note, velocity):
        if self.libseq.getPlayState(self.zynseq.scene, self.phrase, self.sequence) == zynseq.SEQ_STOPPED:
            self.libseq.playNote(note, velocity, self.channel, int(200 * self.duration))

    @Slot(int, int)
    def toggleNote(self, step, row):
        """Add a note at an empty cell, remove the note covering the cell"""
        note = self._note(row)
        if note is None or not 0 <= step < self.steps:
            return
        self.cursor = [step, row]
        self.cursorChanged.emit()
        self._flush_pending()
        # Chord entry: the chord's notes (on the chord's root note's step)
        notes = [note + i for i in chord_intervals(self.chord_mode, self.chord_type, self.chord_tonic, note)]
        notes = [n for n in notes if 0 <= n <= 127]
        start = self.libseq.getNoteStart(step, note)
        if start >= 0:
            for n in notes:
                s = self.libseq.getNoteStart(start, n)
                if s >= 0:
                    self.libseq.removeNote(s, n)
                    self.libseq.playNote(n, 0, self.channel)   # silence it if sounding
        else:
            for n in notes:
                self.libseq.addNote(step, n, self.velocity, self.duration, self.entry_params["offset"])
                self.libseq.setNoteData(step, n, default_note_evdata(self.duration, self.velocity,
                                                                     **self.entry_params))
                self._play_preview(n, self.velocity)
        self._changed()

    @Slot(int, int)
    def editNote(self, step, row):
        """Note options: velocity, duration, the per-note settings (offset, stutter, play chance...),
        remove"""
        note = self._note(row)
        if note is None:
            return
        start = self.libseq.getNoteStart(step, note)
        if start < 0:
            # Empty cell: the note-entry values
            self.entry_options()
            return
        self.cursor = [start, row]
        self.cursorChanged.emit()
        self._note_options(start, note)

    def _note_options(self, start, note, selected=0):
        ev = self.zynseq.get_note_data(start, note)
        if ev is None:
            return
        vel, dur = ev.val2_start, ev.duration

        def edited(action, index):
            # The change, then the options again (with the new value), to change more
            def run(value):
                self._flush_pending()
                action(value)
                self._changed()
                self._note_options(start, note, index)
            return run

        def set_duration(d):
            # addNote over the note keeps its settings (Pattern::addEvent)
            self.libseq.addNote(start, note, vel, float(d), ev.offset)

        def remove():
            self._flush_pending()
            self.libseq.removeNote(start, note)
            self._changed()

        opts = [
            (f"Velocity ({vel})", lambda: self.ui.edit_value(
                "Velocity", vel, 1, 127, edited(lambda v: self.libseq.setNoteVelocity(start, note, int(v)), 0)),
             None, None),
            (f"Duration ({dur:g} steps)", lambda: self.ui.edit_value(
                "Duration (steps)", float(dur), 0.5, float(self.steps), edited(set_duration, 1), step=0.5, decimals=1),
             None, None),
        ]
        for i, p in enumerate(NOTE_PARAMS):
            value = getattr(ev, p["key"])
            apply = edited(lambda v, p=p: set_note_param(self.libseq, start, note, p, v), 2 + i)
            opts.append((f"{p['name']} ({note_param_text(p, value)})",
                         lambda p=p, value=value, apply=apply: self._edit_param(p, value, apply), None, None))
        opts.append(("Remove", remove, None, None))
        self.ui.show_options(f"Note {note_name(note)} at step {start + 1}", opts, selected)

    def _edit_param(self, param, value, apply):
        """Edit a NOTE_PARAMS value (list of options or value editor); apply(value in stored form)"""
        if param["kind"] == "options":
            self._pick(param["name"], list(zip(param["labels"], range(len(param["labels"])))), value, apply)
        elif param["kind"] == "percent":
            self.ui.edit_value(f"{param['name']} (%)", round(100 * value), param["min"], param["max"],
                               lambda v: apply(int(v) / 100))
        else:
            self.ui.edit_value(param["name"], value, param["min"], param["max"], lambda v: apply(int(v)))

    def entry_options(self, selected=0):
        """The values of new notes"""
        def set_velocity(v):
            self.velocity = int(v)
            self.entryChanged.emit()
            self.entry_options(0)

        def set_duration(d):
            self.duration = float(d)
            self.entryChanged.emit()
            self.entry_options(1)

        def setter(key, index):
            def apply(v):
                self.entry_params[key] = v
                self.entryChanged.emit()
                self.entry_options(index)
            return apply

        def reset():
            self.entry_params = dict(NOTE_PARAM_DEFAULTS)
            self.entryChanged.emit()

        opts = [
            (f"Velocity ({self.velocity})", lambda: self.ui.edit_value("New note velocity", self.velocity, 1, 127,
                                                                       set_velocity), None, None),
            (f"Duration ({self.duration:g} steps)", lambda: self.ui.edit_value(
                "New note duration (steps)", self.duration, 0.5, 64.0, set_duration, step=0.5, decimals=1),
             None, None),
        ]
        for i, p in enumerate(NOTE_PARAMS):
            value = self.entry_params[p["key"]]
            opts.append((f"{p['name']} ({note_param_text(p, value)})",
                         lambda p=p, value=value, i=i: self._edit_param(p, value, setter(p["key"], 2 + i)),
                         None, None))
        if self.entry_params != NOTE_PARAM_DEFAULTS:
            opts.append(("Reset offset, stutter and play settings to defaults", reset, None, None))
        self.ui.show_options("New notes", opts, selected)

    # Block selection, copy / cut / paste (zynthian_gui_pated_base block edit)

    @Property(bool, notify=blockChanged)
    def selectMode(self):
        return self.select_mode

    @Property("QVariantList", notify=blockChanged)
    def block(self):
        return list(self._block) if self._block else []

    @Property(bool, notify=blockChanged)
    def hasCopy(self):
        return self.copied is not None

    @Slot()
    def toggleSelectMode(self):
        """The block edit mode on / off (the Select key)"""
        self.set_edit_mode(EDIT_MODE_NONE if self.edit_mode == EDIT_MODE_BLOCK else EDIT_MODE_BLOCK)

    @Slot(int, int, int, int)
    def selectBlock(self, step1, row1, step2, row2):
        """Select the cells between two corners (any order)"""
        n_rows = len(self.keymap)
        s1, s2 = sorted((max(0, min(self.steps - 1, step1)), max(0, min(self.steps - 1, step2))))
        r1, r2 = sorted((max(0, min(n_rows - 1, row1)), max(0, min(n_rows - 1, row2))))
        self._block = [s1, r1, s2, r2]
        self.blockChanged.emit()

    def _block_notes(self, block):
        notes = [self.keymap[r]["note"] for r in range(block[1], block[3] + 1)]
        return min(notes), max(notes)

    @Slot(bool)
    def copyBlock(self, cut):
        """Copy (or cut) the selected block's notes into the pattern buffer; then taps paste it"""
        if not self._block:
            return
        note1, note2 = self._block_notes(self._block)
        if cut:
            self._flush_pending()
        n = self.libseq.copyPatternBuffer(self.pattern, self._block[0], self._block[2], note1, note2, cut)
        if cut:
            self._changed()
        if n:
            self.copied = list(self._block)
            self._cp_offset = [0, 0]
            self.ui.show_info(f"{'Cut' if cut else 'Copied'} {n} notes: tap where to paste")
        else:
            self.copied = None
            self.ui.show_info("No notes in the selection")
        self.blockChanged.emit()
        self.modeChanged.emit()

    @Slot()
    def deleteBlock(self):
        """Remove the selected block's notes (a cut without keeping the copy)"""
        if self._block:
            note1, note2 = self._block_notes(self._block)
            self._flush_pending()
            self.libseq.copyPatternBuffer(self.pattern, self._block[0], self._block[2], note1, note2, True)
            self._changed()
            self._block = None
            self.blockChanged.emit()

    @Slot(int, int)
    def pasteAt(self, step, row):
        """Paste the copied block with its first step and lowest row at (step, row)"""
        if not self.copied or not 0 <= row < len(self.keymap):
            return
        src_note = self._block_notes(self.copied)[0]
        dnote = self.keymap[row]["note"] - src_note
        dstep = step - self.copied[0]
        self._flush_pending()
        self.libseq.pastePatternBuffer(self.pattern, dstep, 0.0, max(-127, min(127, dnote)), False)
        self._changed()

    # Edit modes and knobs as zynthian_gui_pated_base / _notes

    @Property(int, notify=modeChanged)
    def editMode(self):
        return self.edit_mode

    @Property(str, notify=modeChanged)
    def modeTitle(self):
        """The title of the edit mode (Tk shows it inverted in the top bar), "" without one"""
        m = self.edit_mode
        if m == EDIT_MODE_HISTORY:
            return "Undo/Redo"
        if m == EDIT_MODE_BLOCK:
            return "Paste" if self.copied else "Select Block"
        if m == EDIT_MODE_MULTI:
            return "MULTI Duration " if self.edit_param == 0 else "MULTI Velocity"
        if m == EDIT_MODE_SINGLE:
            return self._edit_title()
        return ""

    @Property(str, notify=patternChanged)
    def tkTitle(self):
        """The title as zynthian_gui_pated_notes.get_title: "<sequence> <chain>: Notes" """
        zs = self.zynseq
        name = zs.get_sequence_name(zs.scene, self.phrase, self.sequence) if self._shown else ""
        if name:
            try:
                chain_name = self.ui.chain_manager.get_synth_chain(self.channel).get_title()
            except Exception:
                chain_name = ""
            title = f"{name} {chain_name or f'MIDI-{self.channel + 1}'}"
        else:
            title = f"Pattern {self.pattern}"
        if self.cc_mode:
            # zynthian_gui_pated_cc.get_title
            title = f"{title}: CC{self.cc_num}"
            zctrl = self.ui.chain_manager.get_zynstep_mapped_zctrl(self.channel, self.cc_num) if self._shown else None
            if zctrl:
                return f"{title} ({zctrl.name})"
            names = {1: "ModWheel", 2: "Breath", 5: "Portamento", 7: "Volume", 8: "Balance", 10: "Pan",
                     11: "Expression", 64: "Sustain Pedal", 66: "Sostenuto Pedal", 67: "Soft Pedal",
                     71: "Resonance", 72: "Release", 73: "Attack", 74: "Cutoff", 91: "Reverb", 92: "Tremolo",
                     93: "Chorus", 94: "Detune"}
            return f"{title} (MIDI {names[self.cc_num]})" if self.cc_num in names else title
        return f"{title}: {'Chords' if self.chord_mode else 'Notes'}"

    def _cursor_note_data(self):
        step, row = self.cursor
        note = self._note(row)
        return step, row, note, (self.zynseq.get_note_data(step, note) if note is not None else None)

    def _param_value(self, ev, index):
        """Edit parameter index of the note (ev) or of the new notes (ev None)"""
        if index == 0:
            return ev.duration if ev else self.duration
        if index == 1:
            return ev.val2_start if ev else self.velocity
        key = NOTE_PARAMS[index - 2]["key"]
        return getattr(ev, key) if ev else self.entry_params[key]

    def _edit_title(self):
        _, _, _, ev = self._cursor_note_data()
        i = self.edit_param
        val = self._param_value(ev, i)
        if i == 0:
            return f"Duration: {val:0.1f} steps"
        if i == 1:
            return f"Velocity: {val}"
        return f"{EDIT_PARAM_TITLES[i]}: {note_param_text(NOTE_PARAMS[i - 2], val)}"

    def set_edit_mode(self, mode):
        """zynthian_gui_pated_base.set_edit_mode: the block mode starts a block at the cursor;
        back to none clears the block and the copy"""
        if self.cc_mode and mode in (EDIT_MODE_SINGLE, EDIT_MODE_MULTI, EDIT_MODE_BLOCK):
            mode = EDIT_MODE_NONE
        self.edit_mode = mode
        self.select_mode = mode == EDIT_MODE_BLOCK
        if mode == EDIT_MODE_BLOCK and not self.copied:
            self.selected_events = None
            self._block_start = list(self.cursor)
            self._block_end = list(self.cursor)
            self._update_block()
            self.eventsChanged.emit()
        elif mode != EDIT_MODE_BLOCK:
            self._block = None
            self.copied = None
            self.blockChanged.emit()
        self.modeChanged.emit()

    def _update_block(self):
        s1, s2 = sorted((self._block_start[0], self._block_end[0]))
        r1, r2 = sorted((self._block_start[1], self._block_end[1]))
        self._block = [s1, r1, s2, r2]
        self.blockChanged.emit()

    def _clamp_cell(self, cell):
        return [max(0, min(self.steps - 1, cell[0])), max(0, min(len(self.keymap) - 1, cell[1]))]

    def select_block(self, dstep, drow):
        """Move the block's end (zynthian_gui_pated_base.select_block)"""
        if self._block_end is None:
            self._block_start = list(self.cursor)
            self._block_end = list(self.cursor)
        self._block_end = self._clamp_cell([self._block_end[0] + dstep, self._block_end[1] + drow])
        self.cursor = list(self._block_end)
        self.cursorChanged.emit()
        self._update_block()

    def select_block_all(self):
        """All notes, the block their rows over the whole pattern (select_block_all)"""
        self.selected_events = self.zynseq.get_pattern_selection(self.pattern, 0, self.steps, 0, 127)
        rows = [r for r in (self._row_of_note(k // zynseq.MAX_STEPS_PATTERN) for k in self.selected_events)
                if r is not None]
        if rows:
            self._block_start = [0, max(rows)]
            self._block_end = [self.steps - 1, min(rows)]
            self._update_block()
        self.eventsChanged.emit()

    def select_block_events(self):
        """The notes in the block (select_block_events)"""
        if not self._block:
            return
        note1, note2 = self._block_notes(self._block)
        self.selected_events = self.zynseq.get_pattern_selection(self.pattern, self._block[0], self._block[2],
                                                                 note1, note2)
        self.eventsChanged.emit()

    def clean_selected_events(self):
        if self.selected_events:
            self.selected_events = None
            self.eventsChanged.emit()

    def _row_of_note(self, note):
        for i, k in enumerate(self.keymap):
            if k["note"] == note:
                return i
        return None

    def move_block(self, dstep, drow):
        """Move the copied block (move_block): rows within the keymap, steps around the pattern"""
        if not self.copied:
            return
        n_rows = len(self.keymap)
        dr = self._cp_offset[1] + drow
        if self.copied[1] + dr < 0 or self.copied[3] + dr >= n_rows:
            return
        ds = (self._cp_offset[0] + dstep) % self.steps
        self._cp_offset = [ds, dr]
        # The (hidden) cursor as Tk: the block's end step moving right, its start moving left;
        # its top row moving up, else the row above its bottom
        step = self.copied[2] + ds if dstep > 0 else self.copied[0] + ds
        row = self.copied[3] + dr if drow > 0 else self.copied[1] + dr + 1
        self.cursor = self._clamp_cell([step % self.steps, row])
        self.cursorChanged.emit()
        self.blockChanged.emit()

    @Property("QVariantList", notify=blockChanged)
    def copyEvents(self):
        """The copied notes at their moved place (Tk draws them green): {step, row, duration,
        velocity}"""
        if not self.copied or not self._shown:
            return []
        out = []
        evdata = zynseq.event_data()
        src_row = self.copied[1]
        dnote = self._paste_dnote()
        i = 0
        while self.libseq.getBufferEventDataAt(i, evdata) >= 0:
            i += 1
            if evdata.command != zynseq.MIDI_NOTE_ON:
                continue
            row = self._row_of_note(evdata.val1_start + dnote)
            if row is None:
                continue
            out.append({"step": (evdata.position + self._cp_offset[0]) % self.steps, "row": row,
                        "duration": evdata.duration, "velocity": evdata.val2_start, "label": "",
                        "muted": False, "stutter": 0, "stutterFx": 0, "stutterMuted": False,
                        "selected": False})
        return out

    def _paste_dnote(self):
        src_row = self.copied[1]
        dst_row = max(0, min(len(self.keymap) - 1, src_row + self._cp_offset[1]))
        return self.keymap[dst_row]["note"] - self.keymap[src_row]["note"]

    def paste_block(self):
        """Paste the moved copy (paste_block); the copy stays for more"""
        if not self.copied:
            return
        self._flush_pending()
        self.libseq.pastePatternBuffer(self.pattern, self._cp_offset[0], 0.0,
                                       max(-127, min(127, self._paste_dnote())), False)
        self._changed()

    @Slot(int)
    def setZoom(self, zoom):
        zoom = max(self._zoom_limits[0], min(self._zoom_limits[1], zoom))
        if zoom != self.zoom:
            self.zoom = zoom
            if self._shown:
                self.libseq.setPatternZoom(zoom)
            self.zoomChanged.emit()

    @Slot(int, int)
    def setZoomLimits(self, lo, hi):
        """The zoom range of the grid shown (QML: from its cell size limits, as Tk's
        calculate_geometry_limits)"""
        self._zoom_limits = (min(lo, 0), max(hi, 0))
        if not lo <= self.zoom <= hi:
            self.setZoom(self.zoom)

    @Property(int, notify=zoomChanged)
    def zoomValue(self):
        return self.zoom

    def reset_grid_zoom(self):
        self.setZoom(0)

    def undo_all(self):
        self._undo_all()

    def redo_all(self):
        if not self._pending and self.libseq.redoPatternAll():
            self._reload_events()

    def _edit_single(self, knob, dval):
        """Single note edit (zynthian_gui_pated_notes.zynpot_cb): knob 1 the duration in 0.1 steps,
        knob 2 the parameter; the note at the cursor or the new notes' values"""
        step, row, note, ev = self._cursor_note_data()
        i = self.edit_param
        if knob == 1:
            if i != 0:
                return
            delta = 0.1 * dval
        else:
            delta = dval
        val = self._param_value(ev, i)
        if i == 0:
            val += delta
            if val > self.steps or val < 0.05:
                return
            if ev:
                self._flush_pending()
                self.libseq.addNote(step, note, ev.val2_start, val, ev.offset)
                self._changed()
            else:
                self.duration = val
                self.entryChanged.emit()
            return
        if i == 1:
            val += int(delta)
            if not 1 <= val <= 127:
                return
            if ev:
                self._flush_pending()
                self.libseq.setNoteVelocity(step, note, val)
                self._changed()
            else:
                self.velocity = val
                self.entryChanged.emit()
            return
        p = NOTE_PARAMS[i - 2]
        if p["kind"] == "percent":
            v = round(100 * val) + int(delta)
            if not p["min"] <= v <= p["max"]:
                return
            val = v / 100
        elif p["kind"] == "options":
            val += int(delta)
            if not 0 <= val < len(p["labels"]):
                return
        else:
            val += int(delta)
            if not p["min"] <= val <= p["max"]:
                return
        if ev:
            self._flush_pending()
            set_note_param(self.libseq, step, note, p, val)
            self._changed()
        else:
            self.entry_params[p["key"]] = val
            self.entryChanged.emit()

    def _edit_multi(self, knob, dval):
        """Multi edit: duration (knob 1: 0.1 steps, knob 2: 1) or velocity of the selected notes"""
        if not self.selected_events:
            return
        n = len(self.selected_events)
        self._flush_pending()
        if self.edit_param == 0:
            self.libseq.changeDurationList((0.1 if knob == 1 else 1) * dval, zynseq.event_key_buffer, n)
        else:
            self.libseq.changeVelocityList(dval, zynseq.event_key_buffer, n)
        self._changed()

    def move_cursor(self, dstep, drow):
        """The cursor (select_cell): within the pattern and keymap, over notes covering steps"""
        step, row = self.cursor
        row = max(0, min(len(self.keymap) - 1, row + drow))
        step = max(0, min(self.steps - 1, step + dstep))
        note = self._note(row)
        if dstep and note is not None:
            # Skip the steps a longer note covers (Tk: hidden, overlapping cells)
            for prev in range(step - 1, -1, -1):
                d = self.libseq.getNoteDuration(prev, note)
                if not d:
                    continue
                d = int(-(-d // 1))
                if d > step - prev:
                    step = prev + d if dstep > 0 else prev
                break
            step = max(0, min(self.steps - 1, step))
        self.cursor = [step, row]
        self.cursorChanged.emit()
        if self.edit_mode == EDIT_MODE_SINGLE:
            self.modeChanged.emit()

    @Slot(int, int)
    def touchBold(self, step, row):
        """A bold press on the grid (zynthian_gui_pated_notes.on_grid_release): the cell's note
        parameters (the selected notes' in an edit mode)"""
        note = self._note(row)
        if note is None:
            return
        start = self.libseq.getNoteStart(step, note)
        self.cursor = [start if start >= 0 else step, row]
        self.cursorChanged.emit()
        self.set_edit_mode(EDIT_MODE_SINGLE if self.edit_mode == EDIT_MODE_NONE else EDIT_MODE_MULTI)

    # Touch: hold a note, then drag (zynthian_gui_pated_notes.on_grid_drag with drag_note): up /
    # down its velocity, sideways its duration; an empty cell: the cursor follows, the note is
    # added on release

    @Slot(int, int, result="QVariantList")
    def noteAt(self, step, row):
        """[start step, velocity, duration] of the note covering the cell, [] if none"""
        note = self._note(row)
        if note is None:
            return []
        start = self.libseq.getNoteStart(step, note)
        if start < 0:
            return []
        return [start, self.libseq.getNoteVelocity(start, note), self.libseq.getNoteDuration(start, note)]

    @Slot(int, int, int)
    def dragVelocity(self, step, row, velocity):
        note = self._note(row)
        if note is not None and 1 <= velocity <= 127 and self.libseq.getNoteVelocity(step, note) != velocity:
            self._flush_pending() if not self._pending else None
            self.libseq.setNoteVelocity(step, note, velocity)
            self._pending = True
            self._reload_events()
            self.cursorChanged.emit()

    @Slot(int, int, int)
    def dragDuration(self, step, row, duration):
        note = self._note(row)
        if note is None or duration <= 0:
            return
        if self.libseq.getNoteDuration(step, note) != duration:
            vel = self.libseq.getNoteVelocity(step, note)
            self._flush_pending() if not self._pending else None
            self.libseq.addNote(step, note, vel, float(duration), 0.0)
            self._pending = True
            self._reload_events()
            self.cursorChanged.emit()

    @Slot(int, int)
    def setCursor(self, step, row):
        if 0 <= step < self.steps and 0 <= row < len(self.keymap):
            if [step, row] != self.cursor:
                self.cursor = [step, row]
                self.cursorChanged.emit()
                if self.edit_mode == EDIT_MODE_SINGLE:
                    self.modeChanged.emit()

    @Slot(int)
    def setRefNote(self, row):
        """The bottom row shown (the grid scrolled): libseq keeps it per pattern (Tk's
        set_keymap_offset)"""
        if self._shown and row >= 0:
            self.libseq.setRefNote(int(row))

    @Slot()
    def editDone(self):
        """End of a drag: one undo step"""
        self._flush_pending()

    @Slot(int)
    def playRow(self, row):
        """Piano key tapped: play its note (on_pianoroll_release_action)"""
        note = self._note(row)
        if note is not None:
            self.libseq.playNote(note, self.velocity, self.channel, 200)

    @Property(int, notify=cursorChanged)
    def cursorVelocity(self):
        """The velocity under the cursor (the note's, else the new notes'): Tk's velocity bar"""
        if not self._shown:
            return self.velocity
        _, _, _, ev = self._cursor_note_data()
        return ev.val2_start if ev else self.velocity

    @Property(float, notify=cursorChanged)
    def cursorDuration(self):
        if not self._shown:
            return 1.0
        _, _, _, ev = self._cursor_note_data()
        return ev.duration if ev else 1.0

    @Property(int, notify=patternChanged)
    def refRow(self):
        """The bottom row to show after loading the pattern (Tk's keymap_offset from RefNote)"""
        return getattr(self, "ref_row", 0)

    @Property(int, notify=patternChanged)
    def tonic(self):
        return self.libseq.getTonic() if self._shown else 0

    @Slot()
    def entryOptions(self):
        self.entry_options()

    @Slot()
    def undo(self):
        self._flush_pending()
        if self.libseq.undoPattern():
            self._reload_events()

    @Slot()
    def redo(self):
        if not self._pending and self.libseq.redoPattern():
            self._reload_events()

    @Slot()
    def togglePlayback(self):
        zs = self.zynseq
        if self.libseq.getPlayState(zs.scene, self.phrase, self.sequence) == zynseq.SEQ_STOPPED:
            # From the start of the pattern (work around for a timebase issue in the library)
            self.libseq.setSequencePlayPosition(zs.scene, self.phrase, self.sequence, 0)
            self.libseq.setPlayState(zs.scene, self.phrase, self.sequence, zynseq.SEQ_STARTING)
        else:
            self.libseq.setPlayState(zs.scene, self.phrase, self.sequence, zynseq.SEQ_STOPPED)

    # Menu: "Pattern options" as zynthian_gui_pated_base / _notes / _cc get_menu_options (titles,
    # order, sections). Tk edits the values in the title bar with the knobs; here the value
    # editor or a list. Kept from the Qt editor (Tk lacks them): "Record MIDI", "New note values",
    # "Undo all".

    def _seq_info(self):
        zs = self.zynseq
        try:
            return zs.state["scenes"][zs.scene]["phrases"][self.phrase]["sequences"][self.sequence]
        except Exception:
            return {}

    def _pattern_length_text(self, beats=None, bpb=4):
        """zynthian_gui_pated_base.get_pattern_length (bars and beats of 4 beats per bar)"""
        if beats is None:
            beats = self.libseq.getBeatsInPattern(self.pattern)
        bars = beats // bpb if bpb > 1 else 0
        extra = beats % bpb
        beats_text = "" if extra == 0 else ("1 beat" if extra == 1 else f"{extra} beats")
        bars_text = "" if bars == 0 else ("1 bar" if bars == 1 else f"{bars} bars")
        return f"{bars_text} + {beats_text}" if bars and extra else bars_text + beats_text

    @Slot()
    def menu(self):
        ls = self.libseq
        zs = self.zynseq
        info = self._seq_info()
        opts = []

        def head(t):
            opts.append((f"> {t}", None, None, None))

        def add(label, action):
            opts.append((label, action, None, None))

        # _SEQUENCE (no heading)
        if info:
            name = info.get("name") or ""
            add(f"Rename ({name})" if name else "Rename", self._rename_sequence)
            repeat = info.get("repeat", 0)
            mode = ("LOOP" if repeat == 255 else "ONESHOT" if repeat == 1 else f"PLAY {repeat} TIMES") \
                if repeat > 0 else "DISABLED"
            add(f"Play mode ({mode})", self._pick_playmode)
            pc = ls.getProgramChange(0)
            add(f"Program Change ({pc if pc <= 127 else 'None'})", self._pick_program_change)
        # _PATTERN (no heading)
        add("Edit Notes" if self.cc_mode else "Edit CC", self.toggleCcMode)
        add(f"Length ({self._pattern_length_text()})", self._pick_length)
        add(f"Steps/Beat ({ls.getStepsPerBeat()})", self._pick_steps_per_beat)
        qn = ls.getQuantizeNotes()
        qval = "DISABLED" if qn <= 0 else ("1 step" if qn == 1 else f"1/{qn} step")
        add(f"Quantization ({qval})", self._pick_quantization)
        add(f"Swing Amount ({int(100.0 * ls.getSwingAmount())}%)", lambda: self.ui.edit_value(
            "Swing Amount", int(100.0 * ls.getSwingAmount()), 0, 100, lambda v: ls.setSwingAmount(v / 100.0)))
        add(f"Swing Divisor ({ls.getSwingDiv()})", lambda: self.ui.edit_value(
            "Swing Divisor", ls.getSwingDiv(), 1, max(1, ls.getStepsPerBeat()), lambda v: ls.setSwingDiv(int(v))))
        add(f"Time Humanization ({int(100.0 * ls.getHumanTime())})", lambda: self.ui.edit_value(
            "Time Humanization", int(100.0 * ls.getHumanTime()), 0, 100, lambda v: ls.setHumanTime(v / 100.0)))
        if self.cc_mode:
            interp = bool(ls.getInterpolateCC(self.cc_num))
            add(("\u2612" if interp else "\u2610") + f" Interpolate CC{self.cc_num} values",
                lambda: (ls.setInterpolateCC(self.cc_num, not interp), self.ccChanged.emit()))
            add(f"CC number ({self.cc_num})", self.pickCc)
        else:
            add(f"Velocity Humanization ({int(ls.getHumanVelo())})", lambda: self.ui.edit_value(
                "Velocity Humanization", int(ls.getHumanVelo()), 0, 100, lambda v: ls.setHumanVelo(float(v))))
            add(f"Note Play Chance ({round(100 * ls.getPlayChance())}%)", lambda: self.ui.edit_value(
                "Note Play Chance", round(100 * ls.getPlayChance()), 0, 100, lambda v: ls.setPlayChance(v / 100)))
            scales = scale_names(self.ui.chain_manager, self.channel)
            scale = ls.getScale()
            add(f"Scale ({scales[scale] if scale < len(scales) else scale})", lambda: self._pick(
                "Scale", list(zip(scales, range(len(scales)))), scale, self._set_scale))
            add(f"Tonic ({NOTE_NAMES[ls.getTonic() % 12]})", lambda: self._pick(
                "Tonic", list(zip(NOTE_NAMES, range(12))), ls.getTonic(), self._set_tonic))
        # EDIT
        head("EDIT")
        if not self.cc_mode:
            rest = ls.getInputRest()
            add(f"Rest-step note ({NOTE_NAMES[rest % 12]}{rest // 12 - 1})" if rest < 128 else "Rest note (None)",
                self._pick_rest)
            add(f"Chord mode ({CHORD_MODES[self.chord_mode]})", self._pick_chord_mode)
            if self.chord_mode == 1:
                add(f"Chord type ({CHORDS[self.chord_type][0]})", lambda: self._pick(
                    "Chord type", [(c[0], i) for i, c in enumerate(CHORDS)], self.chord_type, self._set_chord_type))
            elif self.chord_mode >= 2:
                add(f"Diatonic key ({NOTE_NAMES[self.chord_tonic]})", lambda: self._pick(
                    "Diatonic key", list(zip(NOTE_NAMES, range(12))), self.chord_tonic, self._set_chord_tonic))
            add("Transpose pattern", lambda: self._pick(
                "Transpose", [("down", -1), ("up", 1)], 0, self._transpose))
        add("Grid zoom", lambda: self.ui.edit_value("Zoom", self.zoom, self._zoom_limits[0], self._zoom_limits[1],
                                                   lambda v: self.setZoom(int(v))))
        if info:
            name = zs.get_sequence_name(zs.scene, self.phrase, self.sequence)
            add(f"Copy this ({name}) to clipboard #1", lambda: self.cuia_copy([0]))
            add(f"Copy this ({name}) to clipboard #2", lambda: self.cuia_copy([1]))
            for i, src in enumerate(self.clipboard):
                if src is not None and src[2] != self.pattern:
                    sname = zs.get_sequence_name(zs.scene, src[0], src[1])
                    add(f"Paste {sname} from clipboard #{i + 1}", lambda i=i: self.cuia_paste([i]))
        add("Clear pattern ALL", lambda: self.ui.confirm(f"Clear pattern {self.pattern}?", self._clear))
        if self.cc_mode:
            add(f"Clear pattern CC{self.cc_num}", lambda: self.ui.confirm(
                f"Clear CC{self.cc_num} in pattern {self.pattern}?", self._clear_cc))
        else:
            add("Clear pattern notes", lambda: self.ui.confirm(
                f"Clear notes in pattern {self.pattern}?", self._clear_notes))
            add("Load pattern", self._load_pattern_file)
            add("Save pattern", lambda: self._ask_file_name(PATTERNS_DIR, "zpat", self._save_pattern_file))
            add("Import from SMF", self._import_smf)
            add("Export to SMF", lambda: self._ask_file_name(SMF_EXPORT_DIR, "mid", self._export_smf))
        # Qt only, after Tk's entries (Tk's list positions stay)
        add(("\u2612" if ls.isMidiRecord() else "\u2610") + " Record MIDI", self.toggleRecording)
        add("New note values", self.entry_options)
        add("Undo all", self._undo_all)
        title = "Pattern options" + (f": {info['name']}" if info.get("name") else "")
        self.ui.show_options(title, opts)

    def _set_chord_type(self, t):
        self.chord_type = t
        self.entryChanged.emit()

    def _set_chord_tonic(self, t):
        self.chord_tonic = t
        self.entryChanged.emit()

    def _rename_sequence(self):
        zs = self.zynseq

        def named(name):
            zs.set_sequence_param(zs.scene, self.phrase, self.sequence, "name", name[:8])
            self.patternChanged.emit()
        self.ui.show_keyboard(named, zs.get_sequence_name(zs.scene, self.phrase, self.sequence), "Rename")

    def _pick_playmode(self):
        zs = self.zynseq
        labels = ["DISABLED", "LOOP", "ONESHOT"] + [f"PLAY {i} TIMES" for i in range(2, 25)]
        repeat = self._seq_info().get("repeat", 0)
        value = 0 if repeat == 0 else (1 if repeat == 255 else 1 + repeat)

        def apply(v):
            zs.set_sequence_param(zs.scene, self.phrase, self.sequence, "repeat",
                                  0 if v == 0 else (255 if v == 1 else v - 1))
        self._pick("Playmode", list(zip(labels, range(len(labels)))), value, apply)

    def _pick_program_change(self):
        ls = self.libseq
        program = ls.getProgramChange(0) + 1
        if program > 128:
            program = 0

        def apply(v):
            v -= 1
            if v < 0 or v > 127:
                ls.removeProgramChange(0)
            else:
                ls.addProgramChange(0, v)
        self._pick("Program", [("None", 0)] + [(str(i), i + 1) for i in range(128)], program, apply)

    def _pick_quantization(self):
        divs = [0, 1, 2, 3, 4, 6, 8]
        labels = ["DISABLED", "1 step", "1/2 step", "1/3 step", "1/4 step", "1/6 step", "1/8 step"]
        self._pick("Quantization Divisor", list(zip(labels, divs)), self.libseq.getQuantizeNotes(),
                   self.libseq.setQuantizeNotes)

    def _clear_notes(self):
        self._flush_pending()
        self.libseq.clearNotes()
        self._changed()

    @staticmethod
    def _rest_name(note):
        return note_name(note) if note < 128 else "None"

    def _pick_rest(self):
        """The note that enters a rest step when recording from MIDI (zynthian_gui_pated_notes)"""
        choices = [("None", 128)] + [(note_name(n), n) for n in range(128)]
        self._pick("Rest-step note", choices, self.libseq.getInputRest(), self.libseq.setInputRest)

    # Files (zynthian_gui_pated_base): patterns (.zpat) and Standard MIDI Files

    def _ask_file_name(self, dirpath, ext, action):
        """Name a file in dirpath; action(path), after asking before overwriting"""
        def named(name):
            name = name.strip()
            if not name:
                return
            path = f"{dirpath}/{name}.{ext}"
            if os.path.exists(path):
                self.ui.confirm(f"Overwrite '{name}'?", lambda: action(path))
            else:
                action(path)
        self.ui.show_keyboard(named, f"pattern_{self.pattern}", "File name")

    def _save_pattern_file(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if self.zynseq.save_pattern(self.pattern, path):
            self.ui.show_info(f"Saved {os.path.basename(path)}")
        else:
            self.ui.show_info(f"Can't save {os.path.basename(path)}")

    def _load_pattern_file(self):
        def load(path):
            self.zynseq.load_pattern(self.pattern, path)
            # As zynthian_gui_pated_base: needed when the steps/beat changed; no undo past loading
            self.libseq.setBeatsInPattern(self.pattern, self.libseq.getBeatsInPattern(self.pattern))
            self.libseq.resetPatternSnapshots()
            self.load()

        def chosen(path):
            if self.zynseq.is_pattern_empty(self.pattern):
                load(path)
            else:
                self.ui.confirm(f"Replace pattern {self.pattern} with {os.path.basename(path)}?", lambda: load(path))
        FilePicker(self.ui).pick("Load pattern", ["zpat"], chosen)

    def _import_smf(self):
        FilePicker(self.ui).pick("Import MIDI file", ["mid"], self._import_smf_file,
                                 self.last_smf_import.get(self.pattern))

    def _import_smf_file(self, path):
        info = analyze_smf(path, self.bpb)
        if not info or not info[0]:
            self.ui.show_info(f"No notes in {os.path.basename(path)}")
            return
        channels, n_bars = info
        if len(channels) == 1:
            self._do_import_smf(path, channels[0][0], n_bars)
        else:
            self.ui.show_options("MIDI file channel", [
                (label, lambda chan=chan: self._do_import_smf(path, chan, n_bars), None, None)
                for chan, label in channels])

    def _do_import_smf(self, path, chan, n_bars):
        """Notes and CCs of a channel of the file; the pattern's length from the file (up to 16
        bars, as Tk)"""
        self.last_smf_import[self.pattern] = path
        beats = min(n_bars, 16) * self.bpb
        if beats != self.libseq.getBeatsInPattern(self.pattern):
            # No undo past a length change (zynthian_gui_pated_base)
            self.libseq.setBeatsInPattern(self.pattern, beats)
            self.libseq.resetPatternSnapshots()
        else:
            self._flush_pending()
        n = import_smf(self.libseq, path, chan, self.bpb)
        self._snapshot()
        self.load()
        self.ui.show_info(f"Imported {n} note{'' if n == 1 else 's'}" if n is not None else f"Can't read {os.path.basename(path)}")

    def _export_smf(self, path):
        if export_smf(self.libseq, path, self.channel):
            self.ui.show_info(f"Exported {os.path.basename(path)}")
        else:
            self.ui.show_info(f"Can't write {os.path.basename(path)}")

    def _pick_chord_mode(self):
        def apply_mode(mode):
            self.chord_mode = mode
            self.entryChanged.emit()
            if mode == 1:
                self._pick("Chord type", [(c[0], i) for i, c in enumerate(CHORDS)], self.chord_type, apply_type)
            elif mode >= 2:
                self._pick("Diatonic key", list(zip(NOTE_NAMES, range(12))), self.chord_tonic, apply_tonic)

        def apply_type(t):
            self.chord_type = t
            self.entryChanged.emit()

        def apply_tonic(t):
            self.chord_tonic = t
            self.entryChanged.emit()

        self._pick("Chord mode", list(zip(CHORD_MODES, range(len(CHORD_MODES)))), self.chord_mode, apply_mode)

    def _clear_cc(self):
        self._flush_pending()
        self.libseq.clearControl(self.cc_num)
        self._snapshot()
        self.libseq.isPatternModified()
        self.ccChanged.emit()

    show_menu = menu   # CUIA MENU (ZynUI.cuia_menu)

    def _pick(self, title, choices, current, apply):
        selected = next((i for i, (_, v) in enumerate(choices) if v == current), 0)
        self.ui.show_options(title, [(label, lambda v=value: apply(v), None, None) for label, value in choices],
                             selected)

    def _pick_length(self):
        def apply(beats):
            def do():
                self.libseq.setBeatsInPattern(self.pattern, beats)
                self.libseq.resetPatternSnapshots()
                self.load()
            if self.libseq.getLastStep() >= self.libseq.getStepsPerBeat() * beats:
                self.ui.confirm("Reducing beats in pattern will truncate pattern", do)
            else:
                do()
        self._pick("Length (beats)", [(str(b), b) for b in range(1, 65)],
                   self.libseq.getBeatsInPattern(self.pattern), apply)

    def _pick_steps_per_beat(self):
        def apply(spb):
            def do():
                self.libseq.setStepsPerBeat(spb)
                self.libseq.resetPatternSnapshots()
                self.load()
            self.ui.confirm("Changing steps per beat may alter timing and/or lose notes?", do)
        self._pick("Steps per beat", [(str(s), s) for s in STEPS_PER_BEAT], self.libseq.getStepsPerBeat(), apply)

    def _set_scale(self, scale):
        self.libseq.setScale(scale)
        self.load()

    def _set_tonic(self, tonic):
        self.libseq.setTonic(tonic)
        self.load()

    def _transpose(self, offset):
        self._flush_pending()
        if self.libseq.getScale():
            # Transposing works on the chromatic scale (as Tk)
            self.libseq.setScale(0)
            self.load()
        self.libseq.transpose(offset)
        self._changed()

    def _undo_all(self):
        self._flush_pending()
        if self.libseq.undoPatternAll():
            self._reload_events()

    def _clear(self):
        self._flush_pending()
        self.libseq.clearPattern(self.pattern)
        self._changed()
        if self.libseq.getPlayState(self.zynseq.scene, self.phrase, self.sequence) != zynseq.SEQ_STOPPED:
            self.libseq.sendMidiCommand(0xB0 | self.channel, 123, 0)   # all notes off

    def update_wsleds(self, leds):
        """The keypad LEDs (zynthian_gui_pated_base.update_wsleds): ALT: F1 / F2 the clipboard, F3
        the block selection, F4 the CC editor; REC, STOP, PLAY for the pattern; the arrows while
        they undo / redo"""
        wsl = self.ui.keypad_leds
        if self.ui.alt_mode:
            for n, i in enumerate((10, 11)):
                if self.clipboard[n] is None:
                    wsl.set_led(leds[i], wsl.wscolor_active2)
                elif self.clipboard[n][2] == self.pattern:
                    wsl.blink(leds[i], wsl.wscolor_red)
                else:
                    wsl.blink(leds[i], wsl.wscolor_active)
            if self.edit_mode == EDIT_MODE_BLOCK:
                wsl.blink(leds[12], wsl.wscolor_active if self.copied else wsl.wscolor_active2)
            else:
                wsl.set_led(leds[12], wsl.wscolor_active2)
            wsl.set_led(leds[13], wsl.wscolor_active2)
        if self.libseq.isMidiRecord():
            wsl.set_led(leds[1], wsl.wscolor_red)
            wsl.set_led(leds[8], wsl.wscolor_active2)
        else:
            wsl.set_led(leds[1], wsl.wscolor_active2)
        wsl.set_led(leds[2], wsl.wscolor_active2)
        state = self.libseq.getPlayState(self.zynseq.scene, self.phrase, self.sequence)
        if state == zynseq.SEQ_PLAYING:
            wsl.set_led(leds[3], wsl.wscolor_green)
        elif state == zynseq.SEQ_STARTING:
            wsl.set_led(leds[3], wsl.wscolor_yellow)
        elif state in (zynseq.SEQ_STOPPING, zynseq.SEQ_STOPPING_SYNC):
            wsl.set_led(leds[3], wsl.wscolor_red)
        else:
            wsl.set_led(leds[3], wsl.wscolor_active2)
        if self._history_keys():
            for i in (4, 5, 6, 7):
                wsl.set_led(leds[i], wsl.wscolor_active2)

    # Keys, knobs and switches (zynthian_gui_pated_base / _notes, with the edit modes)

    def _ctrl(self, n):
        """The knob of controller slot n (layout ctrl_order)"""
        from zyngui import zynthian_gui_config
        order = zynthian_gui_config.layout.get("ctrl_order", (0, 1, 2, 3))
        return order[n] if n < len(order) else n

    def _history_keys(self):
        return (self.ui.alt_mode and self.edit_mode == EDIT_MODE_NONE) or self.edit_mode == EDIT_MODE_HISTORY

    def navigate(self, what):
        if self.cc_mode:
            self._cc_navigate(what)
            return
        if what in ("left", "right"):
            if self._history_keys():
                self.redo() if what == "right" else self.undo()
            else:
                self.zynpot(self._ctrl(3), 1 if what == "right" else -1)
        elif what in ("up", "down"):
            up = what == "up"
            if self._history_keys():
                self.redo_all() if up else self.undo_all()
            elif self.edit_mode in (EDIT_MODE_SINGLE, EDIT_MODE_MULTI):
                self.zynpot(self._ctrl(2), 1 if up else -1)
            else:
                self.zynpot(self._ctrl(2), -1 if up else 1)
                if self.edit_mode == EDIT_MODE_NONE:
                    note = self._note(self.cursor[1])
                    if note is not None:
                        self._play_preview(note, self.velocity)
        elif what == "select":
            self.switch_select("S")
        elif what == "select_bold":
            self.switch_select("B")

    def back(self):
        """BACK (zynthian_gui_pated_base.back_action): clears the selected notes, leaves the edit
        mode; else the screen goes back"""
        if self.edit_mode == EDIT_MODE_NONE:
            if self.selected_events:
                self.clean_selected_events()
                return True
            self.libseq.updateSequenceInfo()
            return False
        self.selected_events = None if self.edit_mode == EDIT_MODE_BLOCK else self.selected_events
        self.set_edit_mode(EDIT_MODE_NONE)
        self.eventsChanged.emit()
        return True

    def zynpot(self, i, d):
        """Knob 1 zoom (or the duration while editing), 2 the row (block, parameter value), 3 the
        step (block, edit parameter, undo / redo)"""
        if self.cc_mode:
            return self._cc_zynpot(i, d)
        m = self.edit_mode
        if i == self._ctrl(1):
            if m == EDIT_MODE_SINGLE:
                self._edit_single(1, d)
                self.modeChanged.emit()
                return True
            if m == EDIT_MODE_MULTI and self.edit_param == 0:
                self._edit_multi(1, d)
                return True
            self.setZoom(self.zoom + d)
            return True
        if i == self._ctrl(2):
            if m == EDIT_MODE_SINGLE:
                self._edit_single(2, d)
                self.modeChanged.emit()
            elif m == EDIT_MODE_MULTI:
                self._edit_multi(2, d)
            elif m == EDIT_MODE_BLOCK:
                self.move_block(0, -d) if self.copied else self.select_block(0, -d)
            elif m == EDIT_MODE_NONE:
                self.move_cursor(0, -d)
            return True
        if i == self._ctrl(3):
            if m == EDIT_MODE_HISTORY:
                self.redo() if d > 0 else self.undo()
            elif m == EDIT_MODE_BLOCK:
                self.move_block(d, 0) if self.copied else self.select_block(d, 0)
            elif m in (EDIT_MODE_SINGLE, EDIT_MODE_MULTI):
                last = len(EDIT_PARAM_TITLES) - 1 if m == EDIT_MODE_SINGLE else EDIT_PARAM_LAST_MULTI
                self.edit_param = max(0, min(last, self.edit_param + d))
                self.modeChanged.emit()
            elif m == EDIT_MODE_NONE:
                self.move_cursor(d, 0)
            return True
        return True

    def switch_select(self, t="S"):
        """SELECT (zynthian_gui_pated_base.switch_select): short toggles the note / copies, pastes
        the block / ends the edit mode; bold the note's parameters (the selected notes')"""
        if self.cc_mode:
            # The CC editor has no block / note edit modes (zynthian_gui_pated_cc.set_edit_mode)
            if t == "S":
                self._cc_navigate("select")
            return True
        m = self.edit_mode
        if t == "S":
            if m == EDIT_MODE_NONE:
                self.toggleNote(*self.cursor)
            elif m == EDIT_MODE_BLOCK:
                if not self.copied:
                    self.copyBlock(False)
                    if not self.copied:
                        self.set_edit_mode(EDIT_MODE_NONE)
                else:
                    self.paste_block()
            else:
                self.set_edit_mode(EDIT_MODE_NONE)
        elif t == "B":
            if m == EDIT_MODE_NONE:
                self.set_edit_mode(EDIT_MODE_MULTI if self.selected_events else EDIT_MODE_SINGLE)
            elif m == EDIT_MODE_BLOCK:
                if not self.copied:
                    self.select_block_events()
                if self.selected_events:
                    self._block = None
                    self.copied = None
                    self.blockChanged.emit()
                    self.set_edit_mode(EDIT_MODE_MULTI)
                else:
                    self.set_edit_mode(EDIT_MODE_NONE)
        return True

    def switch(self, i, t):
        """Switch 0 short the menu, 1 bold undo / redo mode, 2 short play, 2 bold record; ALT:
        F1 / F2 paste / copy the pattern (bold copy), F3 the block selection, F4 CC / notes"""
        if i == 0 and t == "S":
            self.menu()
            return True
        if i == 1 and t == "B":
            self.set_edit_mode(EDIT_MODE_HISTORY)
            return True
        if i == 2:
            if t == "S":
                self.cuia_toggle_play()
                return True
            if t == "B":
                self.cuia_toggle_record()
                return True
        if self.ui.alt_mode and t in ("S", "B"):
            # V5 / touch keypad wiring: F3 = switch 19, F4 = 23, F1 / F2 = 11 / 15 (clipboard)
            if i == 23:
                return self.cuia_v5_zynpot_switch([0, t])
            if i == 19:
                return self.cuia_v5_zynpot_switch([2, t])
            if i in (11, 15):
                n = (11, 15).index(i)
                self.cuia_paste([n]) if t == "S" else self.cuia_copy([n])
                return True
        return False

    def cuia_v5_zynpot_switch(self, params):
        """Knob pushes: 0 the CC / note editor, 1 short reset the zoom, bold the length; 2 short
        the block selection (in it: cut), bold all notes"""
        try:
            i, t = int(params[0]), str(params[1]).upper()
        except (TypeError, ValueError, IndexError):
            return False
        if i == 0 and t == "S":
            self.toggleCcMode()
            return True
        if i == 0 and t == "B" and self.cc_mode:
            self.cc_show_all = not self.cc_show_all
            self.nudge_cc_num()
            return True
        if i == 1:
            if t == "S":
                self.reset_grid_zoom()
                return True
            if t == "B":
                self._pick_length()
                return True
        if i == 2:
            if t == "S":
                if self.edit_mode == EDIT_MODE_NONE:
                    self.set_edit_mode(EDIT_MODE_BLOCK)
                elif self.edit_mode == EDIT_MODE_BLOCK and not self.copied:
                    self.copyBlock(True)
                return True
            if t == "B":
                if self.edit_mode == EDIT_MODE_NONE:
                    self.set_edit_mode(EDIT_MODE_BLOCK)
                self.select_block_all()
                return True
        return False
