"""Chain routing: audio outputs and MIDI inputs/outputs of the active chain (zynthian_gui_audio_out,
zynthian_gui_midi_config in chain mode). The lists and route changes are shared with the Tk UI
(zyngui.zynthian_audio_out_data, zyngui.zynthian_midi_config_data)."""

import zynautoconnect
from zyngui.zynthian_audio_out_data import audio_out_list
from zyngui.zynthian_midi_config_data import midi_config_action, midi_config_list
from zynqt.screens.base import NOT_PORTED, SelectorScreen, entry
from zynqt.screens.chain_screens import list_data_entries


class AudioOut(SelectorScreen):
    name = "audio_out"

    def build(self):
        self.playback_ports = zynautoconnect.get_hw_audio_dst_ports()
        super().build()

    def fill(self):
        chain = self.chain_manager.get_active_chain()
        self.set_title(f"{chain.get_name()}/Send Audio to ...")
        self.set_entries(list_data_entries(audio_out_list(self.chain_manager, self.playback_ports)))

    def select_action(self, index, t):
        if t == "S":
            self.chain_manager.get_active_chain().toggle_audio_out(self.entries[index]["data"][0])
            self.fill()


class MidiRouting(SelectorScreen):
    """MIDI inputs (midi_in) or outputs (midi_out) of the active chain"""

    midi_input = True

    def fill(self):
        chain = self.chain_manager.get_active_chain()
        self.set_title(f"{chain.get_name()}/MIDI {'Input' if self.midi_input else 'Output'}")
        if not chain.is_midi() or chain.midi_chan is None:
            self.set_entries([entry("This chain has no MIDI.", enabled=False)])
            return
        self.set_entries(list_data_entries(midi_config_list(self.state_manager, chain, self.midi_input)))

    def select_action(self, index, t):
        if t != "S":
            self.ui.show_info(NOT_PORTED)
            return
        chain = self.chain_manager.get_active_chain()
        what = midi_config_action(self.state_manager, chain, self.midi_input, self.entries[index]["data"])
        if what == "midi_chan":
            self.ui.set_midi_channel()
        elif what:
            self.ui.show_info(NOT_PORTED)
        else:
            self.fill()


class MidiIn(MidiRouting):
    name = "midi_in"
    midi_input = True


class MidiOut(MidiRouting):
    name = "midi_out"
    midi_input = False


class MidiDevices(SelectorScreen):
    """MIDI devices and services (zynthian_gui_midi_config without a chain): the main menu's
    MIDI Input and MIDI Output. Services can be switched on and off; device options are not
    ported yet."""

    midi_input = True

    def fill(self):
        self.set_title(f"MIDI {'Input' if self.midi_input else 'Output'} Devices")
        self.set_entries(list_data_entries(midi_config_list(self.state_manager, None, self.midi_input)))

    def select_action(self, index, t):
        what = midi_config_action(self.state_manager, None, self.midi_input, self.entries[index]["data"])
        if what:
            self.ui.show_info(NOT_PORTED)
        else:
            self.fill()


class MidiDevicesIn(MidiDevices):
    name = "midi_devices_in"
    midi_input = True


class MidiDevicesOut(MidiDevices):
    name = "midi_devices_out"
    midi_input = False
