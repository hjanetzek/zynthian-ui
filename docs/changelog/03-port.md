# Changelog: 03-port, zynthian outside ZynthianOS

What strand 03 of `main` changes, newest entry first: zynthian-ui running on other systems
(desktop Linux, Nura/postmarketOS packages) with configurable directories and PipeWire. The strand
applies directly on origin/tomita. Marker `strand/03-port`; this file is the strand's last commit
(see [README.md](README.md)). The Nura packaging itself is in nura-builds.

## 2026-11-20: rebased onto tomita 0c1098a68: the admin screen's VNC entry (1723a5ab: vncserver1) conflicted with the desktop-mode guard: kept under the guard; see rebase-onto-tomita-2026-11-20c.md

- `87ed0cc4c` Add desktop mode (ZYNTHIAN_DESKTOP=1)

## 2026-11-20: strand 01's start-failure fixes below: the desktop engine commit keeps only its comment on the failed processor's cleanup

- `8d1ea82fe` Desktop mode: hide engines whose program isn't installed; fix failed processor cleanup

## 2026-11-20: the strand when the changelog started

42 commits on strand 02, written 2026-11-02 to 2026-11-19.

- **Directories from the environment:** `zynthian_paths` and environment variables for every
  directory, native libraries from ZYNTHIAN_LIB_DIR, content packs beside a read-only
  zynthian-data (ZYNTHIAN_PACKS_DATA_DIR), ZynthianOS data paths in snapshots mapped to this
  system's (`cf986dac6`, `67e568619`, `45bf9d8db`, `5ae13777e`).
- **Desktop mode** (ZYNTHIAN_DESKTOP=1): no Raspberry Pi hardware, no update_zynthian_sys.sh, no
  RBPi audio device, engines hidden whose program isn't installed, UI scale (ZYNTHIAN_UI_SCALE),
  optional help viewer, no systemctl where there is no systemd (`87ed0cc4c`, `9b2d6cd21`,
  `ed7de63f3`, `882ba6d67`, `8d1ea82fe`, `b90e9dfd5`, `ae9b8c52f`, `104e9163d`).
- **`desktop/`:** setup, launcher and install script, a uv venv with all Python packages, zynthian's
  jalv fork, websocket-server bundled, the Qt UI with ZYNTHIAN_UI=qt (Tk where the tree has none),
  no processes left after a session restart (`d935b6595`, `02e65dccc`, `441f21305`, `a00e667bc`,
  `16fcdd0d7`, `2befa53ec`, `2a70d50f2`, `f143cabd6`).
- **PipeWire:** port aliases kept locally when JACK refuses them, all physical audio ports without
  system ports, the main output setting with hardware outputs found by number (`2264da268`,
  `b6dcd055d`, `20649ad86`).
- **Engines on read-only data:** Organelle abstractions and pd's system externals found, a writable
  copy of Aeolus' stops, jack_capture from PATH, plugin GUIs on demand with jalv.gtk3 -H
  (ZYNTHIAN_NATIVE_GUI) (`b006d47de`, `b75aa1e42`, `722862e82`, `b97e3fc59`, `6ceaa61aa`).
- **LV2 widgets:** the built-in widgets' directory from zynthian_paths, zynthian-ui's lv2 bundles on
  LV2_PATH, user and external widgets in $ZYNTHIAN_PLUGINS_DIR/lv2-widgets (`627cfa3c4`,
  `c63ce88e4`, `2f18875e2`). Docs: [zynthian-widgets.md](../zynthian-widgets.md).
- **OSC status query** /STATUS/BUSY: what zynthian is busy with, for tools (`93ec4a128`,
  `f3ebdf760`). Docs: [osc-interface.md](../osc-interface.md).
