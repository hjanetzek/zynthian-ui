"""The touch keypad's LEDs as zynthian_wsleds_v5 (+ the v5touch emulation) sets them: the colour of
each key by the workflow shown (zynthian_gui.get_current_workflow), ALT, the transport state, and
the screen's own LEDs (the screen's update_wsleds(leds), as in Tk: the pattern editor, the MIDI
recorder in ALT mode, the mixer / launcher in ALT mode). Keys show the LED colour as their label
colour; F1-F4 show F5-F8 while their LED is in the ALT colour (set_button_color's "alt" mode)."""

import os

from PySide6.QtCore import QObject, QTimer, Property, Signal

from zyngui import zynthian_gui_config

# LED index -> keypad key (zynthian_wsleds_v5touch.LED2BUTTON)
LED2BUTTON = [0, 1, 2, 3, 7, 6, 5, 4, 8, 9, 10, 11, 15, 14, 13, 12, 16, 17, 18, 19]

# Workflows (zynthian_gui.get_current_workflow): base screens, the screens allowed after them
WORKFLOWS = {
    "menu": (("main_menu", "grid_sel"), ()),
    "add_chain": (("add_chain",), ("engine", "midi_chan")),
    "chain_manager": (("chain_manager",), ("chain_options", "midi_chan", "midi_cc", "midi_key_range", "midi_config",
                                           "midi_in", "midi_out", "processor_options", "audio_in", "audio_out")),
    "admin": (("admin",), ("wifi", "bluetooth", "brightness_config", "touchscreen_calibration", "cv_config")),
    "bank_preset": (("bank", "preset"), ()),
    "chain_control": (("chain_control",), ("processor_options", "file_selector", "midi_cc_range", "midi_cc_single")),
    "audio_player": (("audio_player",), ("midi_cc_range", "midi_cc_single")),
    "alsa_mixer": (("alsa_mixer",), ("midi_cc_range", "midi_cc_single")),
    "tempo": (("tempo",), ("midi_cc_range", "midi_cc_single")),
    "pated": (("pattern_editor", "pated_cc"), ("midi_prog",)),
    "snapshot": (("snapshot",), ()),
    "zs3": (("zs3",), ()),
}


def current_workflow(history, current):
    """The workflow of the screen shown: the last base screen in the history, if every screen
    after it is one of its allowed screens"""
    sh = list(history) + [current]
    for i in range(len(sh) - 1, -1, -1):
        for wf, (base, allowed) in WORKFLOWS.items():
            if sh[i] in base:
                sub = ("option", "confirm", "keyboard") + allowed
                return wf if all(s in sub for s in sh[i + 1:]) else None
    return None


def _env(name, default):
    return os.environ.get(f"ZYNTHIAN_TOUCH_KEYPAD_COLOR_{name}", default)


class KeypadLeds(QObject):
    changed = Signal()

    def __init__(self, ui, parent=None):
        super().__init__(parent)
        self.ui = ui
        # zynthian_wsleds_v5touch.setup_colors
        self.wscolor_off = _env("OFF", zynthian_gui_config.color_bg)
        self.wscolor_red = _env("RED", "#FE2C2F")
        self.wscolor_green = _env("GREEN", "#00FA00")
        self.wscolor_yellow = _env("YELLOW", "#F0EA00")
        self.wscolor_orange = _env("ORANGE", "#FF6A00")
        self.wscolor_blue = _env("BLUE", "#1070FE")
        self.wscolor_purple = _env("PURPLE", "#D000E0")
        self.wscolor_default = _env("DEFAULT", self.wscolor_blue)
        self.wscolor_alt = _env("ALT", self.wscolor_purple)
        self.wscolor_active = _env("ACTIVE", self.wscolor_green)
        self.wscolor_active2 = _env("ACTIVE2", self.wscolor_orange)
        # The per-screen LEDs (zynthian_wsleds_v5.custom_wsleds)
        self.custom_wsleds = [7, 8, 9, 10, 14, 16, 17, 18, 15, 13, 4, 11, 12, 19, None, 2]
        self.wsleds = [self.wscolor_default] * 20
        self.blink_state = False
        self._blink_count = 0
        self._colors = [self.wscolor_default] * 20
        self._alt = [False] * 20
        self._timer = QTimer(self, interval=100)
        self._timer.timeout.connect(self._update)
        self._timer.start()

    # The API the screens' update_wsleds(leds) use (zynthian_wsleds_base)

    def set_led(self, i, color):
        if i is not None and 0 <= i < 20:
            self.wsleds[i] = color

    def blink(self, i, color):
        self.set_led(i, color if self.blink_state else self.wscolor_off)

    def _update(self):
        try:
            self.update()
        except Exception:
            pass   # before the start finished (no state manager parts yet)

    def update(self):
        self._blink_count = (self._blink_count + 1) % 5
        if self._blink_count == 0:
            self.blink_state = not self.blink_state
        ui = self.ui
        sm = ui.state_manager
        cur = ui.current_screen
        wf = current_workflow(ui.screen_history, cur)
        alt = bool(ui.alt_mode)
        w = self.wsleds
        default = self.wscolor_default
        w[0] = self.wscolor_active2 if wf == "admin" else (self.wscolor_active if wf in ("menu", "chain_manager")
                                                            else default)
        w[1] = self.wscolor_active2 if wf == "alsa_mixer" else (self.wscolor_active if cur == "mixer" else default)
        w[2] = self.wscolor_active2 if wf == "bank_preset" else (
            self.wscolor_active if wf in ("chain_control", "audio_player") else default)
        w[3] = self.wscolor_active2 if wf == "snapshot" else (self.wscolor_active if wf == "zs3" else default)
        w[5] = self.wscolor_active2 if wf == "pated" else (self.wscolor_active if cur == "launcher" else default)
        # Tempo LED (no beat blinking: the metronome LED shows the tempo screen)
        w[6] = self.wscolor_active if wf == "tempo" else default
        w[7] = self.wscolor_alt if alt else default
        if alt and cur != "midi_recorder":
            self._midi_recorder_leds()
        else:
            try:
                w[8] = self.wscolor_red if sm.audio_recorder.rec_proc else default
            except AttributeError:
                w[8] = default
            w[9] = default
            w[10] = self.wscolor_green if sm.status_audio_player else default
        w[13] = self.wscolor_green
        w[15] = self.wscolor_red
        for i in (14, 16, 17, 18):
            w[i] = self.wscolor_yellow
        fx = self.wscolor_alt if alt else default
        for i in (4, 11, 12, 19):
            w[i] = fx
        screen = ui._screen_obj(cur) if cur else None
        func = getattr(screen, "update_wsleds", None)
        if callable(func):
            try:
                func(self.custom_wsleds)
            except Exception:
                pass
        if cur == "midi_recorder" and not callable(func):
            self._midi_recorder_leds()
        colors = [self.wscolor_default] * 20
        alts = [False] * 20
        for i, c in enumerate(w):
            colors[LED2BUTTON[i]] = c
            alts[LED2BUTTON[i]] = c == self.wscolor_alt
        if colors != self._colors or alts != self._alt:
            self._colors = colors
            self._alt = alts
            self.changed.emit()

    def _midi_recorder_leds(self):
        """zynthian_gui_midi_recorder.update_wsleds: the transport keys for the MIDI recorder"""
        sm = self.ui.state_manager
        leds = self.custom_wsleds
        self.set_led(leds[1], self.wscolor_red if sm.status_midi_recorder else self.wscolor_alt)
        self.set_led(leds[2], self.wscolor_alt)
        self.set_led(leds[3], self.wscolor_green if sm.status_midi_player else self.wscolor_alt)

    @Property("QVariantList", notify=changed)
    def colors(self):
        """The LED colour of each key (by key index)"""
        return self._colors

    @Property("QVariantList", notify=changed)
    def altLabels(self):
        """Keys showing their ALT label (F1-F4: F5-F8)"""
        return self._alt
