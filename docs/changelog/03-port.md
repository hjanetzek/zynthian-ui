# Changelog: 03-port, zynthian outside ZynthianOS

What strand 03 of `main` changes, newest entry first: zynthian-ui running on other systems
(desktop Linux, Nura/postmarketOS packages) with configurable directories and PipeWire. The strand
applies directly on origin/tomita. Marker `strand/03-port`; this file is the strand's last commit
(see [README.md](README.md)). The Nura packaging itself is in nura-builds.

## 2026-11-28: rebased onto tomita 046817e4: one conflict in the controller-driver folders commit (autoconnect's imports next to upstream's MainLoopLock); see rebase-onto-tomita-2026-11-28.md

## 2026-11-27: rebased onto tomita 26c42c46: conflicts in the directories, OSC status query and audio2midi engine commits (upstream 9f5a87c3's import and tests, the converter's two channels next to LIB_PATH); see rebase-onto-tomita-2026-11-27b.md

## 2026-11-27: rebased onto tomita 5b0b6966: conflicts in the directories commit (LV2 plugin info cache path) and desktop mode (aubionotes removed upstream), see rebase-onto-tomita-2026-11-27.md

## 2026-11-27: audio2midi (upstream e5ea8288): native library and help page through zynthian_paths; desktop install

- `ba8556fea` audio2midi engine: native library and help page through zynthian_paths; desktop install

## 2026-11-26: rebased onto tomita e2f423d33: no conflicts; see rebase-onto-tomita-2026-11-26.md

## 2026-11-21: Launcher: the configuration sourced per start, so removed settings take effect

- `8c6cd6353` desktop launcher: source the configuration only in each start's subshell

## 2026-11-20: rebased onto tomita 0c1098a68: the admin screen's VNC entry (1723a5ab: vncserver1) conflicted with the desktop-mode guard: kept under the guard; see rebase-onto-tomita-2026-11-20c.md

- `3d226c647` Add desktop mode (ZYNTHIAN_DESKTOP=1)

## 2026-11-20: strand 01's start-failure fixes below: the desktop engine commit keeps only its comment on the failed processor's cleanup

- `7b1a8fff5` Desktop mode: hide engines whose program isn't installed; fix failed processor cleanup

## 2026-11-20: the strand when the changelog started

42 commits on strand 02, written 2026-11-02 to 2026-11-19.

- **Directories from the environment:** `zynthian_paths` and environment variables for every
  directory, native libraries from ZYNTHIAN_LIB_DIR, content packs beside a read-only
  zynthian-data (ZYNTHIAN_PACKS_DATA_DIR), ZynthianOS data paths in snapshots mapped to this
  system's (`f60e50e17`, `95c83ac4e`, `177be5e91`, `28752c143`).
- **Desktop mode** (ZYNTHIAN_DESKTOP=1): no Raspberry Pi hardware, no update_zynthian_sys.sh, no
  RBPi audio device, engines hidden whose program isn't installed, UI scale (ZYNTHIAN_UI_SCALE),
  optional help viewer, no systemctl where there is no systemd (`3d226c647`, `634d917d6`,
  `fee7e4fd5`, `9f9d241f4`, `7b1a8fff5`, `3b7623949`, `568fe9fd4`, `7a8b4e31a`).
- **`desktop/`:** setup, launcher and install script, a uv venv with all Python packages, zynthian's
  jalv fork, websocket-server bundled, the Qt UI with ZYNTHIAN_UI=qt (Tk where the tree has none),
  no processes left after a session restart (`b9a6c8eb6`, `3cdd2e419`, `01256629c`, `8eeb87858`,
  `4888b0b95`, `d5076c353`, `8cae1dbda`, `68e392c10`).
- **PipeWire:** port aliases kept locally when JACK refuses them, all physical audio ports without
  system ports, the main output setting with hardware outputs found by number (`ccf552206`,
  `1de993a90`, `5bd466187`).
- **Engines on read-only data:** Organelle abstractions and pd's system externals found, a writable
  copy of Aeolus' stops, jack_capture from PATH, plugin GUIs on demand with jalv.gtk3 -H
  (ZYNTHIAN_NATIVE_GUI) (`bb623b0e7`, `dea579fbd`, `49546ad0a`, `816e82239`, `1f22b1714`).
- **LV2 widgets:** the built-in widgets' directory from zynthian_paths, zynthian-ui's lv2 bundles on
  LV2_PATH, user and external widgets in $ZYNTHIAN_PLUGINS_DIR/lv2-widgets (`4764cfd66`,
  `5ed0d040f`, `85021cf06`). Docs: [zynthian-widgets.md](../zynthian-widgets.md).
- **OSC status query** /STATUS/BUSY: what zynthian is busy with, for tools (`a276ebba9`,
  `9addf9c7d`). Docs: [osc-interface.md](../osc-interface.md).
