# zynthian on postmarketOS / Nura

Packages for building Nura (formerly postmarketOS) images that boot straight into zynthian,
running as an application on PipeWire (`ZYNTHIAN_DESKTOP=1`, see `desktop/`), without
ZynthianOS's system management. Same approach as the Kick port
(`behringer-kick-nura/Linux/nura/README.md`), whose host setup applies unchanged: pmbootstrap,
qemu binfmt for aarch64, the Lenovo Duet's USB boot and touchscreen rotation.

Status: all packages build with abuild on Alpine edge (x86_64, tested in a rootfs, not yet with
pmbootstrap), and the packaged zynthian starts on musl with pipewire-jack. Not yet tested on a
device.

## Packages

| Package | Source | What it does |
|---|---|---|
| `zyncoder/` | `--src` zyncoder checkout (`nura` branch) | `libzyncore.so` (MIDI router, controllers) in `/usr/lib/zynthian`, its Python module. Built with the wiringPi stand-in: no GPIO or I2C |
| `zynthian-ui/` | `--src` this checkout | UI and engine manager in `/usr/share/zynthian/zynthian-ui`, the zynlibs in `/usr/lib/zynthian`, `/usr/bin/zynthian`, bundled Python packages in `/usr/share/zynthian/python` |
| `zynthian-data/` | upstream tarballs | `zynthian-data` (presets, soundfonts, snapshots, ~715 MB), subpackages `zynthian-help` and `zynthian-sys-config` (configuration templates) |
| `postmarketos-ui-zynthian/` | this directory | Kiosk UI: cage + zynthian + pipewire-jack + the engines Alpine packages; `/etc/cage-ui/zynthian.sh` waits for PipeWire, forces a 256-frame quantum and makes zynthian fill the screen; a `tinydm.service` drop-in raises the real-time limit; on Panfrost GPUs XWayland runs without glamor (`/usr/share/tinydm/env-wayland.d/60-zynthian-xwayland.sh`, see [docs/nura-display.md](../docs/nura-display.md)) |
| `deploy.sh` | | Builds packages (`zynthian-ui` and `zyncoder` from their checkouts) and installs them on a running device over SSH (`pmbootstrap sideload`) |
| `seed-distfiles.sh` | | Puts zynthian-ui's Python sources into pmbootstrap's distfiles cache, so the `--src` build needs no network |

The recipes zynthian needs that aren't zynthian's own code are in [nura-builds](https://github.com/hjanetzek/nura-builds) (`aports/`, moved
there with their history on 2026-11-06): PySide6 6.12 (`pyside6`), zynthian's jalv
(`zynthian-jalv`: the LV2 engine needs it, Alpine's jalv makes LV2 chains hang while loading), the
LV2 plugins with the meta package `zynthian-lv2-plugins` (`lv2`), Pure Data and its externals
(`pd`), and the engines ZynAddSubFX, setBfree and SooperLooper (`engines`). nura-builds' CI builds
them and these packages, and publishes images and a package repository. How to package more:
its `docs/packaging-guide.md`; the state of zynthian's plugins: its `docs/lv2-plugins.md`.

The layout comes from `desktop/install.sh`, which `zynthian-ui` uses; `zyncoder` and
`zynthian-data` follow it in their APKBUILDs.

At run time `/usr/bin/zynthian` sets `ZYNTHIAN_DIR=/usr/share/zynthian` and
`ZYNTHIAN_LIB_DIR=/usr/lib/zynthian`; the user's configuration and data go to
`~/.config/zynthian` and `~/.local/share/zynthian` and are created on first start, together with
the LV2 plugin cache. Nothing is written to `/usr`.

### Python packages

Alpine packages most of zynthian's Python dependencies (`depends` in `zynthian-ui/APKBUILD`).
The others are bundled in `/usr/share/zynthian/python`, from files pinned in `$source`:

- pure Python wheels from PyPI: JACK-Client, soundfile, alsa-midi, oyaml, wavio, ffmpeg-python,
  pyrubberband, abletonparsing, future (needed by ffmpeg-python);
- sdists built in `build()`: sox, hwmon, and pyliblo3 from a GitHub commit (PyPI has only glibc
  wheels of 0.17.0, and the 0.16.3 sdist doesn't build with Cython 3).

tkinterweb (the help viewer) is left out: its wheel contains a prebuilt glibc Tkhtml library.
Without it the help screen is disabled.

`--src` skips `$source`, so `prepare` doesn't unpack these; the APKBUILD then takes them from
`$SRCDEST` (the distfiles cache). Seed it once per work dir:

```sh
nura/seed-distfiles.sh ~/.config/pmbootstrap-zynthian.cfg
```

(It needs sudo: the cache is owned by root.)

### Engines

Alpine packages fluidsynth, calf, x42-plugins, mda-lv2 and pure-data; jalv, sfizz and a2jmidid
are in `testing`. ZynAddSubFX, setBfree and SooperLooper are packaged in nura-builds'
`aports/engines/`, the LV2 plugins in its `aports/lv2/`; Aeolus and linuxsampler are not packaged
yet. The kiosk package
depends on the first group and on these (without pure-data and
a2jmidid: PipeWire bridges ALSA MIDI itself).

zynthian-data contains prebuilt binaries for ZynthianOS (glibc, ARM): Pure Data externals and a
plugin UI. The package removes them (they can't load on musl), so the Pd patches that need them
don't work.

## Setup

All commands below work when pasted into fish or bash, run from the zynthian-ui checkout.

Write the pmbootstrap config (own config, `ui = cage` until the kiosk package is built). The work
directory is the one the other Duet builds share (Kick, Oscairn, Zrythm: `~/postmarketos/kick-pi4`),
so chroots, the package cache, the signing key and built packages (e.g. Zrythm's Qt 6.12, which
the Qt port needs) are shared. Skip this if you already have `~/.config/pmbootstrap-zynthian.cfg`:

```sh
printf '%s\n' '[pmbootstrap]' 'device = google-kukui' 'hostname = zynthian-duet' 'is_default_channel = False' 'locale = C.UTF-8' 'service_manager = systemd' 'ssh_key_glob = ~/.ssh/id_ed25519.pub' 'ssh_keys = True' 'timezone = Europe/Berlin' 'ui = cage' "user = $USER" "work = $HOME/postmarketos/kick-pi4" '' '[providers]' 'postmarketos-base-ui-audio-backend = postmarketos-base-ui-audio-backend-pipewire' '' '[mirrors]' > ~/.config/pmbootstrap-zynthian.cfg
```

If the work directory is new, initialise it (interactive; answers as for Kick: channel edge,
systemd, audio backend PipeWire). Link the packages into pmbootstrap's pmaports checkout and seed the distfiles
cache (needs sudo). The plugins, engines, jalv and PySide6 come from a nura-builds checkout (here
next to zynthian-ui); link its recipe directories one by one, not its whole `aports/`, if another
checkout (Zrythm's `tools/nura`) already provides Qt 6.12:

```sh
pmbootstrap -c ~/.config/pmbootstrap-zynthian.cfg init
ln -sfn "$PWD/nura" ~/.local/var/pmbootstrap/cache_git/pmaports/zynthian
for d in lv2 pd engines zynthian-jalv pyside6; do ln -sfn "$PWD/../nura-builds/aports/$d" ~/.local/var/pmbootstrap/cache_git/pmaports/nura-builds-$d; done
ln -sfn "$PWD/../drivenbymoss-rust/nura" ~/.local/var/pmbootstrap/cache_git/pmaports/drivenbymoss   # optional: DrivenByMoss
ln -sfn "$PWD/../zynthian-webconf-nura/nura" ~/.local/var/pmbootstrap/cache_git/pmaports/zynthian-webconf   # optional: webconf (nura branch)
nura/seed-distfiles.sh ~/.config/pmbootstrap-zynthian.cfg
```

## Build and install

Build the packages, in this order, and switch the UI to zynthian:

```sh
pmbootstrap -c ~/.config/pmbootstrap-zynthian.cfg build --arch aarch64 --src="$PWD/../zyncoder" zyncoder
pmbootstrap -c ~/.config/pmbootstrap-zynthian.cfg build --arch aarch64 zynthian-data
pmbootstrap -c ~/.config/pmbootstrap-zynthian.cfg build --arch aarch64 --src="$PWD" zynthian-ui
pmbootstrap -c ~/.config/pmbootstrap-zynthian.cfg build --arch aarch64 postmarketos-ui-zynthian
pmbootstrap -c ~/.config/pmbootstrap-zynthian.cfg config ui zynthian
```

With `--src`, pmbootstrap doesn't build missing dependencies ("Additional packages need
building"), and zynthian-ui depends on zyncoder and zynthian-data, hence the order. Build the
`--src` packages before `install`, and the noarch packages with `--arch aarch64` (see the Kick
README for why). DrivenByMoss's packages (its zynthian controller drivers and the Maschine host)
come from a drivenbymoss-rust checkout: `nura/deploy.sh drivenbymoss dbm-nihost`. `--src` builds get the version `<pkgver base>_p<timestamp>`, so pmbootstrap
warns that the local pmaports have another version; that is expected.

Write the image. Replace `/dev/sdX` with the SD card or USB stick first (check with `lsblk`):

```sh
pmbootstrap -c ~/.config/pmbootstrap-zynthian.cfg install --sdcard=/dev/sdX
```

Update a running device (rebuilds from the checkouts, installs over SSH; `-r` restarts the
session):

```sh
nura/deploy.sh -r zynthian-ui
nura/deploy.sh -r zyncoder zynthian-ui
```

A device whose image was built with another pmbootstrap work dir (e.g. the Kick image) rejects
the packages with "UNTRUSTED signature": each work dir signs with its own key. Add `-k` once to
install this work dir's key on the device:

```sh
nura/deploy.sh -k -n zyncoder zynthian-data zynthian-ui
```

## Known issues

- Not yet tested with pmbootstrap or on a device.
- No hardware encoders or switches (wiringPi stand-in): touch, mouse and keyboard only.
- The UI's ALSA mixer looks for card `hw:0`; with PipeWire the card may be another one.
- `jack_capture` (audio recorder) is expected in `/usr/local/bin`.

## Tools

`nura/tools/` has helpers for a running device (address from the pmbootstrap config, as
`deploy.sh`): `screenshot.sh`, `zyninject.sh` (run Python inside the running Tk zynthian:
profiling, screen timing), `perf_profile.sh`, `thread_cpu.sh` (CPU per thread of zynthian, the
compositor and the engines) and `qt_switch_timing.sh` (screen switch times of the Qt UI). How the
performance numbers were measured, and how to repeat them: [docs/performance-measurement.md](../docs/performance-measurement.md).

## Switching kiosk sessions

`postmarketos-ui-zynthian` installs `kiosk-session`, which sets the session tinydm starts and
restarts it (`-n`: only set it). zynthian's and other kiosk packages (e.g. Zrythm's) can be
installed side by side:

```sh
kiosk-session list           # current and available sessions
kiosk-session zynthian       # zynthian with the Qt UI (cage)
kiosk-session zynthian-tk    # zynthian with the Tk UI
kiosk-session zrythm         # Zrythm (labwc)
kiosk-session zynthian-niri  # zynthian in niri, with plugin windows (postmarketos-ui-zynthian-niri)
```

### zynthian in niri: plugin windows

`postmarketos-ui-zynthian-niri` runs zynthian in [niri](https://github.com/YaLTeR/niri) instead of
cage, so that other windows can be shown next to it, e.g. LV2 plugin GUIs (X11, through
xwayland-satellite, which niri starts when the first X11 client connects):

- zynthian as a full-width column on the workspace `zynthian` (looks like full-screen); every other
  window on a workspace of its own, floating at the size it asks for (`zynthian-niri-workspaces`,
  following niri's event stream). When a window closes, its workspace goes away and zynthian is
  shown again.
- niri's overview shows all workspaces zoomed out (0.6); a tap picks one. It opens with Mod+O, a
  four-finger swipe on a touchpad, or `niri msg action toggle-overview`; there is no touchscreen
  gesture for it yet (to do: a swipe from a screen edge). Mod+Z goes back to zynthian.
- Mod+S switches the layout (`zynthian-niri-layout`): all windows as columns side by side on
  zynthian's workspace (niri's scrolling layout; Mod+Left/Right moves between them), and back.
  Tiled plugin windows get the full height.
- Mod is Super, on Chromebook keyboards the search key (in the Caps Lock place); the main bindings
  also work with Ctrl+Alt (O, Z, S, T, Left, Right). Mod+T opens a test window (glxgears).
- The config is generated at each start (`zynthian-niri`): `/etc/xdg/zynthian-niri/config.kdl`
  with the panel's output, the scale of `/etc/default/zynthian` (`ZYNTHIAN_OUTPUT_SCALE`) and a
  rotation only for panels without a DRM panel orientation (niri rotates the others itself). Local
  changes go into `/etc/xdg/zynthian-niri/local.kdl`.
- On the Duet, OpenGL X11 windows render on the GPU through XWayland with glamor (glxgears: 40 fps,
  no black rectangles). If plugin windows do show them, start XWayland without glamor:
  `environment { XWAYLAND_NO_GLAMOR "1"; }` in `local.kdl`.
- Plugin GUIs from zynthian itself need more work: zynthian's jalv is built without suil and GTK,
  the plugins of nura-builds without GUIs, and zynthian only opens native GUIs for a remote display.

From SSH, `niri msg` needs the session's socket:
`export NIRI_SOCKET=$(ls /run/user/$(id -u)/niri.*.sock)`.

The zynthian UI is `ZYNTHIAN_UI=qt|tk` in `/etc/default/zynthian`.
