"""Admin menu (zynthian_gui_admin), the entries available in desktop mode. Simple settings use the
toggles shared with the Tk UI (zyngui.zynthian_admin_settings); the others are not ported yet."""

from zyncoder.zyncore import lib_zyncore
from zyngui import zynthian_admin_settings, zynthian_gui_config as cfg
from zynqt.screens.base import NOT_PORTED, SelectorScreen, entry, separator


def _check(flag):
    return "☒ " if flag else "☐ "


class Admin(SelectorScreen):
    name = "admin"

    def fill(self):
        self.set_title("Admin")
        s = zynthian_admin_settings

        def toggle(func):
            return lambda e: (func(), self.fill())

        def todo(title, icon):
            return entry(title, icon=icon, enabled=False, info=NOT_PORTED)

        e = [separator("> MIDI")]
        if cfg.midi_prog_change_zs3:
            e.append(entry("Program Change => ZS3", toggle(s.toggle_prog_change_zs3), icon="midi_settings.png",
                           info="MIDI program changes load ZS3s. Select to load processor presets instead."))
        else:
            e.append(entry("Program Change => Processor Presets", toggle(s.toggle_prog_change_zs3),
                           icon="midi_settings.png",
                           info="MIDI program changes load processor presets. Select to load ZS3s instead."))
            e.append(entry(_check(cfg.midi_bank_change) + "MIDI Bank Change", toggle(s.toggle_bank_change),
                           icon="midi_settings.png", info="MIDI bank changes select processor banks."))
        e.append(entry(_check(lib_zyncore.get_active_midi_chan()) + "Active MIDI channel",
                       toggle(s.toggle_active_midi_channel), icon="midi_settings.png",
                       info="MIDI from devices in active mode goes to the active chain's channel."))
        e.append(entry(_check(cfg.midi_usb_by_port) + "MIDI-USB mapped by port", toggle(s.toggle_usbmidi_by_port),
                       icon="midi_settings.png", info="Identify USB MIDI devices by the port they are plugged into."))
        e += [todo("Global Transpose", "midi_settings.png"), todo("Channel Pressure => CC", "midi_settings.png"),
              todo("Test MIDI", "midi_test.png")]

        e.append(separator("> AUDIO"))
        e += [todo("PFL Output", "headphones.png"), todo("ZynVoice", "audio_options.png"),
              todo("Hotplug USB Audio", "audio_options.png")]
        e.append(entry(_check(cfg.snapshot_mixer_settings) + "Audio Levels on Snapshots",
                       toggle(s.toggle_snapshot_mixer_settings), icon="audio_options.png",
                       info="Save and restore the audio levels with snapshots."))
        e.append(entry(_check(cfg.enable_dpm) + "Mixer Peak Meters", toggle(s.toggle_dpm), icon="meters.png",
                       info="Show the peak meters of the chain strips (the main strip always has them)."))
        e.append(todo("Test Audio", "audio_test.png"))

        e.append(separator("> USER INTERFACE"))
        e.append(entry(_check(cfg.preset_preload) + "Preset Preload", toggle(s.toggle_preset_preload),
                       icon="settings.png", info="Load presets when they are selected in the list."))

        e.append(separator("> SYSTEM"))
        e.append(entry("Restart UI", lambda x: self.ui.confirm("Restart the user interface?",
                                                                 lambda: self.ui.exit(102)),
                       icon="settings.png", info="Save the state and restart zynthian."))
        e.append(entry("Exit", lambda x: self.ui.confirm("Exit zynthian?", lambda: self.ui.exit(101)),
                       icon="poweroff.png", info="Save the state and exit zynthian."))
        self.set_entries(e)
