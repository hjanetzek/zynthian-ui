"""Screen names: the Tk UI's (zynthian_gui.screens keys) and the Qt UI's (ZynUI QML_SCREENS and
list_screens).

Shared code, controller drivers, CUIAs (SHOW_SCREEN) and injected scripts use the Tk names; the Qt
UI accepts them (qt_name) and announces its screens under the Tk name (tk_name) with zynsigman's
SS_GUI_SHOW_SCREEN, as zynthian_gui.show_screen does, so the drivers see the screens they know.

Most names are the same in both UIs. The differences:

  Tk name                Qt screen
  control                chain_control (or tempo / alsa_mixer / audio_player when that special
                         processor is the current one: Tk's "control" screen shows it then)
  root                   mixer or launcher, whichever was shown last (Tk: the mixer in its mode)
  zynpad, arranger       launcher (both gone from Tk on tomita: the mixer's launcher mode)
  pated, pated_cc        pattern_editor (pated_cc: Qt's pattern editor in CC mode)
  midi_config            midi_in (chain MIDI input); Qt's midi_out, midi_devices_in and
                         midi_devices_out are all Tk's midi_config (its chain and input flag)

Tk sends the key it was asked for, so the special processor screens go out as "tempo",
"alsa_mixer" and "audio_player" (zynthian_gui.chain_control sends "control" for them instead;
Qt doesn't distinguish the two ways).

Tk screens the Qt UI doesn't have as screens: none, splash, loading, info (Qt: the info box);
help, confirm, keyboard (Qt: overlays; Tk doesn't announce confirm and keyboard either);
midi_cc_range, midi_cc_single, midi_prog, zs3_options, grid_sel, wifi, bluetooth, midi_profile,
brightness_config, touchscreen_calibration, control_test, tts, cv_config.
"""

# Qt screen -> Tk name, where they differ
QT_TO_TK = {
    "midi_in": "midi_config",
    "midi_out": "midi_config",
    "midi_devices_in": "midi_config",
    "midi_devices_out": "midi_config",
}

# Tk name -> Qt screen, where they differ (control and root depend on the state: qt_name)
TK_TO_QT = {
    "control": "chain_control",
    "root": "mixer",
    "zynpad": "launcher",
    "arranger": "launcher",
    "pated": "pattern_editor",
    "pated_cc": "pattern_editor",
    "midi_config": "midi_in",
}

# Tk screens without a Qt screen
TK_ONLY = ("none", "splash", "loading", "info", "help", "confirm", "keyboard", "midi_cc_range",
           "midi_cc_single", "midi_prog", "zs3_options", "grid_sel", "wifi", "bluetooth", "midi_profile",
           "brightness_config", "touchscreen_calibration", "control_test", "tts", "cv_config")


def tk_name(qt_screen, pattern_cc=False):
    """The Tk name of Qt screen qt_screen; pattern_cc: the pattern editor shows CCs"""
    if qt_screen == "pattern_editor" and pattern_cc:
        return "pated_cc"
    return QT_TO_TK.get(qt_screen, qt_screen)


def qt_name(name, last_root="mixer", special=None):
    """The Qt screen for name (a Tk or Qt name). last_root: the root screen shown last (mixer or
    launcher); special: the name of the special processor screen ("tempo", "alsa_mixer",
    "audio_player") whose processor is the current one, else None"""
    if name == "root":
        return last_root
    if name == "control" and special:
        return special
    return TK_TO_QT.get(name, name)
