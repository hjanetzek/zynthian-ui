"""Battery state for the top bar, from /sys/class/power_supply: the system's battery (not those
of peripherals: scope "Device", HID devices) and whether external power is connected."""

import os

POWER_SUPPLY = os.environ.get("ZYNTHIAN_POWER_SUPPLY_DIR", "/sys/class/power_supply")   # override: tests


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ""


def battery_status():
    """(percent, on_external_power) of the system battery, or None if there is none"""
    try:
        names = sorted(os.listdir(POWER_SUPPLY))
    except OSError:
        return None
    percent = None
    charging = False
    external = False
    for name in names:
        d = os.path.join(POWER_SUPPLY, name)
        kind = _read(f"{d}/type")
        if kind == "Battery":
            if _read(f"{d}/scope") == "Device" or name.startswith("hid-") or percent is not None:
                continue
            capacity = _read(f"{d}/capacity")
            if capacity.isdigit():
                percent = int(capacity)
                charging = _read(f"{d}/status") in ("Charging", "Full", "Not charging")
        elif _read(f"{d}/online") == "1":
            external = True   # Mains, USB, USB-PD charger
    if percent is None:
        return None
    return percent, external or charging
