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
| `postmarketos-ui-zynthian/` | this directory | Kiosk UI: cage + zynthian + pipewire-jack + the engines Alpine packages; `/etc/cage-ui/zynthian.sh` waits for PipeWire, forces a 256-frame quantum and makes zynthian fill the screen; a `tinydm.service` drop-in raises the real-time limit |
| `deploy.sh` | | Builds packages (`zynthian-ui` and `zyncoder` from their checkouts) and installs them on a running device over SSH (`pmbootstrap sideload`) |
| `seed-distfiles.sh` | | Puts zynthian-ui's Python sources into pmbootstrap's distfiles cache, so the `--src` build needs no network |

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
nura/seed-distfiles.sh ~/.config/pmbootstrap-zynthian.cfg   # needs sudo: the cache is owned by root
```

### Engines

Alpine packages fluidsynth, calf, x42-plugins, mda-lv2 and pure-data; jalv, sfizz and a2jmidid
are in `testing`. zynaddsubfx, setBfree, Aeolus, sooperlooper, linuxsampler and dragonfly-reverb
are not packaged yet. The kiosk package depends on the first group (without pure-data and
a2jmidid: PipeWire bridges ALSA MIDI itself).

zynthian-data contains prebuilt binaries for ZynthianOS (glibc, ARM): Pure Data externals and a
plugin UI. The package removes them (they can't load on musl), so the Pd patches that need them
don't work.

## Setup

As for Kick, with its own config and work directory. `~/.config/pmbootstrap-zynthian.cfg`:

```ini
[pmbootstrap]
device = google-kukui
hostname = zynthian-duet
is_default_channel = False
locale = C.UTF-8
service_manager = systemd
ssh_key_glob = ~/.ssh/id_ed25519.pub
ssh_keys = True
timezone = Europe/Berlin
ui = zynthian
user = <user>
work = <home>/postmarketos/zynthian

[providers]
postmarketos-base-ui-audio-backend = postmarketos-base-ui-audio-backend-pipewire

[mirrors]
```

Link the packages into pmbootstrap's pmaports checkout:

```sh
ln -sfn "$PWD/nura" ~/.local/var/pmbootstrap/cache_git/pmaports/zynthian
```

## Build and install

```sh
nura/seed-distfiles.sh                                          # once per work dir
pmb() { pmbootstrap -c ~/.config/pmbootstrap-zynthian.cfg "$@"; }
pmb build --arch aarch64 --src=../zyncoder zyncoder
pmb build --arch aarch64 zynthian-data
pmb build --arch aarch64 --src="$PWD" zynthian-ui
pmb build --arch aarch64 postmarketos-ui-zynthian
pmb install --sdcard=/dev/sdX
```

Build in this order: with `--src`, pmbootstrap doesn't build missing dependencies ("Additional
packages need building"), and zynthian-ui depends on zyncoder and zynthian-data. Build the
`--src` packages before `install`, and the noarch packages with `--arch aarch64` (see the Kick
README for why). `--src` builds get the version `<pkgver base>_p<timestamp>`, so pmbootstrap
warns that the local pmaports have another version; that is expected. Updating a running device:

```sh
nura/deploy.sh -r zynthian-ui              # rebuild from this checkout, install, restart the session
nura/deploy.sh zyncoder zynthian-ui        # both checkouts
```

## Known issues

- Not yet tested with pmbootstrap or on a device.
- No hardware encoders or switches (wiringPi stand-in): touch, mouse and keyboard only.
- The UI's ALSA mixer looks for card `hw:0`; with PipeWire the card may be another one.
- `jack_capture` (audio recorder) is expected in `/usr/local/bin`.
