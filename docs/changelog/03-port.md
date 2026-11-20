# Changelog: 03-port, zynthian outside ZynthianOS

What strand 03 of `main` changes, newest entry first: zynthian-ui running on other systems
(desktop Linux, Nura/postmarketOS packages) with configurable directories and PipeWire. The strand
applies directly on origin/tomita. Marker `strand/03-port`; this file is the strand's last commit
(see [README.md](README.md)). The Nura packaging itself is in nura-builds.

## 2026-11-26: rebased onto tomita e2f423d33: no conflicts; see rebase-onto-tomita-2026-11-26.md

## 2026-11-21: Launcher: the configuration sourced per start, so removed settings take effect

- `743f5d0c9` desktop launcher: source the configuration only in each start's subshell

## 2026-11-20: rebased onto tomita 0c1098a68: the admin screen's VNC entry (1723a5ab: vncserver1) conflicted with the desktop-mode guard: kept under the guard; see rebase-onto-tomita-2026-11-20c.md

- `9e2d3f2f2` Add desktop mode (ZYNTHIAN_DESKTOP=1)

## 2026-11-20: strand 01's start-failure fixes below: the desktop engine commit keeps only its comment on the failed processor's cleanup

- `cf36bf5bf` Desktop mode: hide engines whose program isn't installed; fix failed processor cleanup

## 2026-11-20: the strand when the changelog started

42 commits on strand 02, written 2026-11-02 to 2026-11-19.

- **Directories from the environment:** `zynthian_paths` and environment variables for every
  directory, native libraries from ZYNTHIAN_LIB_DIR, content packs beside a read-only
  zynthian-data (ZYNTHIAN_PACKS_DATA_DIR), ZynthianOS data paths in snapshots mapped to this
  system's (`4a41639d2`, `01f1c5e1c`, `592f73f9c`, `d30de11e3`).
- **Desktop mode** (ZYNTHIAN_DESKTOP=1): no Raspberry Pi hardware, no update_zynthian_sys.sh, no
  RBPi audio device, engines hidden whose program isn't installed, UI scale (ZYNTHIAN_UI_SCALE),
  optional help viewer, no systemctl where there is no systemd (`9e2d3f2f2`, `f040d2845`,
  `299e758d1`, `7c97300bf`, `cf36bf5bf`, `a821ac0d6`, `d606e476d`, `ce4ba57e3`).
- **`desktop/`:** setup, launcher and install script, a uv venv with all Python packages, zynthian's
  jalv fork, websocket-server bundled, the Qt UI with ZYNTHIAN_UI=qt (Tk where the tree has none),
  no processes left after a session restart (`1f7a0d8db`, `8a55b0e16`, `c4a83b2c9`, `04aeb4734`,
  `f25fd4ef8`, `03f67f779`, `eebe1dab0`, `b7359f7ca`).
- **PipeWire:** port aliases kept locally when JACK refuses them, all physical audio ports without
  system ports, the main output setting with hardware outputs found by number (`6143f3591`,
  `b59ab6379`, `04934aead`).
- **Engines on read-only data:** Organelle abstractions and pd's system externals found, a writable
  copy of Aeolus' stops, jack_capture from PATH, plugin GUIs on demand with jalv.gtk3 -H
  (ZYNTHIAN_NATIVE_GUI) (`e33beabe9`, `de3cf7366`, `07b26d6e5`, `cc1936bee`, `3e5420f6e`).
- **LV2 widgets:** the built-in widgets' directory from zynthian_paths, zynthian-ui's lv2 bundles on
  LV2_PATH, user and external widgets in $ZYNTHIAN_PLUGINS_DIR/lv2-widgets (`afde5ded9`,
  `d9f6ea04f`, `30c7d3369`). Docs: [zynthian-widgets.md](../zynthian-widgets.md).
- **OSC status query** /STATUS/BUSY: what zynthian is busy with, for tools (`65d897ec3`,
  `0d39a8a5a`). Docs: [osc-interface.md](../osc-interface.md).
