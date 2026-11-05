"""Mixer strips and meters for the Qt UI.

MixerModel: one row per chain with a mixer processor (channel strips; the main mixbus, chain 0,
in its own model), with the strip's controller values. Values change through zynsigman
(SS_ZYNMIXER_SET_VALUE, via SignalBridge), whoever changed them (this UI, MIDI, OSC, a snapshot).

MixerMeters: the strips' levels, read from zynmixer in one call per mixer at frame rate (like
the Tk mixer's update_dpm_states) and exposed as one list property, which the QML meters bind to.
"""

import logging
import os

from PySide6.QtCore import (QAbstractListModel, QModelIndex, QObject, QTimer, Qt, Property, Signal,
                            Slot)

# DPM range as in zynthian_gui_dpm: empty at -50 dB
LOW_DB = -50.0


def db_to_fraction(db):
    return max(0.0, 1.0 - max(db, LOW_DB) / LOW_DB)


class MixerModel(QAbstractListModel):
    ChainIdRole, NameRole, MidiChanRole, LevelRole, BalanceRole, MuteRole, SoloRole, RecordRole, \
        IsMixbusRole, MeterIndexRole = range(Qt.UserRole + 1, Qt.UserRole + 11)

    _ROLE_NAMES = {ChainIdRole: b"chainId", NameRole: b"name", MidiChanRole: b"midiChan",
                   LevelRole: b"level", BalanceRole: b"balance", MuteRole: b"mute",
                   SoloRole: b"solo", RecordRole: b"record", IsMixbusRole: b"isMixbus",
                   MeterIndexRole: b"meterIndex"}
    _SYMBOL_ROLES = {"level": LevelRole, "balance": BalanceRole, "mute": MuteRole,
                     "solo": SoloRole, "record": RecordRole}

    countChanged = Signal()

    def __init__(self, chain_manager, bridge, main_only=False, parent=None):
        super().__init__(parent)
        self.chain_manager = chain_manager
        self.main_only = main_only
        self.chain_ids = []
        bridge.chainsChanged.connect(self.reload)
        bridge.snapshotLoaded.connect(self.reload)
        bridge.mixerValueChanged.connect(self._mixer_value)
        self.reload()

    # Rows

    @Slot()
    def reload(self):
        chain_ids = [chain_id for chain_id, chain in self.chain_manager.chains.items()
                     if (chain_id == 0) == self.main_only]
        if chain_ids == self.chain_ids:
            # Same strips: names or mixer processors may have changed
            if self.chain_ids:
                self.dataChanged.emit(self.index(0), self.index(len(self.chain_ids) - 1))
            return
        self.beginResetModel()
        self.chain_ids = chain_ids
        self.endResetModel()
        self.countChanged.emit()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.chain_ids)

    @Property(int, notify=countChanged)
    def count(self):
        return len(self.chain_ids)

    def roleNames(self):
        return self._ROLE_NAMES

    def chain(self, row):
        try:
            return self.chain_manager.chains[self.chain_ids[row]]
        except (IndexError, KeyError):
            return None

    @staticmethod
    def _controller(chain, symbol):
        proc = chain.zynmixer_proc if chain else None
        if proc is None:
            return None
        return proc.controllers_dict.get(symbol)

    def data(self, index, role=Qt.DisplayRole):
        chain = self.chain(index.row()) if index.isValid() else None
        if chain is None:
            return None
        if role == self.ChainIdRole:
            return chain.chain_id
        if role == self.NameRole:
            return chain.get_name() or f"Chain {chain.chain_id}"
        if role == self.MidiChanRole:
            return -1 if chain.midi_chan is None or chain.midi_chan > 15 else chain.midi_chan
        if role == self.IsMixbusRole:
            return bool(chain.zynmixer_proc and chain.zynmixer_proc.eng_code == "MR")
        if role == self.MeterIndexRole:
            return index.row()
        for symbol, r in self._SYMBOL_ROLES.items():
            if role == r:
                zctrl = self._controller(chain, symbol)
                if zctrl is None:
                    return 0.0 if symbol in ("level", "balance") else False
                return float(zctrl.value) if symbol in ("level", "balance") else bool(zctrl.value)
        return None

    def strip_for(self, mixbus, chan):
        for row, chain_id in enumerate(self.chain_ids):
            chain = self.chain_manager.chains.get(chain_id)
            proc = chain.zynmixer_proc if chain else None
            if proc and proc.mixer_chan == chan and (proc.eng_code == "MR") == mixbus:
                return row
        return None

    @Slot(bool, int, str, float)
    def _mixer_value(self, mixbus, chan, symbol, value):
        role = self._SYMBOL_ROLES.get(symbol)
        row = self.strip_for(mixbus, chan) if role else None
        if row is not None:
            i = self.index(row)
            self.dataChanged.emit(i, i, [role])

    # Changes from the UI: through the processor's controllers, as the Tk mixer does, so MIDI
    # learn, snapshots and feedback work the same

    def _set(self, row, symbol, value):
        zctrl = self._controller(self.chain(row), symbol)
        if zctrl is not None:
            zctrl.set_value(value)

    @Slot(int, float)
    def setLevel(self, row, value):
        self._set(row, "level", max(0.0, min(1.0, value)))

    @Slot(int, float)
    def setBalance(self, row, value):
        self._set(row, "balance", max(-1.0, min(1.0, value)))

    @Slot(int)
    def toggleMute(self, row):
        zctrl = self._controller(self.chain(row), "mute")
        if zctrl is not None:
            zctrl.set_value(int(not zctrl.value))

    @Slot(int)
    def toggleSolo(self, row):
        zctrl = self._controller(self.chain(row), "solo")
        if zctrl is not None:
            zctrl.set_value(int(not zctrl.value))


class MixerMeters(QObject):
    """Levels of the strips of a MixerModel: for row r, levels[4r..4r+3] are channel A, channel
    B, hold A, hold B, as fractions of the meter height (0 = empty). Runs while active."""

    levelsChanged = Signal()
    activeChanged = Signal()

    def __init__(self, state_manager, model, parent=None):
        super().__init__(parent)
        self.state_manager = state_manager
        self.model = model
        self._levels = []
        self._active = False
        hz = int(os.environ.get("ZYNTHIAN_QT_METER_HZ", 30))
        self._timer = QTimer(self, interval=max(10, round(1000 / hz)), timerType=Qt.PreciseTimer)
        self._timer.timeout.connect(self.update)

    @Property("QVariantList", notify=levelsChanged)
    def levels(self):
        return self._levels

    def _get_active(self):
        return self._active

    def _set_active(self, active):
        if active == self._active:
            return
        self._active = active
        sm = self.state_manager
        for mixer in (sm.zynmixer_chan, sm.zynmixer_bus):
            if mixer:
                mixer.enable_dpm(active)
        if active:
            self._timer.start()
        else:
            self._timer.stop()
        self.activeChanged.emit()

    active = Property(bool, _get_active, _set_active, notify=activeChanged)

    @Slot()
    def update(self):
        sm = self.state_manager
        try:
            sm.zynmixer_chan.update_dpm_states()
            sm.zynmixer_bus.update_dpm_states()
        except Exception as e:
            logging.debug(f"DPM update: {e}")
            return
        levels = []
        for row in range(self.model.rowCount()):
            chain = self.model.chain(row)
            proc = chain.zynmixer_proc if chain else None
            if proc is None or proc.mixer_chan is None:
                levels += [0.0, 0.0, 0.0, 0.0]
                continue
            dpm = proc.zynmixer.dpm[proc.mixer_chan]
            levels += [db_to_fraction(dpm.a), db_to_fraction(dpm.b),
                       db_to_fraction(dpm.a_hold), db_to_fraction(dpm.b_hold)]
        if levels != self._levels:
            self._levels = levels
            self.levelsChanged.emit()
