"""zynsigman -> Qt signals.

zynsigman calls its callbacks on the thread that sends a signal (any engine, MIDI or OSC thread)
or on its queue thread. QObjects may only be touched in the GUI thread, so the callbacks here do
nothing but emit Qt signals: emitted from another thread, Qt queues them to the receivers in the
GUI thread.
"""

import logging

from PySide6.QtCore import QObject, Signal

from zyngine.zynthian_signal_manager import zynsigman


class SignalBridge(QObject):
    # Chains or their processors changed: added, removed, moved, renamed, all removed
    chainsChanged = Signal()
    activeChainChanged = Signal()
    # A mixer strip value: mixbus, channel, symbol (level, balance, mute, solo, ...), value
    mixerValueChanged = Signal(bool, int, str, float)
    snapshotLoaded = Signal()
    processorControllersChanged = Signal()
    recorderStateChanged = Signal()
    # Sequencer (launcher): play state of the sequence of channel chan (32: phrase) in phrase;
    # the whole state (sequences added, removed, renamed, ...); the selected phrase
    seqPlayStateChanged = Signal(int, int)
    seqStateChanged = Signal()
    seqPhraseSelected = Signal(int)
    # MIDI input (for learning): device index, channel, CC number / note / program, value / velocity
    midiCc = Signal(int, int, int, int)
    midiNoteOn = Signal(int, int, int, int)
    midiProgramChange = Signal(int, int, int)
    zs3Saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._registered = []
        for ss in (zynsigman.SS_ADD_CHAIN, zynsigman.SS_REMOVE_CHAIN, zynsigman.SS_REMOVE_ALL_CHAINS,
                   zynsigman.SS_MOVE_CHAIN, zynsigman.SS_RENAME_CHAIN, zynsigman.SS_ADD_PROCESSOR,
                   zynsigman.SS_REMOVE_PROCESSOR):
            self._register(zynsigman.S_CHAIN_MAN, ss, self._cb_chains)
        self._register(zynsigman.S_CHAIN_MAN, zynsigman.SS_SET_ACTIVE_CHAIN, self._cb_active_chain)
        self._register(zynsigman.S_MIXER, zynsigman.SS_ZYNMIXER_SET_VALUE, self._cb_mixer_value)
        self._register(zynsigman.S_STATE_MAN, zynsigman.SS_LOAD_SNAPSHOT, self._cb_snapshot)
        self._register(zynsigman.S_PROCESSOR, zynsigman.SS_PROCESSOR_CTRL_SCREENS,
                       self._cb_ctrl_screens)
        self._register(zynsigman.S_AUDIO_RECORDER, zynsigman.SS_AUDIO_RECORDER_STATE, self._cb_recorder)
        self._register(zynsigman.S_STATE_MAN, zynsigman.SS_MIDI_RECORDER_STATE, self._cb_recorder)
        self._register(zynsigman.S_STATE_MAN, zynsigman.SS_MIDI_PLAYER_STATE, self._cb_recorder)
        self._register(zynsigman.S_STEPSEQ, zynsigman.SS_SEQ_PLAY_STATE, self._cb_seq_play_state)
        self._register(zynsigman.S_STEPSEQ, zynsigman.SS_SEQ_STATE, self._cb_seq_state)
        self._register(zynsigman.S_STEPSEQ, zynsigman.SS_SEQ_SELECT_PHRASE, self._cb_seq_phrase)
        self._register(zynsigman.S_MIDI, zynsigman.SS_MIDI_CC, self._cb_midi_cc)
        self._register(zynsigman.S_MIDI, zynsigman.SS_MIDI_NOTE_ON, self._cb_midi_note_on)
        self._register(zynsigman.S_MIDI, zynsigman.SS_MIDI_PC, self._cb_midi_pc)
        self._register(zynsigman.S_STATE_MAN, zynsigman.SS_SAVE_ZS3, self._cb_zs3_saved)

    def _register(self, signal, subsignal, callback):
        zynsigman.register(signal, subsignal, callback)
        self._registered.append((signal, subsignal, callback))

    def stop(self):
        for signal, subsignal, callback in self._registered:
            zynsigman.unregister(signal, subsignal, callback)
        self._registered = []

    def _cb_chains(self, **kwargs):
        self.chainsChanged.emit()

    def _cb_active_chain(self, **kwargs):
        self.activeChainChanged.emit()

    def _cb_mixer_value(self, chan=None, symbol=None, value=None, mixbus=False, **kwargs):
        if chan is None or symbol is None:
            return
        try:
            self.mixerValueChanged.emit(bool(mixbus), int(chan), str(symbol), float(value))
        except (TypeError, ValueError) as e:
            logging.debug(f"mixer value {symbol}={value!r}: {e}")

    def _cb_midi_cc(self, izmip=0, chan=0, num=0, val=0, **kwargs):
        self.midiCc.emit(int(izmip), int(chan), int(num), int(val))

    def _cb_midi_note_on(self, izmip=0, chan=0, note=0, vel=0, **kwargs):
        self.midiNoteOn.emit(int(izmip), int(chan), int(note), int(vel))

    def _cb_midi_pc(self, izmip=0, chan=0, num=0, **kwargs):
        self.midiProgramChange.emit(int(izmip), int(chan), int(num))

    def _cb_zs3_saved(self, **kwargs):
        self.zs3Saved.emit()

    def _cb_snapshot(self, **kwargs):
        self.snapshotLoaded.emit()

    def _cb_ctrl_screens(self, **kwargs):
        self.processorControllersChanged.emit()

    def _cb_recorder(self, **kwargs):
        self.recorderStateChanged.emit()

    def _cb_seq_play_state(self, phrase=0, chan=0, **kwargs):
        self.seqPlayStateChanged.emit(int(phrase), int(chan))

    def _cb_seq_state(self, **kwargs):
        self.seqStateChanged.emit()

    def _cb_seq_phrase(self, phrase=0, **kwargs):
        self.seqPhraseSelected.emit(int(phrase))
