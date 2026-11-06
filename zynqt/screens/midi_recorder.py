"""MIDI recorder and player (zynthian_gui_midi_recorder): record, loop setting, the MIDI files (list
shared with the Tk UI: zyngui.zynthian_midi_recorder_data); tap plays, long press rename/delete"""

import logging
import os

import zynconf
from zyngui import zynthian_gui_config
from zyngui.zynthian_midi_recorder_data import midi_file_rows
from zynlibs.zynsmf.zynsmf import libsmf
from zynqt.screens.base import SelectorScreen, entry
from zynqt.screens.chain_screens import list_data_entries
from zynconf import zynthian_paths


class MidiRecorder(SelectorScreen):
    name = "midi_recorder"

    def fill(self):
        sm = self.state_manager
        self.set_title("MIDI Recorder")
        if sm.status_midi_recorder:
            rec = entry("■ Stop MIDI Recording", lambda e: sm.stop_midi_record(),
                        info="Stop MIDI recording.", icon="midi_recorder.png")
        else:
            rec = entry("⬤ Start MIDI Recording", lambda e: sm.start_midi_record(),
                        info="Start MIDI recording.", icon="midi_recorder.png")
        loop = entry(("☒ " if zynthian_gui_config.midi_play_loop else "☐ ") + "Loop playback",
                     lambda e: self.toggle_loop(), info="Play MIDI files in a loop.", icon="midi_recorder.png")
        stop = []
        if sm.status_midi_player:
            stop = [entry("\u25a0 Stop MIDI Playback", lambda e: sm.stop_midi_playback(),
                          info="Stop playing the MIDI file.", icon="midi_recorder.png")]
        entries = [rec] + stop + [loop] + list_data_entries(midi_file_rows(zynthian_paths.ex_data_dir, 1))
        self.set_entries(entries)

    # Transport keys here: the MIDI recorder and player (zynthian_gui_midi_recorder)

    def cuia_toggle_record(self, params=None):
        self.state_manager.toggle_midi_record()
        self.fill()
        return True

    def cuia_stop(self, params=None):
        self.state_manager.stop_midi_playback()
        self.fill()
        return True

    def cuia_toggle_play(self, params=None):
        self.state_manager.toggle_midi_playback()
        self.fill()
        return True

    def toggle_loop(self):
        zynthian_gui_config.midi_play_loop = not zynthian_gui_config.midi_play_loop
        libsmf.setLoop(zynthian_gui_config.midi_play_loop)
        zynconf.save_config({"ZYNTHIAN_MIDI_PLAY_LOOP": str(int(zynthian_gui_config.midi_play_loop))})
        self.fill()

    def select_action(self, index, t):
        e = self.entries[index]
        if callable(e["action"]):
            if t == "S":
                e["action"](e)
            return
        fpath = e["data"][0] if e["data"] else None
        if not fpath:
            return
        if t == "S":
            self.state_manager.toggle_midi_playback(fpath)
        else:
            self.show_options(fpath, e["title"])

    def show_options(self, fpath, title):
        def rename(new_name):
            new_name = new_name.strip()
            if not new_name:
                return
            try:
                os.rename(fpath, f"{os.path.dirname(fpath)}/{new_name}.mid")
            except Exception as ex:
                logging.error(f"Failed to rename MIDI file => {ex}")
            self.fill()

        def delete():
            try:
                os.remove(fpath)
            except Exception as ex:
                logging.error(f"Failed to delete MIDI file => {ex}")
            self.fill()

        name = os.path.basename(fpath)[:-4]
        self.ui.show_options(f"MIDI file {title}", [
            ("Rename", lambda: self.ui.show_keyboard(rename, name, "Rename MIDI file"), "Rename MIDI file", None),
            ("Delete", lambda: self.ui.confirm(f"Do you really want to delete '{title}'?", delete),
             "Delete MIDI file", None),
        ])
