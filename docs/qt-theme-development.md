# Developing a theme for the Qt UI: workflow

Status 2026-11-15 (branch `qt-tk-base`: tk is the base, classic an override). For people who design or change a theme of zynthian's Qt
Quick UI. How themes are built (tokens, directories, components) is in
[qt-theming.md](qt-theming.md); this guide is about the edit → look → compare loop: which setup to
use for what, how to see changes instantly, how to compare with the Tk UI, and what to check before
committing.

## The four setups

| Setup | Good for | Turnaround |
|---|---|---|
| Offscreen preview on the host (`nura/tools/qml_preview.py`) | a single component (a strip, a list row, a key) with mock data | instant (`--live`) or a PNG per run |
| Desktop preview (`desktop/preview_qt.sh`) | whole screens with a real zynthian backend on this machine | hot reload or a UI restart |
| QEMU VM (`nura/tools/qemu_compare.sh`) | the Nura system at a device's screen size, side by side with the Tk UI | hot reload (`sync_ui.sh -q`) |
| A device (Duet, Pixel 3) | final look and touch, real performance and fonts | hot reload (`sync_ui.sh -q`) |

Work outside-in: shape a component in the offscreen preview, fit it into its screen with hot reload
in the VM or on the device, compare with Tk in the VM, finish on the device.

## Themes and switching

- `zynqt/qml/` itself is the default theme, `tk` (replicates the upstream Tk UI): its `Theme.qml`
  sets tk's values on `ThemeBase.qml` (which declares all tokens, with classic's values).
- Every other theme is a directory `zynqt/qml/+<name>/` with its `Theme.qml` (the tokens it changes
  on ThemeBase) and the components it replaces. Files in `+<name>/` need `import ".."` to see the
  shared components. Shared QML contains no theme checks: a different look is a different file in
  the theme's directory.
- Existing themes: `tk` (default), `classic` (`+classic/`: the Qt port's first look, an override
  since 2026-11-15), `galactica` and `enterprise` (drafts, built on classic: their selectors are
  `[name, classic]`, so they get `+classic/`'s components where they have none; `BASES` in
  `zynqt/theme.py`). An unknown name falls back to tk with a warning.
- The theme is chosen at start with `ZYNTHIAN_QT_THEME` (unset or `tk`: the base). Put it into
  `~/.config/zynthian/zynthian_custom_config.sh` (`export ZYNTHIAN_QT_THEME=classic`): the launcher re-reads
  that file on every UI start, so switching only needs `RESTART_UI` (`nura/tools/sync_ui.sh -R`, or
  the Admin menu's "Restart UI"), not a session restart. `/etc/default/zynthian` is read only when
  the session starts.

## 1. Offscreen preview (host)

```sh
cd ~/bastel/github/zynthian-ui-parity
# a PNG
QT_QPA_PLATFORM=offscreen python3 nura/tools/qml_preview.py SCENE.qml out.png -t tk -s 800x480
# a live window that reloads when SCENE.qml or the theme's files change
python3 nura/tools/qml_preview.py SCENE.qml --live -t tk
# mock mixer strips (the compare snapshot's chains)
python3 nura/tools/qml_preview.py SCENE.qml --live -t tk --mixer
```

- A scene is a QML file whose root is an `Item`; it imports the UI's QML with
  `import "@QML@"` (the tool substitutes the path) and holds its own mock data. Examples:
  `~/bastel/github/zynthian-stuff/ui-parity/tools/scenes/` (list, main menu grid, mixer, keypad).
- Same Qt as Nura (PySide6 6.12), the repository's fonts, the theme's file selectors (default tk), and Tk's
  sizing values in `zynConfig` (font size 16, `ZYNTHIAN_UI_SCALE=auto`, the default colours) unless
  the environment overrides them.
- Not rendered offscreen: shader effects (`MultiEffect`, used for icon tinting). Check those in the
  VM or on the device.

## 2. Desktop preview (host)

`desktop/preview_qt.sh` runs the whole UI with the zynthian backend in a headless labwc at the
Duet's logical size (read its header: `-k` keeps it running, CUIAs over OSC). The theme reaches
the UI through the environment (`ZYNTHIAN_QT_THEME=tk desktop/preview_qt.sh ...`) or the desktop
config's `zynthian_custom_config.sh`. It needs OSC port 1370 free (no
other zynthian running). It uses your desktop zynthian's config and data: back up
`~/.local/share/zynthian/my-data/snapshots/last_state.zss` first, and don't leave test settings in
`~/.config/zynthian/zynthian_envars.sh`.

## 3. QEMU VM, side by side with Tk

`nura/tools/qemu_compare.sh` runs two VMs from the Nura image at the V5 kit's 800x480: one with
the Qt UI (SSH 2242), one with upstream's Tk UI as the reference (SSH 2243). See
[qemu-testing.md](qemu-testing.md), "Side by side".

```sh
nura/tools/qemu_compare.sh -g start          # windows (and sound) on your desktop
NURA_VM_PORT=2242 nura/tools/sync_ui.sh -V -R  # your checkout into the Qt VM, restart the UI
nura/tools/qemu_compare.sh shot DIR          # DIR/tk.png, DIR/qt.png, DIR/side-by-side.png
```

- Load the same snapshot in both before comparing. A quick one with patterns:
  `900-Test/001-Parity Test.zss` (Dexed, MiniOPL3, Fabla). Stop playback in both, and send the CUIA
  `HIDE_CURSOR` before screenshots (moving meters, play heads and the pointer are noise).
- Drive both the same way: CUIAs over OSC (`/CUIA/<name>` to UDP 1370 inside the VM; a sender
  without liblo: `ui-parity/cuia.py` in zynthian-stuff), touch with `ui-parity/tools/vin.py`.
- Tk and Qt never match pixel for pixel (Tk draws through XWayland, Qt Quick antialiases
  differently): compare side by side. A tolerant diff points to where to look:
  `magick compare -fuzz 15% -metric AE` on both shots downscaled to a quarter, or an edge overlay of
  both (`-edge 1`, composited in two colours). Exact pixel diffs (`compare -metric AE`) are for
  comparing the Qt UI with itself, e.g. tk or classic before and after a refactor.

## 4. Hot reload (VM or device)

Changed QML files are reloaded in the running UI within a second; the current screen and the
backend state (chains, snapshot, sequencer) stay. Built on Qt 6.12's QML Preview.

One-time setup on the target (VM or device):

```sh
sudo apk add qt6-qtdeclarative-dev   # provides /usr/lib/qt6/bin/qmlpreview (a smaller package is planned)
echo 'export ZYNTHIAN_QT_QMLPREVIEW=1' >> ~/.config/zynthian/zynthian_custom_config.sh
```

Then, from your checkout (it must contain the hot reload support, `zynthian_qt_main.py` of
`qt-parity` or later):

```sh
nura/tools/sync_ui.sh -R        # device from the pmbootstrap config; add -V (and NURA_VM_PORT) for a VM
# edit QML ...
nura/tools/sync_ui.sh -q        # copy only zynqt/qml, no restart: the UI reloads it
```

- On success `~/.local/state/tinydm.log` on the target shows
  "Inplace updates setting confirmed as: enabled".
- Literals (sizes, colours, texts) update in place: that is the reliable use (tested in the QEMU
  VM). Structural changes (new items or properties) are hit and miss: they may update in place,
  rebuild the whole UI (back on the mixer, QML defaults written into the backend: once the tempo
  went to 80 bpm and the active chain to main), or crash the UI (the launcher restarts it, exit 2;
  seen twice with a new item in a screen that was shown). A new file isn't picked up. For those,
  and for Python changes (models, screens, `zynthian_qt_main.py`), use `sync_ui.sh -R`.
- Python tools still work under it: `zyninject.sh` finds the UI process (qmlpreview's child).
- **Development only**: the QML debug server can control the UI. To switch it off, set
  `export ZYNTHIAN_QT_QMLPREVIEW=0` in `zynthian_custom_config.sh` and `RESTART_UI`: only deleting
  the line isn't enough, the running launcher keeps the variable it exported (until the session
  restarts). Without the variable nothing changes. The same holds for any variable a test put in
  the config (e.g. `ZYNTHIAN_UI_MAIN_MENU_COLUMNS`): to get rid of it, put `unset VAR` in the
  config for one `RESTART_UI` (the launcher sources it in its own shell), then delete the line.
- How it works and why (each detail broke it once): [qt-theming.md](qt-theming.md), "Previewing" →
  "QML hot reload (qmlpreview)".

## Before you commit

1. Every theme loads without QML warnings: switch through them with `RESTART_UI` and read
   `~/.local/state/tinydm.log` on the target (or the preview's output). `ui-parity/tools/qttour.sh`
   tours the screens of the Qt VM and prints the QML errors.
2. Your theme on the main screens at the target size (800x480 for the V5 kit, the Duet's 1280x800
   logical): mixer, main menu, a list (admin), chain control, the keypad (docked and overlay),
   the pattern editor.
3. Changes to shared components: tk and classic before/after with an exact pixel diff, or a note on
   what changed on purpose.
4. Commit by path (`git commit -- <files>`); other people and agents work in the same repository.

## Pitfalls

- A property named like a FINAL property of `Item` (`top`, `enabled`, `radius`, ...) in a component
  stops the whole QML from loading (the UI exits; the launcher restarts it).
- Symbols like ⏹ ▶ render from a colour emoji font unless the font is set: use the forkawesome
  glyphs the UI uses.
- `import ".."` is missing in a file under `+<theme>/`: its shared components are "not a type".
- `qmlpreview` must be Qt 6's (`/usr/lib/qt6/bin/qmlpreview`); `/usr/bin/qmlpreview` on some desktops
  is Qt 5's and silently does nothing.
- A Python syntax error synced into the VM (`sync_ui.sh -V -R`) makes zynthian fail at import; the
  launcher gives up after a few tries and tinydm restarts the whole session (the VM window looks
  like a reboot, zynthian then starts without the last state). Compile first:
  `python -m compileall -q zynqt zyngui zyngine zynthian_qt_main.py`.
- Translucent fills (`Qt.rgba(..., a)`) on a shape show what is under it: tk's controller widgets
  use that to let the grid show through the curve, as Tk draws its grid over the curve.
- Fixed pixel sizes in a component make it unthemable: use or add tokens in `ThemeBase.qml`
  (sizes derive from Tk's font size F there, as `zynthian_gui_config` does).
