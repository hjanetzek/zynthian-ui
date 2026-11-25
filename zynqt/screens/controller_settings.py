"""Controller settings (Admin > Controller Settings): the settings of the controller drivers which
have their own (the DrivenByMoss drivers). Three levels in one screen: the drivers, a driver's
categories, a category's settings; BACK goes up a level. The settings come from the shared
zyngui.zynthian_ctrldev_settings_data (docs/controller-settings.md); a setting opens the options
list (enum), the value editor (integer), the keyboard (text), or toggles (boolean) or presses
(signal) at once. While shown, the screen polls the drivers' settings_revision and refills on a
change (the controller's own changes, settings hidden or disabled by it)."""

from PySide6.QtCore import QTimer

from zyngui import zynthian_ctrldev_settings_data as data
from zynqt.screens.base import SelectorScreen, entry

POLL_MS = 250


def _check(flag):
    return "☒ " if flag else "☐ "


class ControllerSettings(SelectorScreen):
    name = "controller_settings"
    default_icon = "midi_settings.png"

    def __init__(self, ui, parent=None):
        super().__init__(ui, parent)
        self.driver = None      # the driver shown, None: the driver list
        self.category = None    # the category shown, None: the category list
        self._poll_key = None
        self._timer = QTimer(self, interval=POLL_MS)
        self._timer.timeout.connect(self.poll)

    # Showing

    def build(self):
        self.fill()
        self._timer.start()

    def hide(self):
        self._timer.stop()

    def drivers(self):
        return data.settings_drivers(getattr(self.state_manager, "ctrldev_manager", None))

    def _state_key(self, drivers):
        """What the entries depend on: the drivers there are and their revisions"""
        return tuple((id(d), data.revision(d)) for d in drivers)

    def poll(self):
        drivers = self.drivers()
        if self._state_key(drivers) != self._poll_key:
            self.fill()

    def fill(self):
        drivers = self.drivers()
        self._poll_key = self._state_key(drivers)
        if self.driver is not None and self.driver not in drivers:
            # Unloaded (unplugged)
            self.driver = self.category = None
        if self.driver is None:
            self._fill_drivers(drivers)
            return
        settings = data.driver_settings(self.driver)
        categories = data.categories(settings)
        if not categories:
            # The controller stopped (asleep, gone)
            self.driver = self.category = None
            self._fill_drivers(drivers)
            return
        if self.category is not None and self.category not in categories:
            # The controller stopped or hid the whole category
            self.category = None
        if self.category is None:
            self._fill_categories(settings, categories)
        else:
            self._fill_settings(settings)

    def _keep_index(self, entries, key):
        """The entry whose data is key (the level we came from), else the index as it was"""
        for i, e in enumerate(entries):
            if key is not None and e["data"] == key:
                return i
        return self._index if 0 <= self._index < len(entries) else None

    def _fill_drivers(self, drivers, select=None):
        self.set_title("Controller Settings")
        entries = []
        for d in drivers:
            settings = data.driver_settings(d)
            shown = [s for s in settings if data.is_shown(s)]
            if shown:
                info = f"{len(shown)} settings in {len(data.categories(settings))} categories."
            else:
                info = "The controller isn't running (not connected, or asleep)."
            entries.append(entry(data.driver_title(d), action=self._open_driver, info=info,
                                 enabled=bool(shown), data=d))
        if not entries:
            entries.append(entry("No controller with settings", enabled=False,
                                 info="No controller driver with settings of its own is loaded."))
        self.set_entries(entries, self._keep_index(entries, select))

    def _fill_categories(self, settings, categories, select=None):
        self.set_title(data.driver_title(self.driver))
        entries = []
        for c in categories:
            labels = [data.label(s) for s in data.category_settings(settings, c)]
            entries.append(entry(c or "Settings", action=self._open_category, data=c,
                                 info="\n".join(labels)))
        self.set_entries(entries, self._keep_index(entries, select))

    def _fill_settings(self, settings):
        # The category alone: with the driver's name it is too long for the title bar
        self.set_title(self.category or "Settings")
        entries = [entry(self._setting_title(s), action=self._edit, info=data.info_text(s),
                         enabled=data.is_enabled(s), data=s["id"])
                   for s in data.category_settings(settings, self.category)]
        self.set_entries(entries, self._index if 0 <= self._index < len(entries) else None)

    @staticmethod
    def _setting_title(s):
        kind = s.get("kind")
        label = data.label(s)
        if kind == "boolean":
            return _check(data.bool_value(s)) + label
        if kind == "signal":
            # A button; its text is in the info ("Press to reset.")
            return f"▶ {label}"
        return f"{label}: {data.value_text(s)}"

    # Levels

    def _open_driver(self, e):
        self.driver, self.category = e["data"], None
        self._index = 0
        self.fill()

    def _open_category(self, e):
        self.category = e["data"]
        self._index = 0
        self.fill()

    def back(self):
        if self.category is not None:
            came_from, self.category = self.category, None
            settings = data.driver_settings(self.driver)
            self._fill_categories(settings, data.categories(settings), came_from)
            return True
        if self.driver is not None:
            came_from, self.driver = self.driver, None
            self._fill_drivers(self.drivers(), came_from)
            return True
        return False

    # Editing

    def _setting(self, setting_id):
        return data.find(data.driver_settings(self.driver), setting_id) if self.driver is not None else None

    def _set(self, setting_id, value):
        s = self._setting(setting_id)
        if s is None or not data.is_enabled(s):
            return
        if not data.apply(self.driver, s, value):
            self.ui.show_info("The controller isn't running.")
        self.fill()

    def _edit(self, e):
        s = self._setting(e["data"])
        if s is None:
            return
        driver, sid, kind, label = self.driver, s["id"], s.get("kind"), data.label(s)
        if kind == "enum":
            options = data.enum_options(s)
            current = s.get("value")
            selected = options.index(current) if current in options else 0
            self.ui.show_options(label, [(_check(o == current) + o, lambda o=o: self._set(sid, o), None, None)
                                         for o in options], selected)
        elif kind == "integer":
            vmin, vmax = data.int_range(s)
            self.ui.edit_value(label, data.int_value(s), vmin, vmax,
                               lambda v: self._set(sid, v) if self.driver is driver else None)
        elif kind == "boolean":
            self._set(sid, not data.bool_value(s))
        elif kind == "text":
            self.ui.show_keyboard(lambda t: self._set(sid, t) if self.driver is driver else None,
                                  str(s.get("value", "")), label)
        elif kind == "signal":
            self._set(sid, "")
            self.ui.show_info(f"{label}: done.")
