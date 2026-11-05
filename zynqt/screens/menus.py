"""Main menu and add-chain menu (grids), as zynthian_gui_main_menu and zynthian_gui_add_chain"""

from zynqt.screens.base import NOT_PORTED, SelectorScreen, entry


def _todo(title, icon):
    return entry(title, icon=icon, enabled=False, info=NOT_PORTED)


class MainMenu(SelectorScreen):
    name = "main_menu"
    kind = "grid"
    columns = 4

    def fill(self):
        self.set_title("Main")
        ui = self.ui
        self.set_entries([
            entry("Add\nChain", lambda e: ui.cuia_add_chain(), icon="add_chain.png"),
            entry("Chain\nManager", lambda e: ui.show_screen("chain_manager"), icon="chain_manager.png"),
            entry("Snapshots", lambda e: ui.show_screen("snapshot"), icon="snapshot.png"),
            entry("Clean", lambda e: self.clean_menu(), icon="delete.png"),
            entry("MIDI\nInput", lambda e: ui.show_screen("midi_devices_in"), icon="midi_input.png"),
            entry("MIDI\nOutput", lambda e: ui.show_screen("midi_devices_out"), icon="midi_output.png"),
            entry("Tempo", lambda e: ui.show_screen("tempo"), icon="metronome.png"),
            entry("ZS3s", lambda e: ui.show_screen("zs3"), icon="zs3.png"),
            self.audio_rec_entry(),
            entry("Audio\nPlayer", lambda e: ui.show_screen("audio_player"), icon="folder_audio.png"),
            self.midi_rec_entry(),
            entry("MIDI\nPlayer", lambda e: ui.show_screen("midi_recorder"), icon="folder_midi.png"),
            entry("Admin", lambda e: ui.show_screen("admin"), icon="settings.png"),
        ])

    def audio_rec_entry(self):
        rec = bool(self.state_manager.audio_recorder.status)
        return entry("Stop Audio\nRecording" if rec else "Start Audio\nRecording",
                     lambda e: self.ui.cuia_toggle_audio_record(),
                     icon="audio_recording.png" if rec else "audio_recorder.png")

    def midi_rec_entry(self):
        rec = bool(self.state_manager.status_midi_recorder)
        return entry("Stop MIDI\nRecording" if rec else "Start MIDI\nRecording",
                     lambda e: self.ui.cuia_toggle_midi_record(),
                     icon="midi_recording.png" if rec else "midi_recorder.png")

    def clean_menu(self):
        def clean_chains():
            sm = self.state_manager
            if self.chain_manager.get_chain_count() > 1:
                sm.save_last_state_snapshot()
            sm.clean_chains()
            self.ui.show_screen_reset("mixer")
        self.ui.confirm("Remove all chains?", clean_chains)


class AddChain(SelectorScreen):
    """Chain type, then zynthian_qt's ChainEdit asks for the engine and MIDI channel"""

    name = "add_chain"
    kind = "grid"
    columns = 4

    def __init__(self, ui, parent=None):
        super().__init__(ui, parent)
        self.pos = 0

    def fill(self):
        self.set_title("Add Chain...")
        pos = self.pos
        types = [
            ("Instrument", "midi_instrument.png",
             {"type": "MIDI Synth", "midi_thru": False, "audio_thru": False}),
            ("Audio Input", "microphone.png",
             {"type": "Audio Effect", "midi_thru": False, "audio_thru": True}),
            ("Clip Launcher", "zynthian_logo.png",
             {"type": "Audio Generator", "midi_thru": False, "audio_thru": False, "engine": "CL",
              "midi_chan": None}),
            ("MIDI", "midi_logo.png", {"type": "MIDI Tool", "midi_thru": True, "audio_thru": False}),
            ("MIDI\n+\nAudio", "midi_audio.png",
             {"type": "Audio Effect", "midi_thru": True, "audio_thru": True}),
            ("Audio Generator", "audio_generator.png",
             {"type": "Audio Generator", "midi_thru": False, "audio_thru": False}),
            ("Special", "special_chain.png", {"type": "Special", "midi_thru": True, "audio_thru": True}),
            ("Mixbus", "effects_loop.png",
             {"type": "Audio Effect", "midi_thru": False, "audio_thru": True, "mixbus": True}),
        ]
        entries = []
        for title, icon, status in types:
            status = dict(status, pos=pos)
            entries.append(entry(title, lambda e, s=status: self.ui.modify_chain(s), icon=icon))
        if self.chain_manager.get_processor_count(eng_code="CL") > 15:
            entries[2] = entry("Clip Launcher\nMax. 16 reached!", icon="audio.png", enabled=False,
                               info="There are 16 clip launchers already.")
        self.set_entries(entries, 0)
