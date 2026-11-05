"""Processor options (zynthian_gui_processor_options): presets, bypass, replace, remove, randomize,
clean MIDI learn, insert processors"""

import random

import zynautoconnect
from zynqt.screens.base import NOT_PORTED, SelectorScreen, entry, separator


class ProcessorOptions(SelectorScreen):
    name = "processor_options"

    def __init__(self, ui, parent=None):
        super().__init__(ui, parent)
        self.processor = None
        self.last_random = {}

    def build(self):
        proc = self.ui.current_processor
        if proc is not self.processor:
            self.processor = proc
            self.last_random = {}
        super().build()

    def fill(self):
        p = self.processor
        if p is None:
            self.set_entries([])
            return
        self.set_title(f"{p.get_name()}: Options")
        e = [separator("> Manage this processor")]
        if len(p.get_bank_list()) > 1 or p.preset_list:
            e.append(entry("Presets", lambda x: self.ui.cuia_bank_preset(), icon="preset.png",
                           info="Select a bank and preset for this processor."))
        if p.type == "Audio Effect" and p.eng_code not in ("MI", "MR"):
            e.append(entry(("☒ " if p.is_bypassed() else "☐ ") + "Bypass",
                           lambda x: self.toggle_bypass(), info="Bypass this processor.", icon="bypass.png"))
        if p.type not in ("MIDI Synth", "Audio Generator") and p.chain is not None \
                and p.chain.get_processor_count(p.type) > 1:
            e.append(entry("Move", lambda x: self.ui.start_move_processor(p), icon="move_up_down.png",
                           info="Move this processor within the chain: arrows (left/right along the chain, "
                                "up/down serial/parallel), SELECT or Done to finish."))
        if p.eng_code not in ("MI", "MR"):
            if (p.type != "MIDI Synth" or p.engine.get_options()["replace"]) and p.eng_code != "CL":
                e.append(entry(f"Replace {p.name}", lambda x: self.replace(), icon="replace_processor.png",
                               info="Replace this processor with another of similar type."))
            if p.type in ("MIDI Tool", "Audio Effect"):
                e.append(entry("Remove", lambda x: self.remove(), icon="delete.png",
                               info="Remove this processor from the chain."))
        if p.type == "MIDI Synth":
            e.append(entry("Randomize parameters", lambda x: self.randomize(), icon="dice.png",
                           info="Change all processor parameters to random values.\n\n"
                                "This is truly random so may produce undesirable effect, but can undo randomization."))
            if self.last_random:
                e.append(entry("Undo Randomize", lambda x: self.undo_randomize(), icon="back.png",
                               info="Undo the last parameter randomization."))
        e.append(entry("Clean MIDI-learn", lambda x: self.midi_clean(), icon="delete_presets.png",
                       info="Remove CC bindings from all parameters in this processor."))
        e.append(entry("Info", icon="info.png", enabled=False, info=NOT_PORTED))

        add = []
        pos = "series" if p.type in ("MIDI Synth", "MIDI Tool") or p.eng_code in ("MI", "MX") else "parallel"
        if p.type in ("MIDI Synth", "MIDI Tool"):
            add.append(entry("Insert MIDI Processor", lambda x: self.add_processor("MIDI Tool"),
                             icon="midi_processor.png",
                             info=f"Insert a new MIDI processor in the chain in {pos} with this processor."))
        if p.type in ("MIDI Synth", "Audio Effect", "Audio Generator"):
            add.append(entry("Insert Audio Processor", lambda x: self.add_processor("Audio Effect"),
                             icon="audio_processor.png",
                             info=f"Insert a new audio processor in the chain in {pos} with this processor."))
        if add:
            e += [separator("> Add to chain")] + add
        self.set_entries(e)

    def toggle_bypass(self):
        self.processor.toggle_bypass()
        self.fill()

    def replace(self):
        p = self.processor
        self.ui.modify_chain({"chain_id": p.chain.chain_id, "processor": p, "type": p.type})

    def remove(self):
        p = self.processor

        def do_remove():
            sm = self.state_manager
            sm.start_busy("processor_options::do_remove", "Removing processor")
            try:
                self.chain_manager.remove_processor(p.chain.chain_id, p)
                zynautoconnect.request_audio_connect(True)
                zynautoconnect.request_midi_connect(True)
            finally:
                sm.end_busy("processor_options::do_remove")
            self.processor = None
            self.ui.set_current_processor(None)
            self.ui.purge_history("processor_options")
            self.ui.chain_control()

        self.ui.confirm(f"Do you want to remove {p.engine.name} from the chain?", do_remove)

    def add_processor(self, proc_type):
        p = self.processor
        try:
            if p.type == "MIDI Synth":
                slot = -1 if proc_type == "Audio Effect" else None
            else:
                slot = p.get_chain_slot() + 1
        except Exception:
            slot = None
        self.ui.modify_chain({"chain_id": p.chain.chain_id, "type": proc_type,
                              "midi_thru": p.midi_chan is not None,
                              "audio_thru": proc_type == "Audio Effect", "slot": slot})

    def randomize(self):
        for zctrl in self.processor.controllers_dict.values():
            if zctrl.is_integer:
                value = random.randint(zctrl.value_min, zctrl.value_max)
            else:
                value = random.uniform(zctrl.value_min, zctrl.value_max)
            self.last_random[zctrl.symbol] = zctrl.value
            zctrl.set_value(value)
        self.fill()

    def undo_randomize(self):
        for zctrl in self.processor.controllers_dict.values():
            if zctrl.symbol in self.last_random:
                value = self.last_random[zctrl.symbol]
                self.last_random[zctrl.symbol] = zctrl.value
                zctrl.set_value(value)
        self.fill()

    def midi_clean(self):
        p = self.processor
        self.ui.confirm(f"Do you want to clean MIDI-learn for ALL controls in {p.name}?",
                        lambda: self.chain_manager.clean_midi_learn(p))
