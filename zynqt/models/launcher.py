"""Launcher pads for the mixer's launcher mode (zynthian_gui_mixer's launcher): one pad per chain
and phrase, what it shows from zyngui.zynthian_launcher_data (shared with the Tk UI).

QML pads call padInfo(chainId, phrase) once and again when padChanged names them (a sequence's
play state changed) or on padsChanged (the whole sequencer state: names, patterns, phrases)."""

from PySide6.QtCore import QObject, Property, Signal, Slot

from zyngui import zynthian_gui_config
from zyngui.zynthian_launcher_data import pad_channel, pad_info, toggle_pad
from zynlibs.zynseq import zynseq


class Launcher(QObject):
    padChanged = Signal(int, int)       # chain id, phrase
    padsChanged = Signal()
    phraseChanged = Signal()

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
        info = pad_info(self.zynseq, chain, phrase, zynthian_gui_config.color_tx)
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
            self.ui.show_info("The phrase menu is not in the Qt UI yet.")
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
        self.ui.show_screen("mixer", history=False)
        return True
