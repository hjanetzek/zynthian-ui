"""A controller driver with settings (docs/controller-settings.md) for the settings screens' tests:
the settings of DrivenByMoss's Push 2 and Maschine JAM as their cores list them (abridged, the
kinds and categories as in the cores' dumps), plus a boolean and a setting hidden by the
controller, as a Flexi slot's are while the slot is off."""

ENUM_ON_OFF = ["Off", "On"]

PUSH2 = [
    # (scope, kind, category, label, default/value, extra)
    ("document", "enum", "Scales", "Scale", "Major", ["Major", "Minor", "Dorian", "Mixolydian"]),
    ("document", "enum", "Scales", "Base", "C", ["C", "G", "D", "A", "E", "B", "F", "Bb", "Eb", "Ab", "Db", "Gb"]),
    ("document", "enum", "Scales", "In Key", "In Key", ["In Key", "Chromatic"]),
    ("document", "enum", "Note Repeat", "Active", "Off", ENUM_ON_OFF),
    ("document", "enum", "Note Repeat", "Period", "1/16", ["1/4", "1/8", "1/16", "1/32"]),
    ("global", "enum", "Session", "Pads", "Clips", ["Clips", "Scenes"]),
    ("global", "enum", "Transport", "Behaviour on Pause", "Pause", ["Pause", "Stop", "Return to Zero"]),
    ("global", "integer", "Play and Sequence", "Fixed Accent Value", "127", ["1", "127"]),
    ("global", "integer", "Play and Sequence", "Quantize Amount", "100", ["1", "100"]),
    ("document", "enum", "Play and Sequence", "MIDI Edit/Insert note channel", "1", [str(c) for c in range(1, 17)]),
    ("global", "enum", "Workflow", "Exclude deactivated items (tracks, sends, devices, layers)", "Off", ENUM_ON_OFF),
    ("global", "enum", "Workflow", "New Clip Length", "1 Bar", ["1 Beat", "2 Beats", "1 Bar", "2 Bars", "4 Bars"]),
    ("global", "integer", "Pads", "Sensitivity", "5", ["0", "10"]),
    ("global", "integer", "Hardware Setup", "Display Brightness", "100", ["0", "100"]),
    ("global", "signal", "Display Colors", "Reset colors to default", "", ["Reset"]),
    ("global", "text", "Display Colors", "Background", "#535353", []),
    ("global", "text", "Display Colors", "Text", "#000000", []),
    ("global", "action", "Debug", "Display Mode", "", []),
    ("global", "boolean", "Flexi", "Slot 1 Active", "false", []),
    ("global", "enum", "Flexi", "Slot 1 Command", "Off", ["Off", "Play", "Stop"]),
]

JAM = [
    ("document", "enum", "Scales", "Scale", "Major", ["Major", "Minor"]),
    ("global", "enum", "Hardware Setup", "LED Brightness", "Normal", ["Dim", "Normal", "Bright"]),
]


def settings_list(rows):
    return [{"id": i, "scope": scope, "kind": kind, "category": category, "label": label, "default": value,
             "value": value, "extra": list(extra), "visible": True, "enabled": True}
            for i, (scope, kind, category, label, value, extra) in enumerate(rows)]


class FakeSettingsDriver:
    """The settings interface of a driver: get_settings, set_setting, settings_revision. The
    Flexi slot's command is hidden while the slot is off (the controller's state)."""

    def __init__(self, name, rows, running=True):
        self.name = name
        self.settings = settings_list(rows)
        self.settings_revision = 0
        self.running = running
        self.calls = []
        self._flexi()

    def get_driver_name(self):
        return self.name

    def get_settings(self):
        return self.settings if self.running else []

    def set_setting(self, setting_id, value):
        self.calls.append((setting_id, value))
        if not self.running:
            return False
        s = next(s for s in self.settings if s["id"] == setting_id)
        if s["kind"] == "signal":
            for t in self.settings:
                if t["kind"] == "text":
                    t["value"] = t["default"]
        else:
            s["value"] = value
        self._flexi()
        self.settings_revision += 1
        return True

    def controller_changes(self, label, value):
        """A change made on the controller (take_setting_changes)"""
        next(s for s in self.settings if s["label"] == label)["value"] = value
        self.settings_revision += 1

    def set_state(self, label, visible=True, enabled=True):
        """A state change of the controller (take_setting_states)"""
        s = next(s for s in self.settings if s["label"] == label)
        s["visible"], s["enabled"] = visible, enabled
        self.settings_revision += 1

    def _flexi(self):
        active = next((s for s in self.settings if s["label"] == "Slot 1 Active"), None)
        command = next((s for s in self.settings if s["label"] == "Slot 1 Command"), None)
        if active and command:
            command["visible"] = active["value"] == "true"


class FakeCtrldevManager:
    def __init__(self, drivers=(), hid_drivers=()):
        self.drivers = {i: d for i, d in enumerate(drivers)}
        self.hid_drivers = {f"HID:{i}": d for i, d in enumerate(hid_drivers)}
