# Changelog: 08-dbm, the DrivenByMoss drivers

What strand 08 of `main` changes, newest entry first: the parts of the DrivenByMoss (DBM) drivers
that use zynthian's chain control grid and the Qt UI: the host's parameter pages and the
controller's views on zynthian's screens. The drivers themselves (adapter, base driver,
controllers, settings, `docs/dbm/`) are in strand 04. Without DrivenByMoss (the drivenbymoss
package, or `DBM_PYTHON_DIR` / `DBM_LIBRARY`) they don't load and their tests skip. Needs strands
04 (the drivers), 05 (the chain controller pages, the control grid model) and 07
(PATTERN_EDITOR_WINDOW; guarded). Marker `strand/08-dbm`; this file is the strand's last commit
(see [README.md](README.md)).

## 2026-11-28: DrivenByMoss drivers: zynthian's ZS3s as the host's snapshots (JAM snapshot view, model.zs3_snapshots); the page surface on Select + CONTROL

- `363f0c85b` dbm: zynthian's ZS3s as the host's snapshots (JAM snapshot view)
- `73b46f3fa` dbm: snapshots: model.zs3_snapshots (dbm_host takes a DAW's snapshots as its own); JAM end-to-end test; Select + CONTROL for the page surface

## 2026-11-26: rebased onto tomita e2f423d33: no conflicts; see rebase-onto-tomita-2026-11-26.md

## 2026-11-26: the strand: the DrivenByMoss drivers' grid and view parts, moved from drivenbymoss-rust (2026-11-06..25; the drivers themselves in strand 04)

- `119c4bc56` DrivenByMoss drivers: chain control's grid as the host's pages
- `e0cc64d80` DrivenByMoss drivers: the controller's views on zynthian's screens (ControllerView, ClipEditWindow)
- `1ff9230bd` docs: chain controller pages, control grid, controller settings and DrivenByMoss docs without branch names and local paths
