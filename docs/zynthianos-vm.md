# The ZynthianOS VM (upstream's own environment)

A QEMU/KVM VM with **upstream's zynthian, set up by upstream's own script**, for testing upstream
behaviour and our upstream fixes (branches from `origin/tomita`) without any of the Nura port's
changes. `tools/zynthianos_vm.sh` builds it, starts it, copies a checkout into it, restarts
zynthian and runs upstream's test suite there.

```sh
tools/zynthianos_vm.sh status                  # running? set up? zynthian up? (last line: usable: yes/no)
tools/zynthianos_vm.sh start                   # boot it (about 30 s to SSH, see Numbers)
tools/zynthianos_vm.sh sync ~/bastel/github/zynthian-ui-noticed   # a checkout -> /zynthian/zynthian-ui
tools/zynthianos_vm.sh restart                 # restart zynthian, wait until it is up
tools/zynthianos_vm.sh run-tests               # upstream's ./run_tests.sh in the VM (pytest args after it)
tools/zynthianos_vm.sh restore                 # the original tree back
tools/zynthianos_vm.sh stop
```

`zynthianos_vm.sh -h` has every command and option. It works from any checkout or worktree.

## What it is

Upstream runs a "virtual zynthian" (https://virtual.zynthian.org/, forum topic "Virtual Zynthian
Demo", 2026-11): an x86_64 Debian trixie LXC container set up with zynthian-sys'
`scripts/setup_system_lxc_64bit_trixie.sh`, configured by `config/zynthian_envars_LXC_x86_64.sh`
(sound card "Dummy device", wiring `TOUCH_ONLY`, 800x480), with the UI on a KasmVNC X server
(`virtual_zynthian.service`) and the audio streamed to the browser over WebRTC (MediaMTX,
`jack2whip.service`). This VM is that setup, with the VM in the container's place:

| | |
|---|---|
| Base | Debian 13 trixie generic cloud image (`debian-13-generic-amd64.raw` from cloud.debian.org; the generic kernel, because the cloud kernel has no sound drivers) |
| Setup | zynthian-sys `scripts/setup_system_lxc_64bit_trixie.sh`, unchanged, run directly on the VM's Debian as root, branches **tomita** (`ZYNTHIAN_BRANCH=tomita ZYNTHIAN_SYS_BRANCH=tomita`) |
| SSH | port **2272**, `ssh -p 2272 root@127.0.0.1` (key login; root's password is zynthian's `opensynth`) |
| Webconf | http://127.0.0.1:8172 |
| Display | KasmVNC (upstream's), https://127.0.0.1:8472 (self-signed certificate, user root, password opensynth); `zynthianos_vm.sh shot` for screenshots |
| OSC | UDP 1370 in the VM = 127.0.0.1:1372 on the host (`zynthianos_vm.sh cuia ...`) |
| Directory | `/mnt/ssd860/qemu/zynthianos-x86` (`-d`, `ZOSVM_DIR`): `zos.img` (the disk, 64 GB sparse), `zos-built.img` (the disk right after setup, for `reset`), `seed.img` (cloud-init), `OVMF_VARS.fd`, `serial.log` |
| Resources | KVM, 8 vCPUs, 6 GB (`-c`, `-m`), UEFI (OVMF), headless (no QEMU display) |

Other VMs on this machine (2240, 2242/2243, 2252/2253, 2262) belong to other agents: the script only
touches its own directory and ports (`-p` moves all of them: webconf, KasmVNC and OSC follow).

### Why not the original Raspberry Pi image

The first plan was the real image (`zynthianos-vangelis-2610-stable`, aarch64) under
`qemu-system-aarch64 -M virt` with the image's own kernel rebuilt with virtio drivers (QEMU's
Raspberry Pi models have 1-2 GB, no network on raspi4b and no VC4). `qemu-system-aarch64` isn't
installed on this host, and the emulation (TCG) would be several times slower than a Pi. The user
chose upstream's own x86_64 setup instead: native speed, nothing new on the host, and an
environment upstream itself runs. The plan and the aarch64 groundwork (image, kernel source and
config) are kept in `/mnt/ssd860/qemu/zynthianos/` and in the private results repository
(`results/2026-11-19-zynthianos-qemu-plan.md`).

What that means for tests: the userland is upstream's (same repositories, same systemd units, the
same venv packages, same scripts and webconf), but the binaries are x86_64 Debian packages and
upstream's x86_64 recipe builds, not the Pi image's aarch64 builds. Engines/plugins that upstream
only ships as aarch64 prebuilt binaries are missing here, as on virtual.zynthian.org (jofemodo:
"I only installed the engines available as deb package").

## Changes to upstream's setup

Run unchanged on a fresh Debian trixie (2026-11-19, zynthian-sys tomita `3df97e00`), the script
breaks early and everything after it cascades: it was evidently developed in a container that
already had parts of the zynthian environment. `setup` works around that as narrowly as possible
(each one is an upstream issue, in the private issues log; the unpatched run's log is in the private
results repository):

1. `./zynthian_envars.sh` (what the script sources first) is `config/zynthian_envars_LXC_x86_64.sh`,
   the configuration the script itself installs later (line 266). With `scripts/zynthian_envars.sh`
   zyncoder is built before that for a GPIO wiring layout and fails (`wiringPi.h` missing).
2. `PATH` has zynthian-sys' `scripts` and `sbin` from the start (what `etc/profile.zynthian` adds,
   which the script only sources at line 250; it calls `create_my_data_dirtree.sh` bare at 208).
3. `ZYNTHIAN_MY_DATA=/zynthian/zynthian-my-data` in the environment: `sbin/create_my_data_dirtree.sh`
   tests and creates `$ZYNTHIAN_MY_DATA`, which nothing defines (the rest of it uses
   `$ZYNTHIAN_MY_DATA_DIR`), so the user data tree is never created (vangelis has the same bug).
4. `python3-lgpio` is dropped from the script's apt line (the only edit of the script; the diff is
   kept in the VM as `/root/zynthian-setup/setup.patch`): it exists only in Raspberry Pi OS' archive,
   and the failing `apt-get` leaves out every Python package of that line, `python3.13-venv` too
   (then no `/zynthian/venv` and no pip modules).
5. `python-is-python3` and the `en_US.UTF-8` locale are installed/enabled before the run (Raspberry
   Pi OS has both; waf recipes call `python`, and the script's `update-locale` names en_US.UTF-8
   without generating it).

The VM-specific additions:

- **snd-dummy is loaded at boot** (`/etc/modules-load.d/zynthianos-vm.conf`, from cloud-init): in
  upstream's container the LXC host provides the Dummy card; here the VM's own kernel does.
- **cloud-init** (Debian cloud image): hostname `zynthian`, root's SSH key and password.
- **Test venv** `/zynthian/zynthian-ui/venv`: created by `setup` (see below), plus `xvfb`/`xauth`
  from Debian for `run_tests.sh gui`. Not part of upstream's setup; `/zynthian/venv` is untouched.
- UEFI boot (OVMF): the image's BIOS grub boot-looped under SeaBIOS on this host.

## Building it

```sh
tools/zynthianos_vm.sh setup        # 1-2 hours on the first run; resumes if interrupted
```

`setup` creates the disk from the Debian image (downloaded to the VM directory if missing,
sha512-checked), boots it with the cloud-init seed, fetches the three scripts from zynthian-sys
(branch `-b`, default tomita) into `/root/zynthian-setup/` in the VM, runs
`setup_system_lxc_64bit_trixie.sh` there detached (log: `/root/zynthian-setup/setup.log`, exit code
in `exit`), waits for it, sets up the test venv, reboots, waits for zynthian and saves the disk as
`zos-built.img`. `reset` copies that back (discards every change made since).
A fresh build from nothing: `stop`, delete `zos.img`, `zos-built.img`, `seed.img`, then `setup`.

## Testing upstream fixes

The VM's `/zynthian/zynthian-ui` is a git clone of upstream on `tomita`. To test a branch:

```sh
cd ~/bastel/github/zynthian-ui-noticed            # a branch from origin/tomita
tools/zynthianos_vm.sh sync                        # (or: sync DIR)
tools/zynthianos_vm.sh restart                     # "zynthian is up (N s)"
tools/zynthianos_vm.sh log 100                     # the UI's journal (virtual_zynthian.service)
tools/zynthianos_vm.sh restore && tools/zynthianos_vm.sh restart   # back to upstream's tree
```

- **sync** saves the original tree once as `/zynthian/zynthian-ui.orig`, then rsyncs the checkout
  over `/zynthian/zynthian-ui` with `--delete`. Not sent and not deleted: `.git` (the VM keeps its
  clone, so `git -C /zynthian/zynthian-ui status`/`diff` in the VM show your change against
  upstream's commit), `.gitignore`d files, `venv`, `build/` directories, `*.so`, caches. The VM's
  native libraries (`zynlibs/*/build`, built by upstream's setup) stay, so a change to C code in
  zynlibs needs a build in the VM (`zynthianos_vm.sh ssh 'cd /zynthian/zynthian-ui/zynlibs && ./build.sh'`).
- **restore** rsyncs `/zynthian/zynthian-ui.orig` back and removes it.
- **restart** restarts `virtual_zynthian.service` (upstream's `zynthian.service` is a trigger for it
  in this setup: `systemctl restart zynthian` from webconf and scripts does the same) and waits
  until the service is active and zynthian's OSC server is bound (UDP 1370).
- To move the VM's repositories to a newer tomita: `zynthianos_vm.sh ssh 'cd /zynthian/zynthian-ui && git pull'`
  (or upstream's own update, `/zynthian/zynthian-sys/scripts/update_zynthian.sh`, which updates all
  repositories and runs their recipes) — after a `restore`.

### Upstream's test suite

Upstream (tomita) has `run_tests.sh` and `tests/README.md`; its CI (`.github/workflows/tests.yml`)
runs `ruff check .`, builds the native libraries with `tests/native/build_native.sh <zyncoder>` and
runs `xvfb-run -a python -m pytest -ra`. "Running on a Zynthian" is supported: `./run_tests.sh`,
with a write guard that refuses writes to `/zynthian/config` & co.

```sh
tools/zynthianos_vm.sh run-tests                 # ./run_tests.sh (hermetic: unit, integration, architecture)
tools/zynthianos_vm.sh run-tests gui             # under xvfb
tools/zynthianos_vm.sh run-tests native          # builds tests/native (against /zynthian/zyncoder), real libs on a private dummy jackd
tools/zynthianos_vm.sh run-tests -k chain -x     # pytest arguments
tools/zynthianos_vm.sh ssh 'cd /zynthian/zynthian-ui && venv/bin/ruff check .'
```

`run_tests.sh` uses the checkout's `venv` when there is one, else `/zynthian/venv`. `setup` makes
`/zynthian/zynthian-ui/venv` (a venv of /zynthian/venv's Python with a `.pth` file that adds
`/zynthian/venv`'s site-packages, plus pytest, pytest-timeout, pytest-cov and ruff from PyPI), so
`/zynthian/venv` itself stays as upstream built it. `sync`/`restore` leave the venv alone
(`/venv/` is in the VM clone's `.git/info/exclude`).

## Driving the UI

- **CUIAs over OSC:** `tools/zynthianos_vm.sh cuia NAME [ARGS]` sends `/cuia/NAME` to zynthian's
  OSC server (integer arguments as `i`, others as `s`), e.g. `cuia zynswitch 2 S`,
  `cuia screen_admin`, `cuia arrow_down`. From inside the VM: `oscsend localhost 1370 /cuia/NAME`.
- **Screenshots:** `tools/zynthianos_vm.sh shot FILE.png` (ImageMagick `import` of the UI's X
  display `:0`, which is KasmVNC's).
- **Looking at it:** KasmVNC in a browser, https://127.0.0.1:8472.
- `tools/zyninject.sh` doesn't apply (it needs Python 3.14's `sys.remote_exec`; the VM has Debian's
  3.13) and talks to Nura devices.

## Limits

- No audio output on the host: JACK runs on the Dummy card (upstream streams the mix to the browser
  via MediaMTX/WebRTC; that is installed and enabled as upstream does, not used by the tools).
- x86_64 builds, not the device's aarch64 ones: engine/plugin availability differs from a real
  zynthian (see above), and CPU/latency numbers mean nothing for a Pi.
- No GPIO/I2C/SPI, no kit autodetection; wiring is `TOUCH_ONLY`, as upstream's virtual zynthian.
- Updating with upstream's `update_zynthian.sh` follows upstream; the test venv and the snd-dummy
  module file survive it.

## Numbers

(filled in from the first build; see the plan document for the measurements)
