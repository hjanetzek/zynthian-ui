"""Admin menu (zynthian_gui_admin), the entries available in desktop mode. The settings are shared
with the Tk UI (zyngui.zynthian_admin_settings); values are picked from an options list (Tk's
param editor)."""

import logging
import shutil
import subprocess

import zynautoconnect
from zyncoder.zyncore import lib_zyncore
from zyngui import zynthian_admin_settings, zynthian_gui_config as cfg
from zynconf import zynthian_paths
from zynqt.screens.base import NOT_PORTED, SelectorScreen, entry, separator

TEST_AUDIO = f"{zynthian_paths.data_dir}/files/Audio/Oya.mp3"
TEST_MIDI = f"{zynthian_paths.data_dir}/files/Midi/roland_take5.mid"


def _check(flag):
    return "☒ " if flag else "☐ "


def _signed(value):
    return f"+{value}" if value > 0 else str(value)


class Admin(SelectorScreen):
    name = "admin"

    def __init__(self, ui, parent=None):
        super().__init__(ui, parent)
        self.test_audio_proc = None

    def pick(self, title, choices, current, action):
        """Options list of (label, value), the current value selected; action(value) then refill"""
        selected = next((i for i, (_, v) in enumerate(choices) if v == current), 0)

        def chosen(value):
            action(value)
            self.fill()

        self.ui.show_options(title, [(label, lambda v=value: chosen(v), None, None) for label, value in choices],
                             selected)

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
        gtrans = lib_zyncore.get_global_transpose()
        e.append(entry(f"Global Transpose ({_signed(gtrans) if gtrans else 'None'})",
                       lambda x: self.pick("Global Transpose", [(_signed(v), v) for v in range(-24, 25)],
                                           lib_zyncore.get_global_transpose(), lib_zyncore.set_global_transpose),
                       icon="midi_settings.png",
                       info="MIDI note transpose. It affects all MIDI messages, in addition to each chain's transpose."))
        e.append(entry(f"Channel Pressure => CC ({cfg.midi_chanpress_cc or 'NONE'})",
                       lambda x: self.pick("Channel Pressure => CC",
                                           [("NONE", 0)] + [(f"CC {v}", v) for v in range(1, 120)],
                                           cfg.midi_chanpress_cc or 0,
                                           lambda v: s.set_chanpress_cc(v, self.state_manager)),
                       icon="midi_settings.png", info="Map channel pressure messages (mono AT) to the selected CC."))
        e.append(entry("Test MIDI", lambda x: self.test_midi(), icon="midi_output.png",
                       info="Play a MIDI track through the loaded chains."))

        e.append(separator("> AUDIO"))
        e.append(entry(f"PFL Output ({cfg.pfl_output})",
                       lambda x: self.pick("PFL Output", [(v, v) for v in s.pfl_output_labels()], cfg.pfl_output,
                                           s.set_pfl_output),
                       icon="headphones.png", info="The audio output for pre-fader listening."))
        e.append(todo("ZynVoice", "audio_options.png"))
        e.append(entry("Hotplug USB Audio", lambda x: self.hotplug_menu(), icon="audio_options.png",
                       info="Use USB audio devices plugged in at runtime (alsa_in/alsa_out). Not needed with "
                            "PipeWire, which adds them itself."))
        e.append(entry(_check(cfg.snapshot_mixer_settings) + "Audio Levels on Snapshots",
                       toggle(s.toggle_snapshot_mixer_settings), icon="audio_options.png",
                       info="Save and restore the audio levels with snapshots."))
        e.append(entry(_check(cfg.enable_dpm) + "Mixer Peak Meters", toggle(s.toggle_dpm), icon="meters.png",
                       info="Show the peak meters of the chain strips (the main strip always has them)."))
        if self.test_audio_proc and self.test_audio_proc.poll() is None:
            e.append(entry("\u25a0 Stop Test Audio", lambda x: self.stop_test_audio(), icon="audio_test.png",
                           info="Stop the test audio."))
        else:
            e.append(entry("Test Audio", lambda x: self.test_audio(), icon="audio_test.png",
                           enabled=self.audio_test_command() is not None,
                           info="Play an audio file to test the audio output (mplayer or pw-play)."))

        e.append(separator("> USER INTERFACE"))
        vis = cfg.visible_mixer_strips
        e.append(entry(f"Visible Chains ({vis if vis > 0 else 'Auto'})",
                       lambda x: self.pick("Visible chains", [("Auto", 0)] + [(str(v), v) for v in range(4, 17)],
                                           cfg.visible_mixer_strips,
                                           lambda v: (s.set_visible_mixer_strips(v), self.ui.mixer_settings_changed())),
                       icon="settings.png", info="Mixer strips shown at once (others by flicking). Auto: all."))
        e.append(entry(f"Visible Launchers ({cfg.visible_launchers})", icon="settings.png", enabled=False,
                       info="The launcher is not ported yet."))
        e.append(entry(f"Mixer Toggle Control ({cfg.mixer_toggle})",
                       lambda x: self.pick("Toggle Control", [(v, v) for v in s.MIXER_TOGGLES], cfg.mixer_toggle,
                                           lambda v: (s.set_mixer_toggle(v), self.ui.mixer_settings_changed())),
                       icon="settings.png", info="The mixer strips' second button."))
        e.append(entry(_check(self.ui.keypadDocked) + "Docked Touch Keypad", toggle(self.ui.toggleKeypadDocked),
                       icon="settings.png", info="The touch keys beside the screens. Off: an overlay, brought "
                       "up by a tap or swipe down on the top bar (for small screens)."))
        e.append(entry(_check(cfg.preset_preload) + "Preset Preload", toggle(s.toggle_preset_preload),
                       icon="settings.png", info="Load presets when they are selected in the list."))

        e.append(separator("> SYSTEM"))
        e.append(entry("Restart UI", lambda x: self.ui.confirm("Restart the user interface?",
                                                                 lambda: self.ui.exit(102)),
                       icon="settings.png", info="Save the state and restart zynthian."))
        e.append(entry("Exit", lambda x: self.ui.confirm("Exit zynthian?", lambda: self.ui.exit(101)),
                       icon="poweroff.png", info="Save the state and exit zynthian."))
        self.set_entries(e)

    # Hotplug USB audio

    def hotplug_menu(self):
        def run(action, device):
            if action == "tts":
                self.ui.show_info("ZynVoice is not ported yet.")
                return
            zynthian_admin_settings.hotplug_apply(action, device, self.state_manager)
            self.hotplug_menu()

        options = [(label, (lambda a=action, d=device: run(a, d)) if action else None, info, None)
                   for label, action, device, info in zynthian_admin_settings.hotplug_options()]
        self.ui.show_options("Hotplug Audio", options)

    # Tests

    def test_midi(self):
        self.state_manager.toggle_midi_playback(TEST_MIDI)
        self.ui.show_screen("midi_recorder")

    @staticmethod
    def audio_test_command():
        if shutil.which("mplayer"):
            return ["mplayer", "-nogui", "-noconsolecontrols", "-nolirc", "-nojoystick", "-really-quiet",
                    "-ao", "jack", TEST_AUDIO]
        if shutil.which("pw-play"):
            return ["pw-play", TEST_AUDIO]
        return None

    def test_audio(self):
        cmd = self.audio_test_command()
        try:
            self.test_audio_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as ex:
            logging.error(f"Test audio failed => {ex}")
            return
        zynautoconnect.request_audio_connect()
        self.ui.show_info("TEST AUDIO", 3000)
        self.fill()

    def stop_test_audio(self):
        if self.test_audio_proc:
            self.test_audio_proc.terminate()
            self.test_audio_proc = None
        self.fill()
