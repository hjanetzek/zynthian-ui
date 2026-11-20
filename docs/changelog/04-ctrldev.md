# Changelog: 04-ctrldev, controller drivers

What strand 04 of `main` changes, newest entry first: where controller drivers come from and how
they connect. Needs strand 03 (zynthian_paths). Marker `strand/04-ctrldev`; this file is the
strand's last commit (see [README.md](README.md)).

## 2026-11-26: rebased onto tomita e2f423d33: no conflicts (upstream's APC40 fix e2f423d3 merges); see rebase-onto-tomita-2026-11-26.md

## 2026-11-26: the DrivenByMoss drivers, moved from drivenbymoss-rust (2026-11-06..25, 51 imported + 7 integration commits squashed; their grid and view parts in strand 08)

- `0c70c0cad` DrivenByMoss drivers: the zynthian adapter, the base driver and the first controllers
- `ff8b6d4d6` docs/dbm: the DrivenByMoss drivers' CPU profile
- `3c98d33ba` DrivenByMoss drivers: Ableton Push 1, 2 and 3
- `efabc68a6` DrivenByMoss drivers: settings for zynthian's UI (get_settings, set_setting, settings_revision)

## 2026-11-20: rebased onto tomita 0c1098a68: no conflict; upstream's SysEx identity autoload (07793ae7) and CC feedback broker (d6d08865) merge with the driver folders and HID drivers (HID drivers have no zmip: no identity requests); see rebase-onto-tomita-2026-11-20c.md

## 2026-11-20: the strand when the changelog started

4 commits on strand 03, written 2026-11-02 to 2026-11-08.

- **Driver folders:** user drivers load without a link in the code tree; drivers from other
  folders through ZYNTHIAN_CTRLDEV_PATH (used for DrivenByMoss); PipeWire MIDI port uids
  (`9b1829d3f`, `63f227e2b`).
- **HID drivers:** loaded without a MIDI port, keeping their device's MIDI ports; the autoconnect
  lock is released when a connect raises (`2d8589800`, `dd24a886f`).
