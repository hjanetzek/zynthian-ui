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
            _todo("Chain\nManager", "chain_manager.png"),
            entry("Snapshots", lambda e: ui.show_screen("snapshot"), icon="snapshot.png"),
            entry("Clean", lambda e: self.clean_menu(), icon="delete.png"),
            _todo("MIDI\nInput", "midi_input.png"),
            _todo("MIDI\nOutput", "midi_output.png"),
            _todo("Tempo", "metronome.png"),
            _todo("ZS3s", "zs3.png"),
            _todo("Audio\nRecorder", "rec_audio.png"),
            _todo("Audio\nPlayer", "folder_audio.png"),
            _todo("MIDI\nRecorder", "rec_midi.png"),
            _todo("Admin", "settings.png"),
        ])

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
