"""Chain routing: audio outputs and MIDI inputs/outputs of the active chain (zynthian_gui_audio_out,
zynthian_gui_midi_config in chain mode). The lists and route changes are shared with the Tk UI
(zyngui.zynthian_audio_out_data, zyngui.zynthian_midi_config_data)."""

import zynautoconnect
from zyncoder.zyncore import lib_zyncore
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
            row = self.entries[index]["data"]
            if row and isinstance(row[1], int) and not isinstance(row[0], int):
                show_device_options(self.ui, self.midi_input, row[1], self.fill)
            else:
                self.ui.show_info(NOT_PORTED)
            return
        chain = self.chain_manager.get_active_chain()
        what = midi_config_action(self.state_manager, chain, self.midi_input, self.entries[index]["data"])
        if what == "midi_chan":
            self.ui.set_midi_channel()
        elif what in ("midi_cc", "midi_key_range"):
            self.ui.show_screen(what)
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
        row = self.entries[index]["data"]
        what = midi_config_action(self.state_manager, None, self.midi_input, row)
        if what == "options" and isinstance(row[1], int):
            show_device_options(self.ui, self.midi_input, row[1], self.fill)
        elif what:
            self.ui.show_info(NOT_PORTED)
        else:
            self.fill()


class MidiDevicesIn(MidiDevices):
    name = "midi_devices_in"
    midi_input = True


class MidiDevicesOut(MidiDevices):
    name = "midi_devices_out"
    midi_input = False


def show_device_options(ui, midi_input, idev, refresh):
    """Options of MIDI device idev (as zynthian_gui_midi_config.show_options/menu_cb): input mode,
    sequencer capture, MIDI clock, port name. Controller drivers are not ported yet."""
    try:
        port = (zynautoconnect.devices_in if midi_input else zynautoconnect.devices_out)[idev]
    except (IndexError, TypeError):
        return
    if port is None:
        return

    def act(func):
        def run():
            try:
                func()
            except Exception as e:
                ui.show_info(f"Failed: {e}")
            refresh()
        return run

    opts = []
    if midi_input:
        if zynautoconnect.get_midi_in_dev_mode(idev):
            opts.append(("Input mode (Active chain)", act(lambda: (lib_zyncore.zmip_set_flag_active_chain(idev, False),
                                                                  zynautoconnect.update_midi_in_dev_mode(idev))),
                         "Active chain mode: MIDI goes to the active chain. Select for multitimbral mode.",
                         "midi_input.png"))
        else:
            opts.append(("Input mode (Multitimbral)", act(lambda: (lib_zyncore.zmip_set_flag_active_chain(idev, True),
                                                                  zynautoconnect.update_midi_in_dev_mode(idev))),
                         "Multitimbral mode: MIDI goes to the chains on its channel. Select for active chain mode.",
                         "midi_input.png"))
        capture = port.aliases[0] not in zynautoconnect.get_zynseq_exclude_ports()
        opts.append((("☒" if capture else "☐") + " Sequencer capture",
                     act(lambda: zynautoconnect.toggle_zynseq_input_zmop(idev)),
                     "Use this input device for live recording from the step sequencer.", "midi_input.png"))
        clock = zynautoconnect.get_ext_clock_zmip() == idev
        opts.append((("☒" if clock else "☐") + " MIDI Clock Source",
                     act(lambda: zynautoconnect.set_ext_clock_zmip(-1 if clock else idev)),
                     "Sync to MIDI clock from this device (only one device at a time).", "midi_input.png"))
    else:
        sending = port.aliases[0] in zynautoconnect.get_midi_clock_output_ports()
        opts.append((("☒" if sending else "☐") + " Send MIDI Clock",
                     act(lambda: zynautoconnect.toggle_midi_clock_output_zmop(idev)),
                     "Send MIDI clock to this device.", "midi_output.png"))

    def rename(name):
        zynautoconnect.set_port_friendly_name(port, name)
        refresh()

    opts.append(("Rename port",
                 lambda: ui.show_keyboard(rename, port.aliases[1], "Port name"), "Rename this port.", None))
    opts.append(("Reset name", act(lambda: zynautoconnect.set_port_friendly_name(port)),
                 "Back to the port's own name.", None))
    ui.show_options(port.aliases[1], opts)
