"""Pattern editor, notes (zynthian_gui_pated_notes): the selected launcher pad's pattern as a grid,
steps across, the keymap's notes (chromatic, a scale, or the synth's drum map) up the side.

Tap an empty cell to add a note (velocity and duration of the note-entry values), tap a note to
remove it, long press a note for its velocity and duration. Arrows move the cursor, SEL toggles
the note at the cursor. The keymap, events and new note defaults are shared with the Tk editor
(zyngui.zynthian_pated_data)."""

from PySide6.QtCore import QObject, QTimer, Property, Signal, Slot

from zyngui.zynthian_pated_data import (NOTE_NAMES, STEPS_PER_BEAT, default_note_evdata, load_keymap, note_events,
                                        note_name, scale_names)
from zynlibs.zynseq import zynseq


class PatternEditor(QObject):
    name = "pattern_editor"

    patternChanged = Signal()       # pattern, length, keymap: the whole grid
    eventsChanged = Signal()
    playheadChanged = Signal()
    cursorChanged = Signal()
    entryChanged = Signal()         # note-entry values (velocity, duration)

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
        return f"Vel {self.velocity}  Dur {self.duration:g}"

    # Editing (undo snapshots around each change, as the Tk editor)

    def _note(self, row):
        return self.keymap[row]["note"] if 0 <= row < len(self.keymap) else None

    def _changed(self):
        self.libseq.savePatternSnapshot()
        self._events = note_events(self.libseq)
        self.libseq.isPatternModified()
        self.eventsChanged.emit()

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
        start = self.libseq.getNoteStart(step, note)
        if start >= 0:
            self.libseq.removeNote(start, note)
            self.libseq.playNote(note, 0, self.channel)   # silence it if sounding
        else:
            self.libseq.addNote(step, note, self.velocity, self.duration, 0.0)
            self.libseq.setNoteData(step, note, default_note_evdata(self.duration, self.velocity))
            self._play_preview(note, self.velocity)
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

    @Slot()
    def redo(self):
        if self.libseq.redoPattern():
            self._events = note_events(self.libseq)
            self.libseq.isPatternModified()
            self.eventsChanged.emit()

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
        opts = [
            (f"Length ({beats} beats)", self._pick_length, None, None),
            (f"Steps/Beat ({ls.getStepsPerBeat()})", self._pick_steps_per_beat, None, None),
            (f"Scale ({scales[scale] if scale < len(scales) else scale})", lambda: self._pick(
                "Scale", list(zip(scales, range(len(scales)))), scale, self._set_scale), None, None),
            (f"Tonic ({NOTE_NAMES[ls.getTonic() % 12]})", lambda: self._pick(
                "Tonic", list(zip(NOTE_NAMES, range(12))), ls.getTonic(), self._set_tonic), None, None),
            ("Transpose up", lambda: self._transpose(1), None, None),
            ("Transpose down", lambda: self._transpose(-1), None, None),
            ("New note values", self.entry_options, None, None),
            ("Undo all", self._undo_all, None, None),
            ("Clear pattern", lambda: self.ui.confirm(f"Clear pattern {self.pattern}?", self._clear), None, None),
        ]
        self.ui.show_options("Pattern Editor", opts)

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
