"""Chain options (zynthian_gui_chain_options): add or remove effects, clean MIDI learn, rename or
remove the chain"""

import zynautoconnect
from zynqt.screens.base import NOT_PORTED, SelectorScreen, entry, separator


class ChainOptions(SelectorScreen):
    name = "chain_options"

    def fill(self):
        chain = self.chain_manager.get_active_chain()
        if chain is None:
            self.set_entries([])
            return
        self.set_title(f"{chain.get_name()}: Chain Options")
        midi_procs = chain.get_processor_count("MIDI Tool")
        audio_procs = max(0, chain.get_processor_count("Audio Effect") - 1)
        processors = []
        if chain.is_midi():
            processors.append(entry("Add MIDI-FX processor", lambda e: self.add_processor("MIDI Tool"),
                                    info="Add a MIDI effects processor to the end of this chain.",
                                    icon="midi_processor.png"))
        if chain.is_audio():
            processors.append(entry("Add Audio-FX processor", lambda e: self.add_processor("Audio Effect"),
                                    info="Add an audio effects processor to the end of this chain.",
                                    icon="audio_processor.png"))
        if midi_procs:
            processors.append(entry("Remove all MIDI-FX", lambda e: self.remove_all("MIDI Tool"),
                                    info="Remove all MIDI-FX processors from this chain.",
                                    icon="delete_midi_processors.png"))
        if audio_procs:
            processors.append(entry("Remove all Audio-FX", lambda e: self.remove_all("Audio Effect"),
                                    info="Remove all audio-FX processors from this chain.",
                                    icon="delete_audio_processors.png"))
        if chain.get_processor_count():
            processors.append(entry("Clean MIDI Learn", lambda e: self.clean_midi_learn(),
                                    info="Remove CC bindings from all parameters of all processors in this chain.",
                                    icon="delete_presets.png"))
        entries = ([separator("> PROCESSORS")] + processors) if processors else []
        entries.append(separator("> MANAGE"))
        if chain.chain_id:
            entries.append(entry("Move chain", icon="move_left_right.png", enabled=False,
                                 info=NOT_PORTED))
        entries.append(entry("Rename chain", lambda e: self.rename(),
                             info="Change the name of the chain. Clear name to reset to default name.",
                             icon="rename.png"))
        entries.append(entry("Export chain as snapshot...", icon="snapshot_chains.png", enabled=False,
                             info=NOT_PORTED))
        if chain.chain_id:
            entries.append(entry("Remove chain", lambda e: self.remove_chain(),
                                 info="Remove this chain and all its processors.", icon="delete_chains.png"))
        self.set_entries(entries)

    def add_processor(self, proc_type):
        chain = self.chain_manager.get_active_chain()
        slot = None
        if proc_type == "Audio Effect" and chain.zynmixer_proc:
            # Before the mixer processor (pre-fader)
            slot = chain.zynmixer_proc.get_chain_slot()
        self.ui.modify_chain({"chain_id": chain.chain_id, "type": proc_type,
                              "midi_thru": chain.midi_chan is not None,
                              "audio_thru": proc_type == "Audio Effect", "slot": slot})

    def remove_all(self, proc_type):
        chain = self.chain_manager.get_active_chain()

        def remove():
            sm = self.state_manager
            sm.start_busy("remove_all_procs", "Removing processors")
            try:
                for processor in chain.get_processors(proc_type):
                    if processor.eng_code not in ("MI", "MR"):
                        self.chain_manager.remove_processor(chain.chain_id, processor)
                zynautoconnect.request_audio_connect(True)
                zynautoconnect.request_midi_connect(True)
            finally:
                sm.end_busy("remove_all_procs")
            self.fill()

        kind = "MIDI" if proc_type == "MIDI Tool" else "audio"
        self.ui.confirm(f"Do you really want to remove all {kind} effects from this chain?", remove)

    def clean_midi_learn(self):
        chain = self.chain_manager.get_active_chain()
        self.ui.confirm(f"Clean MIDI learn for all controls of all processors in chain {chain.get_name()}?",
                        lambda: self.chain_manager.clean_midi_learn(chain.chain_id))

    def rename(self):
        chain = self.chain_manager.get_active_chain()

        def do_rename(title):
            self.chain_manager.set_chain_title(chain.chain_id, title)
            self.fill()

        self.ui.show_keyboard(do_rename, chain.title or "", "Chain name")

    def remove_chain(self):
        chain = self.chain_manager.get_active_chain()

        def remove():
            self.chain_manager.remove_chain(chain.chain_id)
            self.ui.show_screen_reset("mixer")

        self.ui.confirm("Do you really want to remove this chain?", remove)
