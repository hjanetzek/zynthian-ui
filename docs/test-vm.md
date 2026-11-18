# The test suite VM

zynthian-ui's test suite (`run_tests.sh`, [tests/README.md](../tests/README.md)) runs in a QEMU VM of
its own, not on the developer's machine: `tools/test_vm.sh` creates it, installs what the suite
needs, copies a checkout into it and runs the tests there over SSH. Every mode runs completely there:
the hermetic layers, the Tk tests under xvfb and the native libraries on a private dummy jackd.

```sh
cd ~/bastel/github/zynthian-ui-<your worktree>
tools/test_vm.sh status              # running? (start / stop)
tools/test_vm.sh sync                # this checkout -> the VM
tools/test_vm.sh run all             # default + gui + native, with a summary per mode
tools/test_vm.sh run gui -k mixer    # one mode, pytest arguments after it
tools/test_vm.sh shell               # a shell in the VM, in the synced tree
```

`test_vm.sh -h` has all options. It works from any checkout or worktree of zynthian-ui (the script
of one checkout can sync another: `test_vm.sh sync DIR`).

## The VM

| | |
|---|---|
| Base | zynthian's Nura image (`zynthian-qemu-amd64.img.zst`, the user's download in `~/.cache/nura-builds`) |
| SSH | port **2262** (`ssh -p 2262 user@127.0.0.1`; key login and passwordless sudo) |
| Directory | `/mnt/ssd860/qemu/nura-builds-test` (the VM drive, when mounted), else `~/.cache/nura-builds-test`; `-d DIR` or `NURA_TEST_VM_DIR` |
| Disk | 12 GB sparse, about 4 GB used after setup |
| Resources | 4 GB memory, 8 CPUs (`-m`, `-c`), headless, no sound card |

When the VM drive isn't mounted and `~/.cache/nura-builds-test` has no disk, the script stops with a
message (mount it: `sudo mount /mnt/ssd860`, it is in `/etc/fstab`) instead of creating a new disk in
the home directory. Other VMs on this machine (SSH 2222, 2240, 2242/2243, 2252/2253) belong to the
user and other agents: the script only touches its own directory and port.

**Why zynthian's image and not a plain Alpine/postmarketOS one:** the suite imports zynthian's whole
Python stack (lilv, numpy, scipy, PySide6, Tk, JACK-Client, pyliblo3, oyaml, soundfile, ...), and the
Nura zynthian-ui package brings exactly that: Alpine packages as dependencies, and the PyPI modules
Alpine doesn't have vendored in `/usr/share/zynthian/python`. A plain image would need that list
rebuilt by hand and would drift from what the devices run. The kiosk session (zynthian itself,
PipeWire) is switched off: the VM only runs tests.

## What `setup` installs

`test_vm.sh setup` (idempotent; a fresh disk from the image: `test_vm.sh -r setup`, about 1.5 minutes):

- **pytest** with pytest-timeout and pytest-cov, ruff (`py3-pytest*`, `ruff`).
- **Native build**: build-base, cmake, pkgconf, python3-dev, and the headers: pipewire-jack-dev (JACK),
  alsa-lib-dev, liblo-dev, libsndfile-dev, libsamplerate-dev, rubberband-dev, fftw-dev, nlohmann-json.
  zyncoder's sources come from the host (synced next to the tree, see below).
- **GUI tests**: xvfb, xvfb-run, xauth, mesa-dri-gallium, font-dejavu (Tk comes with zynthian-ui).
- **git** (the executable-bit test reads the index, see `sync`), rsync, py3-cffi, py3-cairosvg.
- **A venv** `~/zyntest-venv` with the system's modules (`--system-site-packages`), the modules
  zynthian-ui vendors (a `.pth` file for `/usr/share/zynthian/python`), and from PyPI what neither
  has: moderngl-window and pyopengltk (imported by the Tk UI's `zynthian_widget_audio_file.py`).
- **jackd** (next section), and `/etc/profile.d/zyntest.sh` (the venv on `PATH`).
- `tinydm` disabled: no kiosk session.

### jackd

The native tests start a private `jackd --no-realtime -d dummy` (`tests/jacktest.py`, found with
`shutil.which("jackd")`) and talk to it through libjack. On Nura that is a problem twice over:

1. Alpine's `jack` package conflicts with `pipewire-jack` (both own `/usr/lib/libjack.so.0`), and the
   image's zynthian packages depend on pipewire-jack. pipewire-jack's libjack talks to PipeWire, not
   to a jackd.
2. musl's getopt misparses jackd's driver options when the value is a separate argument:
   `-d dummy -r 48000 -p 256` runs with a period of 8192, not 256. With the value attached
   (`-r48000 -p256`) it works. `tests/jacktest.py` passes them separately.

The solution in the VM:

- `jack` is unpacked (`apk fetch`) to **`/opt/jack`**, with a `libjack.so` link (as jack-dev would
  install it: JACK-Client dlopen()s `libjack.so`).
- **`/etc/ld-musl-x86_64.path`** puts `/opt/jack/usr/lib` before `/lib:/usr/local/lib:/usr/lib`: every
  process in the VM loads jack's libjack, also the child processes the tests start with a cleared
  environment (`tests/native/zynmixer/test_exit.py` passes only `PATH` and `JACK_DEFAULT_SERVER`,
  so `LD_LIBRARY_PATH` would not reach them). Nothing in the VM uses PipeWire's JACK.
- **`/usr/local/bin/jackd`**, a wrapper: sets `JACK_DRIVER_DIR=/opt/jack/usr/lib/jack` and attaches
  the separate driver option values before it runs `/opt/jack/usr/bin/jackd`.
- The libraries are compiled against pipewire-jack-dev's headers: the same API and soname.

Removing pipewire-jack and installing jack properly isn't possible without removing zynthian-ui,
zyncoder and the session packages (and with them the Python stack the tests use). `setup` checks the
result: a dummy jackd at 48000 Hz / 256 frames and a JACK-Client client on it. The warning
`Cannot lock down ... memory area (Out of memory)` from jackd is harmless (memlock limit, no realtime).

## `sync` and `run`

`sync [DIR]` copies the checkout (default: the one of the current directory) to
`~/zynthian-ui-test/NAME` in the VM, NAME being its directory name (`-t NAME` for another): every
worktree gets its own tree and its own native build, so several agents can use the VM. Next to the
trees, shared: `~/zynthian-ui-test/zyncoder` (from the checkout's `zyncoder` link or `../zyncoder`;
`build_native.sh` builds libzyncore from it) and `~/zynthian-ui-test/zynthian-data/snapshots` (the
corpus tests). Left out: `.git`, `.gitignore`d files (venv, `__pycache__`, build directories, caches);
the VM's own `tests/native/build` stays. The tree in the VM gets a git index made from the checkout's
(`git ls-files -s`: file modes and blob ids, no history), for `test_cli_scripts.py`'s check of the
committed executable bit.

`run [MODE] [ARGS]` runs `tests/native/build_native.sh` first (incremental with make: a few seconds
when nothing changed; `-B` skips it), then `run_tests.sh` in the VM, streaming the output, with the
exit code of pytest. MODE: `default` (`./run_tests.sh`), `gui`, `native`, or `all` (the three one after
the other and a summary line per mode; exit code: the first failing mode's). The native libraries are
built for every mode, so `default` and `gui` include `tests/native` too: `run gui` alone runs
everything; `all` checks each mode as the README describes it. One run at a time per tree (`flock`).

Always `sync` before `run`: `run` tests what was synced last, not the checkout.

## How long it takes

Measured 2026-11-18 on this desktop (8 vCPUs), from a fresh disk, `run all` on main (4f33b58c):

| Step | Time |
|---|---|
| `-r setup` (fresh disk, packages) | 93 s |
| `sync` | a few seconds |
| native build, first time / unchanged | about 25 s / 2 s |
| `default` | 107 s |
| `gui` | 104 s |
| `native` | 38 s |
| `run all`, first build included | 267 s (about 4.5 min) |

Result there: default 812 passed, 2 skipped, 28 xfailed, 3 failed; gui 814 passed, 28 xfailed,
3 failed; native 249 passed, 13 xfailed, 1 failed. The failures are the three stale xfail markers below.

## Skips by design and known issues

Skips that remain by design:

- `default` mode: `tests/gui/test_tk_infrastructure.py` (2) skip, "no DISPLAY": the
  default mode has no display, by design; `gui` runs them.
- `tests/hardware/` is empty (it would need `ZYNTHIAN_TEST_HARDWARE=1` on a real box).

Known issues (also in the issues log):

- Three strict xfails XPASS on main (4f33b58c), so the suite is red there until their markers are
  removed (test bookkeeping, not the VM): `tests/integration/test_legacy_snapshot.py`
  `test_v0_snapshot_without_note_range_converts` and `test_v0_mod_ui_layer_without_midi_channel_converts`
  (the converter was fixed in 30c3121c), and `tests/native/zynmixer/test_exit.py::test_exit_after_solo_is_clean`
  (the invalid free in mixer.c `end()` was fixed in d850becd: defect 31 is gone).
- One warning per run: moderngl-window imports PyGLM as `glm` (a PendingDeprecationWarning of PyGLM).
- `tests/jacktest.py` passes jackd's driver options as separate arguments, which musl's jackd
  misparses; the VM's wrapper attaches them. On a Nura device with a real jackd the same happens.
- Once, `test_module_imports[zyngine.deconvolve]` timed out (60 s) in the `default` run, inside the
  import of `numpy.testing` (scipy.signal → array_api_compat); it passed in the other modes and alone.
  Not reproduced so far; Alpine's py3-numpy-pyc has no byte code for `numpy/testing`, so that import
  compiles at every run.

## Rebuild from scratch

```sh
tools/test_vm.sh stop
tools/test_vm.sh -r setup            # a fresh disk from the image, then everything installed
tools/test_vm.sh sync && tools/test_vm.sh run all
```

A newer image: download it as `run_qemu.sh -u` does (into `~/.cache/nura-builds`), then `-r setup`.
