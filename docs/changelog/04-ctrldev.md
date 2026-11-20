# Changelog: 04-ctrldev, controller drivers

What strand 04 of `main` changes, newest entry first: where controller drivers come from and how
they connect. Needs strand 03 (zynthian_paths). Marker `strand/04-ctrldev`; this file is the
strand's last commit (see [README.md](README.md)).

## 2026-11-20: rebased onto tomita 0c1098a68: no conflict; upstream's SysEx identity autoload (07793ae7) and CC feedback broker (d6d08865) merge with the driver folders and HID drivers (HID drivers have no zmip: no identity requests); see rebase-onto-tomita-2026-11-20c.md

## 2026-11-20: the strand when the changelog started

4 commits on strand 03, written 2026-11-02 to 2026-11-08.

- **Driver folders:** user drivers load without a link in the code tree; drivers from other
  folders through ZYNTHIAN_CTRLDEV_PATH (used for DrivenByMoss); PipeWire MIDI port uids
  (`a84370bc5`, `1e87bb721`).
- **HID drivers:** loaded without a MIDI port, keeping their device's MIDI ports; the autoconnect
  lock is released when a connect raises (`470276781`, `53bc2a8da`).
