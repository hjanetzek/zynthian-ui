"""Pattern editor, notes (zynthian_gui_pated_notes): the selected launcher pad's pattern as a grid,
steps across, the keymap's notes (chromatic, a scale, or the synth's drum map) up the side.

Tap an empty cell to add a note (velocity and duration of the note-entry values), tap a note to
remove it, long press a note for its velocity and duration. Arrows move the cursor, SEL toggles
the note at the cursor. The keymap, events and new note defaults are shared with the Tk editor
(zyngui.zynthian_pated_data)."""

from PySide6.QtCore import QObject, QTimer, Property, Signal, Slot

from zyngui.zynthian_pated_data import (CHORD_MODES, CHORDS, NOTE_NAMES, STEPS_PER_BEAT, chord_intervals,
                                        default_note_evdata, load_keymap, note_events, note_name, scale_names)
from zynlibs.zynseq import zynseq


class PatternEditor(QObject):
    name = "pattern_editor"

    patternChanged = Signal()       # pattern, length, keymap: the whole grid
    eventsChanged = Signal()
    playheadChanged = Signal()
    cursorChanged = Signal()
    entryChanged = Signal()         # note-entry values (velocity, duration)
    ccChanged = Signal()            # CC view: mode, CC number, values
    blockChanged = Signal()         # select mode, selected block, copied buffer

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
        self.chord_mode = 0         # CHORD_MODES index
        self.chord_type = 0         # CHORDS index (chord mode 1)
        self.chord_tonic = 0        # key of the diatonic chords
        self.cc_mode = False        # CC view instead of the notes
        self.cc_num = 64
        self.cc_cursor = 0          # step
        self.select_mode = False    # touch selects a block instead of adding notes
        self._block = None           # selected block: [step1, row1, step2, row2] (inclusive)
        self.copied = None          # copied block (its [step1, row1, step2, row2]); taps paste it
        self._timer = QTimer(self, interval=40)
        self._timer.timeout.connect(self._poll)

    # Screen (ZynUI): shown / hidden

    def build(self):
        self.load()
        self._timer.start()

    def hide(self):
        self._timer.stop()

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
        row_of = {k["note"]: i for i, k in enumerate(self.keymap)}
        notes = sorted((step, note) for step, note, *_ in self._events if note in row_of)
        if notes:
            # Start at the first note, so the pattern's notes are in view
            self.cursor = [notes[0][0], row_of[notes[0][1]]]
        else:
            if self.cursor[0] >= self.steps:
                self.cursor[0] = 0
            if not 0 <= self.cursor[1] < len(self.keymap):
                self.cursor[1] = row_of.get(60, len(self.keymap) // 2)
        self.libseq.isPatternModified()   # reset the flag
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
            # Changed elsewhere (MIDI recording, the other UI, undo)
            self._events = note_events(self.libseq)
            self.eventsChanged.emit()
            self.ccChanged.emit()

    # For QML

    @Property(int, notify=patternChanged)
    def steps(self):
        return self.libseq.getSteps()

    @Property(int, notify=patternChanged)
    def stepsPerBeat(self):
        return self.libseq.getStepsPerBeat()

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
        """Notes: {step, row, duration, velocity}; notes outside the keymap are left out"""
        row_of = {k["note"]: i for i, k in enumerate(self.keymap)}
        return [{"step": step, "row": row_of[note], "duration": dur, "velocity": vel}
                for step, note, dur, vel, _ in self._events if note in row_of]

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
        return f"Vel {self.velocity}  Dur {self.duration:g}{chord}"

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
        return bool(self.libseq.getInterpolateCC(self.cc_num))

    @Property("QVariantList", notify=ccChanged)
    def ccValues(self):
        """Per step: [value, end value, duration] or None"""
        values = []
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
        self.ccChanged.emit()

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
        self.libseq.isPatternModified()
        self.ccChanged.emit()

    @Slot()
    def ccEditDone(self):
        """End of a paint gesture: one undo step"""
        self.libseq.savePatternSnapshot()

    @Slot(int)
    def removeCc(self, step):
        if 0 <= step < self.steps and self.libseq.getControlValue(step, self.cc_num) <= 127:
            self.libseq.savePatternSnapshot()
            self.libseq.removeControl(step, self.cc_num)
            self.libseq.savePatternSnapshot()
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
            self.ccChanged.emit()

        self._pick("CC number", [(label(n), n) for n in range(1, 128)], self.cc_num, apply)

    def _cc_navigate(self, what):
        step = self.cc_cursor
        if what in ("left", "right"):
            self.cc_cursor = max(0, min(self.steps - 1, step + (1 if what == "right" else -1)))
            self.ccChanged.emit()
        elif what in ("up", "down"):
            v = self.libseq.getControlValue(step, self.cc_num)
            v = 64 if v > 127 else v + (1 if what == "up" else -1)
            self.setCc(step, v)
            self.ccEditDone()
        elif what == "select":
            if self.libseq.getControlValue(step, self.cc_num) <= 127:
                self.removeCc(step)
            else:
                self.setCc(step, 64)
                self.ccEditDone()

    # Editing (undo snapshots around each change, as the Tk editor)

    def _note(self, row):
        return self.keymap[row]["note"] if 0 <= row < len(self.keymap) else None

    def _changed(self):
        self.libseq.savePatternSnapshot()
        self._events = note_events(self.libseq)
        self.libseq.isPatternModified()
        self.eventsChanged.emit()
        self.ccChanged.emit()

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
        self.libseq.savePatternSnapshot()
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
                self.libseq.addNote(step, n, self.velocity, self.duration, 0.0)
                self.libseq.setNoteData(step, n, default_note_evdata(self.duration, self.velocity))
                self._play_preview(n, self.velocity)
        self._changed()

    @Slot(int, int)
    def editNote(self, step, row):
        """Note options: velocity, duration, remove"""
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
        vel = self.libseq.getNoteVelocity(start, note)
        dur = self.libseq.getNoteDuration(start, note)

        def set_velocity(v):
            self.libseq.savePatternSnapshot()
            self.libseq.setNoteVelocity(start, note, int(v))
            self._changed()

        def set_duration(d):
            self.libseq.savePatternSnapshot()
            self.libseq.removeNote(start, note)
            self.libseq.addNote(start, note, vel, float(d), 0.0)
            self._changed()

        def remove():
            self.libseq.savePatternSnapshot()
            self.libseq.removeNote(start, note)
            self._changed()

        self.ui.show_options(f"Note {note_name(note)} at step {start + 1}", [
            (f"Velocity ({vel})", lambda: self.ui.edit_value("Velocity", vel, 1, 127, set_velocity), None, None),
            (f"Duration ({dur:g} steps)", lambda: self.ui.edit_value("Duration (steps)", float(dur), 0.5,
                                                                     float(self.steps), set_duration, step=0.5,
                                                                     decimals=1), None, None),
            ("Remove", remove, None, None),
        ])

    def entry_options(self):
        def set_velocity(v):
            self.velocity = int(v)
            self.entryChanged.emit()

        def set_duration(d):
            self.duration = float(d)
            self.entryChanged.emit()

        self.ui.show_options("New notes", [
            (f"Velocity ({self.velocity})", lambda: self.ui.edit_value("New note velocity", self.velocity, 1, 127,
                                                                       set_velocity), None, None),
            (f"Duration ({self.duration:g} steps)", lambda: self.ui.edit_value(
                "New note duration (steps)", self.duration, 0.5, 64.0, set_duration, step=0.5, decimals=1),
             None, None),
        ])

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
        self.select_mode = not self.select_mode
        if not self.select_mode:
            self._block = None
            self.copied = None
        self.blockChanged.emit()

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
            self.libseq.savePatternSnapshot()
        n = self.libseq.copyPatternBuffer(self.pattern, self._block[0], self._block[2], note1, note2, cut)
        if cut:
            self._changed()
        if n:
            self.copied = list(self._block)
            self.ui.show_info(f"{'Cut' if cut else 'Copied'} {n} notes: tap where to paste")
        else:
            self.copied = None
            self.ui.show_info("No notes in the selection")
        self.blockChanged.emit()

    @Slot()
    def deleteBlock(self):
        """Remove the selected block's notes (a cut without keeping the copy)"""
        if self._block:
            note1, note2 = self._block_notes(self._block)
            self.libseq.savePatternSnapshot()
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
        self.libseq.savePatternSnapshot()
        self.libseq.pastePatternBuffer(self.pattern, dstep, 0.0, max(-127, min(127, dnote)), False)
        self._changed()

    @Slot()
    def entryOptions(self):
        self.entry_options()

    @Slot()
    def undo(self):
        self.libseq.savePatternSnapshot()
        if self.libseq.undoPattern():
            self._events = note_events(self.libseq)
            self.libseq.isPatternModified()
            self.eventsChanged.emit()
            self.ccChanged.emit()

    @Slot()
    def redo(self):
        if self.libseq.redoPattern():
            self._events = note_events(self.libseq)
            self.libseq.isPatternModified()
            self.eventsChanged.emit()
            self.ccChanged.emit()

    @Slot()
    def togglePlayback(self):
        zs = self.zynseq
        if self.libseq.getPlayState(zs.scene, self.phrase, self.sequence) == zynseq.SEQ_STOPPED:
            # From the start of the pattern (work around for a timebase issue in the library)
            self.libseq.setSequencePlayPosition(zs.scene, self.phrase, self.sequence, 0)
            self.libseq.setPlayState(zs.scene, self.phrase, self.sequence, zynseq.SEQ_STARTING)
        else:
            self.libseq.setPlayState(zs.scene, self.phrase, self.sequence, zynseq.SEQ_STOPPED)

    # Menu (zynthian_gui_pated_base / _notes menu, the main entries)

    @Slot()
    def menu(self):
        ls = self.libseq
        beats = ls.getBeatsInPattern()
        scales = scale_names(self.ui.chain_manager, self.channel)
        scale = ls.getScale()
        chord_label = CHORD_MODES[self.chord_mode] + (f": {CHORDS[self.chord_type][0]}" if self.chord_mode == 1 else "")
        opts = [
            ("Edit notes" if self.cc_mode else "Edit CC", self.toggleCcMode, None, None),
            (f"Length ({beats} beats)", self._pick_length, None, None),
            (f"Steps/Beat ({ls.getStepsPerBeat()})", self._pick_steps_per_beat, None, None),
            (f"Scale ({scales[scale] if scale < len(scales) else scale})", lambda: self._pick(
                "Scale", list(zip(scales, range(len(scales)))), scale, self._set_scale), None, None),
            (f"Tonic ({NOTE_NAMES[ls.getTonic() % 12]})", lambda: self._pick(
                "Tonic", list(zip(NOTE_NAMES, range(12))), ls.getTonic(), self._set_tonic), None, None),
            ("Transpose up", lambda: self._transpose(1), None, None),
            ("Transpose down", lambda: self._transpose(-1), None, None),
            ("New note values", self.entry_options, None, None),
            (f"Chord mode ({chord_label})", self._pick_chord_mode, None, None),
            ("Undo all", self._undo_all, None, None),
            ("Clear pattern", lambda: self.ui.confirm(f"Clear pattern {self.pattern}?", self._clear), None, None),
        ]
        if self.cc_mode:
            interp = bool(ls.getInterpolateCC(self.cc_num))
            opts.insert(1, (f"{'☒' if interp else '☐'} Interpolate CC{self.cc_num} values",
                            lambda: (ls.setInterpolateCC(self.cc_num, not interp), self.ccChanged.emit()), None, None))
            opts.insert(2, (f"CC number ({self.cc_num})", self.pickCc, None, None))
            opts.append((f"Clear pattern CC{self.cc_num}", lambda: self.ui.confirm(
                f"Clear CC{self.cc_num} in pattern {self.pattern}?", self._clear_cc), None, None))
        self.ui.show_options("Pattern Editor", opts)

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
        self.libseq.savePatternSnapshot()
        self.libseq.clearControl(self.cc_num)
        self.libseq.savePatternSnapshot()
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
        self._pick("Length (beats)", [(str(b), b) for b in range(1, 65)], self.libseq.getBeatsInPattern(), apply)

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
        self.libseq.savePatternSnapshot()
        if self.libseq.getScale():
            # Transposing works on the chromatic scale (as Tk)
            self.libseq.setScale(0)
            self.load()
        self.libseq.transpose(offset)
        self._changed()

    def _undo_all(self):
        self.libseq.savePatternSnapshot()
        if self.libseq.undoPatternAll():
            self._changed()

    def _clear(self):
        self.libseq.savePatternSnapshot()
        self.libseq.clearPattern(self.pattern)
        self._changed()
        if self.libseq.getPlayState(self.zynseq.scene, self.phrase, self.sequence) != zynseq.SEQ_STOPPED:
            self.libseq.sendMidiCommand(0xB0 | self.channel, 123, 0)   # all notes off

    # Keys

    def navigate(self, what):
        if self.cc_mode:
            self._cc_navigate(what)
            return
        step, row = self.cursor
        if what == "left":
            step = max(0, step - 1)
        elif what == "right":
            step = min(self.steps - 1, step + 1)
        elif what == "up":
            row = min(len(self.keymap) - 1, row + 1)
        elif what == "down":
            row = max(0, row - 1)
        elif what == "select":
            self.toggleNote(step, row)
            return
        elif what == "select_bold":
            self.editNote(step, row)
            return
        self.cursor = [step, row]
        self.cursorChanged.emit()
        if what in ("up", "down"):
            note = self._note(row)
            if note is not None:
                self._play_preview(note, self.velocity)

    def back(self):
        return False
