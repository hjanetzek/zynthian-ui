# Controller settings

Some controller drivers have settings of their own: the DrivenByMoss (DBM) drivers bring the
settings of the DBM core (scales, note repeat, transport, workflow, pads, display colours, ...),
the ones Bitwig shows in its controller preferences. The Qt UI shows them in
**Admin > Controller Settings**: the drivers with settings, a driver's categories, a category's
settings.

## Interface between UI and driver

The UI finds the drivers through the ctrldev manager (`state_manager.ctrldev_manager`: `drivers`,
then `hid_drivers`) and takes every driver which has these three (duck-typed, nothing to inherit):

| member | |
| --- | --- |
| `get_settings()` | the settings, a list of dicts; empty while the controller doesn't run. The list belongs to the driver: the UI doesn't change it |
| `set_setting(id, value)` | set a setting; `value` is a str (a signal: any value presses its button). True if the driver took it (False: not running) |
| `settings_revision` | an int which changes whenever the list changes |

A setting:

| key | |
| --- | --- |
| `id` | int |
| `scope` | `"global"` (kept by the controller) or `"document"` (saved with the snapshot) |
| `kind` | `enum`, `integer`, `boolean`, `text`, `signal`, `action` |
| `category`, `label` | its group and name |
| `default`, `value` | str; booleans `"true"` / `"false"` |
| `extra` | an enum's options, an integer's minimum and maximum, a signal's button text |
| `visible` | False: not shown (the controller hides settings without effect, e.g. a Flexi slot's while the slot is off) |
| `enabled` | False: shown greyed, not changeable |

The UI doesn't filter by name: what it shows is what the driver reports as visible.

## Code

- `zyngui/zynthian_ctrldev_settings_data.py`: UI-independent (drivers with settings, categories,
  shown settings, value texts, info texts, the value to set per kind). A Tk screen can use it as
  it is.
- `zynqt/screens/controller_settings.py`: the Qt screen `controller_settings`, a list screen with
  three levels; BACK goes up a level.
  A setting changed (options list, value editor, keyboard, toggle, button) leaves the screen
  where it is: the options list is not part of the screen history (`NO_HISTORY_SCREENS` in
  `zynqt/ui.py`), so closing it always returns to this screen, also when an older options
  list was left by MENU (the pattern editor's options, then the main menu).

| kind | widget |
| --- | --- |
| enum | the options list (`show_options`), the current option checked |
| integer | the value editor (`edit_value`: encoder, arrows or touch) with the setting's min and max |
| boolean | toggles at once (☐ / ☒) |
| text | the on-screen keyboard |
| signal | a button (▶ label, the button text in the info), pressed at once |
| action | not shown yet (it needs a list of host actions to pick from) |

## Threading and polling

The UI calls the interface from the GUI thread. The driver must make that safe. The DBM drivers
(`zynthian_ctrldev_base_dbm.py`, for now in drivenbymoss-rust `backends/zynthian/ctrldev/`) do:
only their tick thread calls into the core, so

- `get_settings()` returns a cached list which the tick thread replaces as a whole;
- `set_setting()` queues the value for the tick thread and updates the cached value at once
  (bumping the revision), so the screen shows the new value without waiting for a tick;
- every tick (30 ms) the tick thread passes the queued values to the core (`App.set_setting`),
  polls `take_setting_changes()` (changes the controller made, e.g. the scale chosen on the JAM)
  and `take_setting_states()` (visible / enabled), reads all settings again after the UI's
  changes (a signal may change others: Push's "Reset colors"), and bumps `settings_revision`
  when the cache changed;
- stopping the controller (sleep, device gone) clears the cache.

While the screen is shown it polls the drivers every 250 ms (a QTimer, stopped when it is hidden)
and refills when the set of drivers or a revision changed. A category the controller hides
entirely, or a controller that stops, takes the screen up to the level that still exists.

## Where settings are kept

- **document** settings are part of the snapshot, as before: the driver's `get_state()` holds the
  core's formatted document settings (`dbm_document`); after a change from the UI the driver reads
  them again at once.
- **global** settings are kept by the core in its per-controller settings file in the drivers'
  config folder; the core owns that file and when it is written (at the latest when the
  controller stops or sleeps).
