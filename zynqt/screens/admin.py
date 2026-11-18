"""Admin menu (zynthian_gui_admin), the entries available in desktop mode. The settings are shared
with the Tk UI (zyngui.zynthian_admin_settings); values are picked from an options list (Tk's
param editor)."""

import logging
import os
import shutil
import subprocess

import zynautoconnect
from zyncoder.zyncore import lib_zyncore
from zyngui import zynthian_admin_settings, zynthian_gui_config as cfg
import zynconf
from zynconf import zynthian_paths
from zynqt import theme as zyntheme
from zynqt.screens.base import NOT_PORTED, SelectorScreen, entry, separator

TEST_AUDIO = f"{zynthian_paths.data_dir}/files/Audio/Oya.mp3"
TEST_MIDI = f"{zynthian_paths.data_dir}/files/Midi/roland_take5.mid"
QML_DIR = os.path.join(os.path.dirname(os.path.abspath(zyntheme.__file__)), "qml")


def _check(flag):
    return "☒ " if flag else "☐ "


def _signed(value):
    return f"+{value}" if value > 0 else str(value)


class Admin(SelectorScreen):
    name = "admin"
    default_icon = "zynthian_logo.png"   # Tk's selector_info default

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
                           info="MIDI Program Change messages can be used for learning/recalling ZS3s (subsnapshots) or for changing processor presets."))
        else:
            e.append(entry("Program Change => Processor Presets", toggle(s.toggle_prog_change_zs3),
                           icon="midi_settings.png",
                           info="MIDI Program Change messages can be used for learning/recalling ZS3s (subsnapshots) or for changing processor presets."))
            e.append(entry(_check(cfg.midi_bank_change) + "MIDI Bank Change", toggle(s.toggle_bank_change),
                           icon="midi_settings.png", info=("Select bank when MIDI Program Change received" if cfg.midi_bank_change
                                 else "Don't select bank when MIDI Program Change received")))
        gtrans = lib_zyncore.get_global_transpose()
        e.append(entry(f"Global Transpose ({_signed(gtrans) if gtrans else 'None'})",
                       lambda x: self.pick("Global Transpose", [(_signed(v), v) for v in range(-24, 25)],
                                           lib_zyncore.get_global_transpose(), lib_zyncore.set_global_transpose),
                       icon="midi_settings.png",
                       info="MIDI note transpose.\nThis effects all MIDI messages and is in addition to individual chain transpose."))
        e.append(entry(_check(lib_zyncore.get_active_midi_chan()) + "Active MIDI channel",
                       toggle(s.toggle_active_midi_channel), icon="midi_settings.png",
                       info="Send active MIDI channel messages to all chains with the same MIDI channel. When disabled, only "
                            "active chain receives."))
        e.append(entry(_check(cfg.midi_usb_by_port) + "MIDI-USB mapped by port", toggle(s.toggle_usbmidi_by_port),
                       icon="midi_settings.png", info=("MIDI ports are indexed by their device name and the physical USB port to which they are plugged"
                             if cfg.midi_usb_by_port else "MIDI ports are indexed by their device name only.")))
        e.append(entry(f"Channel Pressure => CC ({cfg.midi_chanpress_cc or 'NONE'})",
                       lambda x: self.pick("Channel Pressure => CC",
                                           [("NONE", 0)] + [(f"CC {v}", v) for v in range(1, 120)],
                                           cfg.midi_chanpress_cc or 0,
                                           lambda v: s.set_chanpress_cc(v, self.state_manager)),
                       icon="midi_settings.png", info="Map channel pressure messages (monoAT) to the selected CC."))
        e.append(entry("Test MIDI", lambda x: self.test_midi(), icon="midi_output.png",
                       info="Play a MIDI track to test MIDI output.\n\nThis will play the MIDI through any loaded chains."))

        e.append(separator("> AUDIO"))
        e.append(entry(f"Main Output ({s.main_output_label()})",
                       lambda x: self.pick("Main Output", s.main_output_choices(), cfg.main_output,
                                           s.set_main_output),
                       icon="audio_output.png", info="The hardware outputs of the main mix (chains routed to "
                       "\"Main output\"). Default: the first two."))
        e.append(entry(f"PFL Output ({cfg.pfl_output})",
                       lambda x: self.pick("PFL Output", [(v, v) for v in s.pfl_output_labels()], cfg.pfl_output,
                                           s.set_pfl_output),
                       icon="headphones.png", info="Select the audio output device for pre-fader listening."))
        e.append(todo("ZynVoice", "audio_options.png"))
        e.append(entry("Hotplug USB Audio", lambda x: self.hotplug_menu(), icon="audio_options.png",
                       info="Use USB audio devices plugged in at runtime (alsa_in/alsa_out). Not needed with "
                            "PipeWire, which adds them itself."))
        e.append(entry(_check(cfg.snapshot_mixer_settings) + "Audio Levels on Snapshots",
                       toggle(s.toggle_snapshot_mixer_settings), icon="meter.png",
                       info="Soundcard parameters are saved with snapshot" if cfg.snapshot_mixer_settings
                       else "Soundcard parameters are not saved with snapshot"))
        e.append(entry(_check(cfg.enable_dpm) + "Mixer Peak Meters", toggle(s.toggle_dpm), icon="meters.png",
                       info="Peak programme meters are enabled." if cfg.enable_dpm
                       else "Peak programme meters are disabled.\nThis saves a little CPU power."))
        if self.test_audio_proc and self.test_audio_proc.poll() is None:
            e.append(entry("\u25a0 Stop Test Audio", lambda x: self.stop_test_audio(), icon="audio_test.png",
                           info="Stop the test audio."))
        else:
            e.append(entry("Test Audio", lambda x: self.test_audio(), icon="audio_output.png",
                           enabled=self.audio_test_command() is not None,
                           info="Play an audio track to test audio output.\n\nPress BACK to cancel playback."))

        e.append(separator("> USER INTERFACE"))
        vis = cfg.visible_mixer_strips
        e.append(entry(f"Visible Chains ({vis if vis > 0 else 'Auto'})",
                       lambda x: self.pick("Visible chains", [("Auto", 0)] + [(str(v), v) for v in range(4, 17)],
                                           cfg.visible_mixer_strips,
                                           lambda v: (s.set_visible_mixer_strips(v), self.ui.mixer_settings_changed())),
                       icon="settings.png", info="Quantity of chains shown in mixer"))
        e.append(entry(f"Visible Launchers ({cfg.visible_launchers})",
                       lambda x: self.pick("Visible launchers", [(str(v), v) for v in range(1, 17)],
                                           cfg.visible_launchers, self.set_visible_launchers),
                       icon="settings.png", info="Quantity of launchers shown in mixer"))
        e.append(entry(f"Mixer Toggle Control ({cfg.mixer_toggle})",
                       lambda x: self.pick("Toggle Control", [(v, v) for v in s.MIXER_TOGGLES], cfg.mixer_toggle,
                                           lambda v: (s.set_mixer_toggle(v), self.ui.mixer_settings_changed())),
                       icon="settings.png", info="The toggle control to show at top of each mixer channel"))
        e.append(entry(_check(self.ui.keypadDocked) + "Docked Touch Keypad", toggle(self.ui.toggleKeypadDocked),
                       icon="settings.png", info="The touch keys beside the screens (phones, touch-only devices). Also "
                       "shown / hidden by a tap on the top bar's status area."))
        e.append(entry(_check(cfg.preset_preload) + "Preset Preload", toggle(s.toggle_preset_preload),
                       icon="settings.png", info="Pre-load presets while browsing the list" if cfg.preset_preload
                       else "Do not pre-load preset for while browsing the list"))

        nav = {"v5_keypad_left": "V5 keypad at Left", "v5_keypad_right": "V5 keypad at right"}.get(
            cfg.touch_navigation, "None")
        e.append(entry(f"Touch Navigation: {nav}", lambda x: self.touch_navigation_menu(), icon="settings.png",
                       info="Enable touch-screen V5 buttons."))

        e.append(separator("> SCREEN"))
        e.append(entry(f"Theme ({self.running_theme()})", lambda x: self.theme_menu(), icon="settings.png",
                       info="The look of the user interface. Saved for the next start."))
        e.append(entry("Calibrate Touchscreen", lambda x: self.ui.cuia_screen_calibrate(), icon="settings.png",
                       info="Show touchscreen calibration.\nTouch each crosshair until it changes color.\n"
                            "Screen closes after 15s of inactivity."))
        e.append(entry("Clean Screen", lambda x: self.ui.cuia_screen_clean(), icon="settings.png",
                       info="10s countdown with no touch trigger. Allows screen to be cleaned without "
                            "triggering any action."))

        e.append(separator("> SYSTEM"))
        e.append(entry("Restart UI", lambda x: self.ui.confirm("Restart the user interface?",
                                                                 lambda: self.ui.exit(102)),
                       icon="settings.png", info="Save the state and restart zynthian."))
        e.append(entry("Exit", lambda x: self.ui.confirm("Exit zynthian?", lambda: self.ui.exit(101)),
                       icon="poweroff.png", info="Stop zynthian UI but do not reboot."))
        # The selection stays where it was (Tk's selector keeps its index)
        self.set_entries(e, self._index if 0 < self._index < len(e) else None)

    def set_visible_launchers(self, value):
        zynthian_admin_settings.set_visible_launchers(value)
        self.ui.launcher.padsChanged.emit()

    def touch_navigation_menu(self):
        """zynthian_gui_admin.touch_navigation_menu: None / keypad left / right, then restart"""
        def apply(value):
            if value != cfg.touch_navigation:
                def do():
                    zynconf.save_config({"ZYNTHIAN_UI_TOUCH_NAVIGATION": value})
                    self.ui.exit(102)
                self.ui.confirm("Restart UI to apply touch-navigation settings?", do)
        self.pick("Touch Navigation", [("None", ""), ("V5 keypad at left", "v5_keypad_left"),
                                       ("V5 keypad at right", "v5_keypad_right")], cfg.touch_navigation, apply)

    # Theme (ZYNTHIAN_QT_THEME, zynqt/theme.py)

    def running_theme(self):
        return getattr(self.ui, "theme_name", None) or os.environ.get(zyntheme.VAR) or zyntheme.DEFAULT

    def theme_menu(self):
        """The themes there are (zynqt/qml/+<name>/), the user's choice marked, and Default (no
        choice: the session's or kit's theme); a change is saved and applied at once (the QML is
        loaded again, zynthian keeps running)"""
        chosen = zyntheme.user_theme()
        system = zyntheme.session_theme()
        session = system or zyntheme.DEFAULT
        running = self.running_theme()
        where = "the custom config" if zyntheme.custom_config_sets_theme() else "zynthian's config"

        def label(text, value):
            return _check(value == chosen) + text

        def info(value):
            if not value:
                if system:
                    return f"No theme of your own: the system's, {system} (/etc/default/zynthian, set by the kit)."
                return f"No theme of your own: the default, {session}."
            text = zyntheme.DESCRIPTIONS.get(value, f"The theme in zynqt/qml/+{value}/.")
            return text + f"\n\nSaved in {where}." + ("\n(running now)" if value == running else "")

        def apply(value):
            if value == chosen:
                return
            name = value or f"default ({session})"

            def do():
                try:
                    zyntheme.save_theme(value)
                except Exception as err:
                    logging.error(f"Can't save the theme => {err}")
                    self.ui.show_info(f"Can't save the theme: {err}")
                    return
                # then "Theme (<new>)"
                self.ui.switch_theme(value or zyntheme.session_theme(), self.fill)
            self.ui.confirm(f"Switch to theme {name}?", do)

        choices = [("", f"Default ({session})")] + [(t, t) for t in zyntheme.available_themes(QML_DIR)]
        selected = next((i for i, (v, _) in enumerate(choices) if v == chosen), 0)
        self.ui.show_options("Theme", [(label(text, v), lambda v=v: apply(v), info(v), None)
                                       for v, text in choices], selected)

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
