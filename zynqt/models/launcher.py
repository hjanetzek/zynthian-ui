"""Launcher pads for the mixer's launcher mode (zynthian_gui_mixer's launcher): one pad per chain
and phrase, what it shows from zyngui.zynthian_launcher_data (shared with the Tk UI).

QML pads call padInfo(chainId, phrase) once and again when padChanged names them (a sequence's
play state changed) or on padsChanged (the whole sequencer state: names, patterns, phrases)."""

from PySide6.QtCore import QObject, Property, Signal, Slot

from zyngui import zynthian_gui_config
from zyngui.zynthian_launcher_data import (DURATION_LABELS, LOOP_COUNT_CHOICES, duration_to_index,
                                           follow_choices, loops_to_play_options, pad_channel, pad_info,
                                           phrase_menu_options, set_phrase_value, toggle_pad,
                                           toggle_play_flag)
from zynlibs.zynseq import zynseq


class Launcher(QObject):
    padChanged = Signal(int, int)       # chain id, phrase
    padsChanged = Signal()
    phraseChanged = Signal()
    movingPhraseChanged = Signal()

    def __init__(self, ui, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.chain_manager = ui.chain_manager
        self.zynseq = ui.state_manager.zynseq
        ui.bridge.seqPlayStateChanged.connect(self._play_state)
        ui.bridge.seqStateChanged.connect(self.padsChanged)
        ui.bridge.snapshotLoaded.connect(self.padsChanged)
        ui.bridge.chainsChanged.connect(self.padsChanged)
        ui.bridge.seqPhraseSelected.connect(self._phrase_selected)
        self.moving_phrase = False

    # Changes

    def _phrase_selected(self, _phrase):
        self.phraseChanged.emit()

    def _play_state(self, phrase, chan):
        for chain_id, chain in self.chain_manager.chains.items():
            if pad_channel(chain) == chan:
                self.padChanged.emit(chain_id, phrase)

    # For QML

    @Property(int, notify=padsChanged)
    def phrases(self):
        return self.zynseq.phrases

    @Property(int, notify=phraseChanged)
    def phrase(self):
        return self.zynseq.phrase

    @Property(int, constant=True)
    def visiblePads(self):
        """Pads shown at once (admin: Visible Launchers)"""
        return zynthian_gui_config.visible_launchers if zynthian_gui_config.visible_launchers > 0 else 8

    @Slot(int, int, result="QVariantMap")
    def padInfo(self, chain_id, phrase):
        chain = self.chain_manager.chains.get(chain_id)
        if chain is None:
            return {}
        info = pad_info(self.zynseq, chain, phrase, zynthian_gui_config.color_tx, self.moving_phrase)
        info.pop("state", None)
        info["loops"] = [{"part": part, "top": c1, "bottom": c2, "text": text}
                         for part, c1, c2, text in info["loops"]]
        info["hasSequence"] = pad_channel(chain) is not None
        return info

    def select(self, chain_id, phrase):
        if self.chain_manager.active_chain is None or self.chain_manager.active_chain.chain_id != chain_id:
            self.chain_manager.set_active_chain_by_id(chain_id)
        if 0 <= phrase < self.zynseq.phrases:
            self.zynseq.select_phrase(phrase)

    @Slot(int, int)
    def tapPad(self, chain_id, phrase):
        """As a short press in Tk: select the pad, start/stop its sequence"""
        self.select(chain_id, phrase)
        chain = self.chain_manager.chains.get(chain_id)
        if chain is not None:
            toggle_pad(self.zynseq, chain, phrase)

    @Slot(int, int)
    def longPressPad(self, chain_id, phrase):
        """As a bold press in Tk: edit the pad"""
        self.select(chain_id, phrase)
        self.edit_pad()

    def edit_pad(self):
        """zynthian_gui_mixer.edit_pad: pattern editor, audio clip or phrase menu"""
        chain = self.chain_manager.get_active_chain()
        if chain is None:
            return
        if chain.chain_id == 0:
            self.phrase_menu()
        elif isinstance(chain.midi_chan, int) and chain.midi_chan < zynseq.PHRASE_CHANNEL:
            if chain.midi_chan > 15:
                # Audio clip (clippy): its processor's controls, with this phrase's clip
                proc = chain.get_processors()[0]
                chain.set_current_processor(proc)
                proc.engine.set_phrase(proc, self.zynseq.phrase)
                self.ui.chain_control(chain.chain_id, proc)
            else:
                self.ui.show_info("The pattern editor is not in the Qt UI yet.")

    def toggle_selected(self):
        chain = self.chain_manager.get_active_chain()
        if chain is not None:
            toggle_pad(self.zynseq, chain, self.zynseq.phrase)

    def select_offset(self, step):
        phrase = self.zynseq.phrase + step
        if 0 <= phrase < self.zynseq.phrases:
            self.zynseq.select_phrase(phrase)

    # Screen "launcher" (ZynUI): the mixer view in launcher mode

    def build(self):
        self.padsChanged.emit()

    def hide(self):
        pass

    def navigate(self, what):
        if self.moving_phrase:
            if what in ("up", "down"):
                self.move_phrase(-1 if what == "up" else 1)
            elif what in ("select", "select_bold"):
                self.end_moving_phrase()
            return
        if what == "up":
            self.select_offset(-1)
        elif what == "down":
            self.select_offset(1)
        elif what == "left":
            self.chain_manager.previous_chain()
        elif what == "right":
            self.chain_manager.next_chain()
        elif what == "select":
            self.toggle_selected()
        elif what == "select_bold":
            self.edit_pad()

    def back(self):
        """BACK in the launcher: back to the mixer (Tk toggles the launcher mode)"""
        if self.moving_phrase:
            self.end_moving_phrase()
            return True
        self.ui.show_screen("mixer", history=False)
        return True

    # Moving the selected phrase (phrase menu: Move / Clone)

    @Property(bool, notify=movingPhraseChanged)
    def movingPhrase(self):
        return self.moving_phrase

    def start_moving_phrase(self):
        self.moving_phrase = True
        self.movingPhraseChanged.emit()
        self.padsChanged.emit()

    @Slot()
    def end_moving_phrase(self):
        self.moving_phrase = False
        self.movingPhraseChanged.emit()
        self.padsChanged.emit()

    @Slot(int)
    def move_phrase(self, step):
        to = self.zynseq.phrase + step
        if 0 <= to < self.zynseq.phrases:
            self.zynseq.nudge_phrase(self.zynseq.scene, self.zynseq.phrase, step > 0)
            self.padsChanged.emit()
            self.phraseChanged.emit()   # nudge_phrase moves the selection without a signal

    # Phrase menu (zynthian_gui_mixer.phrase_menu, shared: zynthian_launcher_data)

    def phrase_menu(self, chan=None):
        """Options of the selected phrase (chan None) or of chan's sequence in it"""
        if chan is None:
            chan = zynseq.PHRASE_CHANNEL
        menu = phrase_menu_options(self.zynseq, chan)
        if not menu:
            return
        title, rows = menu
        options = [(label, (lambda k=key, v=value: self._phrase_option(chan, k, v)) if key else None, None, None)
                   for key, label, value in rows]
        self.ui.show_options(title, options)

    def _pick(self, chan, title, choices, current, apply):
        """Options list of (label, value), current selected; apply(value), then the menu again"""
        selected = next((i for i, (_, v) in enumerate(choices) if v == current), 0)

        def chosen(value):
            apply(value)
            self.phrase_menu(chan)

        self.ui.show_options(title, [(label, lambda v=value: chosen(v), None, None) for label, value in choices],
                             selected)

    def _set(self, chan, symbol):
        sm = self.ui.state_manager
        return lambda value: set_phrase_value(self.zynseq, self.chain_manager, sm, chan, symbol, value)

    def _phrase_option(self, chan, key, value):
        zs = self.zynseq
        match key:
            case "duration":
                self._pick(chan, "Duration", list(zip(DURATION_LABELS, range(len(DURATION_LABELS)))),
                           duration_to_index(value), self._set(chan, "duration"))
            case "automate":
                self._pick(chan, "Automate", [(title, offset) for offset, title in follow_choices(zs)], value,
                           self._set(chan, "automate"))
            case "loop_count":
                self._pick(chan, "Loop count", [(label, v) for v, label in LOOP_COUNT_CHOICES], value,
                           self._set(chan, "loop_count"))
            case "loops_to_play":
                self._loops_to_play(chan, value)
            case "tempo":
                apply = self._set(chan, "tempo")
                self.ui.edit_value("Tempo (BPM)", float(value or zs.get_tempo()), 10.0, 420.0,
                                   lambda v: (apply(v), self.phrase_menu(chan)), step=1, decimals=1)
            case "remove_tempo":
                zs.set_sequence_param(zs.scene, value, zynseq.PHRASE_CHANNEL, "tempo", 0)
                self.phrase_menu(chan)
            case "bpb":
                self._pick(chan, "Beats per bar", [(str(i), i) for i in range(1, 25)], value,
                           self._set(chan, "bpb"))
            case "rename":
                def rename(name):
                    zs.set_sequence_param(zs.scene, zs.phrase, zynseq.PHRASE_CHANNEL, "name", name[:8])
                    self.phrase_menu(chan)
                self.ui.show_keyboard(rename, value, "Phrase name (8 characters)")
            case "insert":
                zs.insert_phrase(zs.scene, value)
                self.padsChanged.emit()
                self.ui.show_screen("launcher", history=False)
            case "clone":
                sm = self.ui.state_manager
                sm.start_busy("clone_phrase", "Cloning phrase...")
                try:
                    zs.duplicate_phrase(zs.scene, value)
                    zs.select_phrase(value + 1)
                finally:
                    sm.end_busy("clone_phrase")
                self.ui.show_screen("launcher", history=False)
                self.start_moving_phrase()
            case "move":
                self.ui.show_screen("launcher", history=False)
                self.start_moving_phrase()
            case "delete":
                def remove():
                    zs.remove_phrase(zs.scene, value)
                    self.padsChanged.emit()
                self.ui.confirm(f"Remove phrase {value + 1}?", remove)

    def _loops_to_play(self, chan, flags):
        def toggle(params):
            self._loops_to_play(chan, toggle_play_flag(self.zynseq, params))

        options = [(label, lambda p=params: toggle(p), None, None)
                   for label, params in loops_to_play_options(self.zynseq, flags)]
        if options:
            self.ui.show_options("Loops to play", options)
