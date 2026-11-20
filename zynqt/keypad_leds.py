"""The touch keypad's LEDs as zynthian_wsleds_v5 (+ the v5touch emulation) sets them: the colour of
each key by the workflow shown (zynthian_gui.get_current_workflow), ALT, the transport state, and
the screen's own LEDs (the screen's update_wsleds(leds), as in Tk: the pattern editor, the MIDI
recorder in ALT mode, the mixer / launcher in ALT mode). Keys show the LED colour as their label
colour; F1-F4 show F5-F8 while their LED is in the ALT colour (set_button_color's "alt" mode).

It also names what F1-F4 do now (functionLabels): the screen's own action for the key (a screen's
fkey_labels(), e.g. the pattern editor's ALT clipboard, block and CC keys), else the custom
switch's UI action of the wiring configuration (ZYNTHIAN_WIRING_CUSTOM_SWITCH_08/12/16/20, V5:
PROGRAM_CHANGE 1-4, with ALT 5-8), as a short label such as "PROG 1"."""

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


# The F keys: keypad key -> zynswitch (key + 4; the custom switch index is the key)
FN_KEYS = (7, 11, 15, 19)

# Short labels of CUIAs (the others: their words, abbreviated by CUIA_WORDS)
CUIA_LABELS = {
    "PROGRAM_CHANGE": "PROG", "ZS3_LOAD": "ZS3", "ZS3_NEXT": "ZS3 +", "ZS3_PREV": "ZS3 -",
    "ZS3_SAVE": "SAVE ZS3", "ALL_SOUNDS_OFF": "PANIC", "ALL_NOTES_OFF": "NOTES OFF",
    "TOGGLE_ALT_MODE": "ALT", "TAP_TEMPO": "TAP", "TEMPO_UP": "BPM +", "TEMPO_DOWN": "BPM -",
    "SET_TEMPO": "BPM", "TEMPO": "TEMPO", "SCREEN_CHAIN_MANAGER": "CHAINS", "SCREEN_CONTROL": "CTRL",
    "CHAIN_CONTROL": "CTRL", "SCREEN_MIXER": "MIXER", "SCREEN_AUDIO_MIXER": "MIXER",
    "SCREEN_ALSA_MIXER": "ALSA", "SCREEN_ZYNPAD": "PADS", "SCREEN_LAUNCHER": "PADS",
    "SCREEN_PATTERN_EDITOR": "STEP", "SCREEN_SNAPSHOT": "SNAP", "SCREEN_ZS3": "ZS3",
    "SCREEN_MIDI_RECORDER": "MIDI REC", "SCREEN_AUDIO_PLAYER": "PLAYER", "SCREEN_ADMIN": "ADMIN",
    "BANK_PRESET": "PRESET", "PRESET_FAV": "FAVS", "MAIN_MENU": "MENU", "MENU": "MENU",
    "TOGGLE_MIDI_LEARN": "LEARN", "ENABLE_MIDI_LEARN": "LEARN", "TTS_TOGGLE_ENABLE": "TTS",
    "ARROW_UP": "UP", "ARROW_DOWN": "DOWN", "ARROW_LEFT": "LEFT", "ARROW_RIGHT": "RIGHT",
    "V5_ZYNPOT_SWITCH": "KNOB", "ZYNSWITCH": "SW", "ZYN_CC": "CC", "NOP": "",
    "SHOW_SCREEN": "-",   # just its parameter (the screen)
}
CUIA_DROP = ("SCREEN", "TOGGLE")
CUIA_WORDS = {"AUDIO": "AUD", "RECORD": "REC", "RECORDER": "REC", "SNAPSHOT": "SNAP",
              "CONTROL": "CTRL", "OPTIONS": "OPT", "PATTERN": "PAT", "PLAYER": "PLAY",
              "CHAIN": "CHN", "MANAGER": "MGR", "SEQUENCE": "SEQ", "SELECT": "SEL"}
LINE_LEN = 8     # longer labels go on two lines (as "OPT\nADMIN"), at most two of these


def cuia_label(cuia):
    """A short label of a CUIA with its parameters ("PROGRAM_CHANGE 1": "PROG 1"), "" for none;
    over LINE_LEN characters on two lines"""
    if not cuia:
        return ""
    parts = str(cuia).strip().split(" ", 1)
    name = parts[0].upper()
    params = parts[1].replace(",", " ").upper().split() if len(parts) > 1 else []
    if name in CUIA_LABELS:
        words = CUIA_LABELS[name].split()
        if not words:
            return ""
        if words == ["-"]:
            words = []
    else:
        words = [CUIA_WORDS.get(w, w) for w in name.split("_") if w and w not in CUIA_DROP] or [name]
    words = [w[:LINE_LEN] for w in words + params[:2]]
    if not words:
        return ""
    # One line, or two balanced ones
    label = " ".join(words)
    if len(label) <= LINE_LEN or len(words) == 1:
        return label
    best = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        if best is None or max(len(a), len(b)) < max(len(best[0]), len(best[1])):
            best = (a, b)
    return best[0][:LINE_LEN].strip() + "\n" + best[1][:LINE_LEN].strip()


def switch_cuia(config, alt):
    """The CUIA a custom switch's press does (wiring configuration, as zynqt.ui.cuia__zynswitch):
    its push action, else its short one, else its bold one; ALT's own if set"""
    if not config:
        return ""
    for t in ("P", "S", "B"):
        cuia = (alt and config.get("A" + t)) or config.get(t)
        if cuia:
            return cuia
    return ""


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
        self._lit = [False] * 20
        self._fn = [""] * 20
        # The websocket's "wsled_state" (zynthian_wsleds_base.update): the LED colours by LED
        # index as letters, while websocket clients are connected
        self.wscolors_dict = {str(self.wscolor_off): "0", str(self.wscolor_blue): "B", str(self.wscolor_green): "G",
                              str(self.wscolor_red): "R", str(self.wscolor_orange): "O",
                              str(self.wscolor_yellow): "Y", str(self.wscolor_purple): "P"}
        self.last_wsled_state = ""
        self.wsled_state_changed = False
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
        lit = [False] * 20
        for i, c in enumerate(w):
            colors[LED2BUTTON[i]] = c
            alts[LED2BUTTON[i]] = c == self.wscolor_alt
            lit[LED2BUTTON[i]] = c not in (self.wscolor_default, self.wscolor_off)
        if getattr(ui, "websocket_clients", None):
            state = ",".join(self.wscolors_dict.get(str(c), "0") for c in w)
            if state != self.last_wsled_state:
                self.last_wsled_state = state
                self.wsled_state_changed = True
        fn = self._function_labels(screen, cur, alt)
        if colors != self._colors or alts != self._alt or fn != self._fn:
            self._colors = colors
            self._alt = alts
            self._lit = lit
            self._fn = fn
            self.changed.emit()

    def _function_labels(self, screen, cur, alt):
        """What F1-F4 do now (by key index): the screen's own actions (fkey_labels() {switch:
        label}, as its switch() takes the keys first, not under a dialog), else the wiring
        configuration's custom switch action. MIDI custom switches: nothing (the touch keys only
        send switch CUIAs)"""
        labels = [""] * 20
        own = {}
        func = getattr(screen, "fkey_labels", None)
        overlay = getattr(self.ui, "_overlay_shown", None)
        if callable(func) and not (callable(overlay) and overlay()):
            try:
                own = func() or {}
            except Exception:
                own = {}
        actions = zynthian_gui_config.custom_switch_ui_actions
        for key in FN_KEYS:
            if key + 4 in own:
                labels[key] = own[key + 4] or ""
                continue
            config = actions[key] if key < len(actions) else None
            cuia = switch_cuia(config, alt)
            # Short press on the shown screen's key: its bold action (zynthian_gui)
            short = (config or {}).get("S") or ""
            if cuia == short and short and cur and (short.lower().endswith(cur)
                                                     or (short.lower() == "menu" and cur == "main_menu")):
                cuia = config.get("B") or cuia
            labels[key] = cuia_label(cuia)
        return labels

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
    def lit(self):
        """Keys whose LED shows a state (not the default colour, not off): the workflow's key,
        ALT, the transport, the screen's own LEDs, the arrows, SEL and BACK. Themes that don't
        colour their labels with the LED (classic) show these as a light on the key"""
        return self._lit

    @Property("QVariantList", notify=changed)
    def functionLabels(self):
        """What each F key (7, 11, 15, 19) does now, as a short label ("PROG 1"; with ALT the F5-F8
        functions), "" for none; the other keys ""."""
        return self._fn

    @Property("QVariantList", notify=changed)
    def altLabels(self):
        """Keys showing their ALT label (F1-F4: F5-F8)"""
        return self._alt
