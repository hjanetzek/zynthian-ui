# Measuring UI performance on the device

How the numbers in [qt-port-plan.md](qt-port-plan.md) and [nura-display.md](https://github.com/hjanetzek/nura-builds/blob/main/docs/nura-display.md)
were measured, so they can be repeated: CPU use per thread, and screen switch times of the Qt and
Tk UIs. The device was a Lenovo IdeaPad Duet (MT8183: cpu0–3 Cortex-A53, cpu4–7 Cortex-A73) with
Nura; the tools work on other Nura devices too.

All tools are in `tools/` and run from the host. They find the device through the
pmbootstrap config (default `~/.config/pmbootstrap-zynthian.cfg`: `user`, `hostname`.local) or
`-H HOST -u USER`, and need SSH access with passwordless `sudo` on the device (for the CPU
governor and `sys.remote_exec`).

| Tool | Measures |
|---|---|
| `thread_cpu.sh` | CPU per thread of zynthian (Tk or Qt UI), the compositor, the engines |
| `qt_switch_timing.sh` | Qt UI: time from a screen switch to the frame on screen |
| `zyninject.sh screen_timing.py` | Tk UI: time of a screen switch until the X server has drawn it |
| `zyninject.sh profile_screen.py`, `profile_idle.py`, `perf_profile.sh` | Tk UI: where the time goes (cProfile, perf) |
| `zynqt/spike/spike.py --bench` | Qt Quick on the device without zynthian (M0 spike) |

## Conditions

The numbers depend on these more than on anything else; keep them the same when comparing.

- **CPU governor.** The tools set `performance` for the measurement and restore the previous
  governor (`-g -` keeps it). Under `schedutil` the clock stays low for bursty UI work and the
  same work shows about twice the CPU time (and slower screen switches). Results are percent of
  one core at that clock.
- **CPU affinity.** zynthian pinned to the big cores: `CPUAffinity=4-7` (systemd unit property
  or the tinydm drop-in `60-zynthian-cpus.conf`), as in the kiosk.
- **Nothing else in the audio graph.** A second PipeWire client that is stopped (e.g. `kill
  -STOP`) stalls the whole graph: xruns, CPU load 100 %, engines and snapshots fail to load. Stop
  other audio applications for the measurement, don't suspend them.
- **Same compositor and resolution for comparisons.** Qt runs as a native Wayland client at the
  output's resolution (1920×1200 at scale 2 on the Duet). Tk runs through XWayland; under a
  compositor with output scaling (labwc at scale 2) its window is drawn at half the resolution
  (960×565) and scaled up, under cage at full resolution. XWayland's glamor setting matters too
  (see nura-builds' [nura-display.md](https://github.com/hjanetzek/nura-builds/blob/main/docs/nura-display.md)).
- **Idle or playing.** Meters only cost something when the levels change: measure once idle and
  once while playing (e.g. a MIDI keyboard into a FluidSynth chain).
- **Don't touch the device** during switch timing: touches and the timing CUIAs interleave.

## Running zynthian for a measurement

Either in its kiosk session (cage, started by tinydm), or as a second application in a running
Wayland session (labwc of another kiosk, a desktop) as a transient systemd user unit. Start it
from the device or over SSH with `systemd-run`: a process started from an SSH session in the
background is killed when the session ends (SIGHUP), even with `setsid`.

Kiosk session, Qt UI with timing: in `~/.config/zynthian/zynthian_custom_config.sh`

```sh
export ZYNTHIAN_UI=qt
export ZYNTHIAN_QT_TIMING=1
```

then `sudo systemctl restart tinydm`; zynthian's output goes to `~/.local/state/tinydm.log`.

Qt UI in a running Wayland session (here `wayland-0`), on the device:

```sh
systemd-run --user --unit=zynqt-test --property=CPUAffinity=4-7 \
	--setenv=WAYLAND_DISPLAY=wayland-0 --setenv=QT_QPA_PLATFORM=wayland \
	--setenv=QT_WAYLAND_DISABLE_WINDOWDECORATION=1 --setenv=ZYNTHIAN_UI=qt \
	--setenv=ZYNTHIAN_FULLSCREEN=1 --setenv=ZYNTHIAN_QT_TIMING=1 /usr/bin/zynthian
```

Tk UI in the same session through XWayland (display `:0`):

```sh
systemd-run --user --unit=zyntk-test --property=CPUAffinity=4-7 \
	--setenv=DISPLAY=:0 --setenv=ZYNTHIAN_FULLSCREEN=1 --setenv=ZYNTHIAN_UI_SCALE=auto /usr/bin/zynthian
```

Output: `journalctl --user -u zynqt-test` (or `zyntk-test`). Stop with `systemctl --user stop
zynqt-test` (zynthian saves its state and exits cleanly on SIGTERM). Only one zynthian at a time:
both use the OSC port 1370 and the same JACK client names. Wait until the snapshot has loaded
(~30 s on the Duet) before measuring.

## CPU per thread

```sh
tools/thread_cpu.sh -t 20
```

Output, percent of one core over the measuring time (Qt UI on the mixer while playing):

```
python3 ./zynthian_qt_main.py  (pid 12309), 20 s, governor performance
  engine:fluidsynth                  9.4 %
  zynthian:data-loop.0               7.0 %
  zynthian:python3                   4.8 %
  zynthian:QSGRenderThread           4.8 %
  compositor:labwc                   2.8 %
```

- `zynthian:python3`: zynthian's main thread, the UI's Python and Qt's GUI thread (Tk: all of
  the UI).
- `zynthian:QSGRenderThread`: Qt Quick's render thread (GPU command submission).
- `zynthian:data-loop.0`: PipeWire's real-time thread inside zynthian (pipewire-jack): the
  zynlibs' audio processing (mixer, sequencer, audio player).
- `compositor:*`: cage or labwc compositing and presenting the frames.
- `engine:*`: the synth/effect processes.

For the UI alone, show the screen to measure (e.g. `oscsend localhost 1370
/cuia/screen_audio_mixer` on the device) and run it idle, then while playing.

## Screen switch times, Qt UI

zynthian must run with `ZYNTHIAN_QT_TIMING=1`. Then

```sh
tools/qt_switch_timing.sh -U zynqt-test     # test unit; without -U: the kiosk log
tools/qt_switch_timing.sh -r 5 screen_audio_mixer main_menu    # other CUIAs, 5 rounds
```

switches through the screens over OSC (2 s apart) and prints, per switch, the time from the start
of the switch (`ZynUI._set_current_screen`) to the next frame on screen
(`QQuickWindow.frameSwapped`), and how much of it was Python (`build`: filling the screen's
list):

```
main_menu: 52.6 ms to frame (build 5.5 ms)      <- first visit: the screen's view is built
...
main_menu: 5.1 ms to frame (build 0.5 ms)
chain_control: 7.1 ms to frame (build 1.3 ms)
```

Use the rounds after the first for the steady state; the first shows the cost of building each
screen's view once.

## Screen switch times, Tk UI

```sh
tools/zyninject.sh -s 'SCREENS=["mixer", "main_menu", "chain_control", "admin", "snapshot"]' \
	-s ROUNDS=3 tools/screen_timing.py
```

runs `screen_timing.py` inside the running Tk zynthian (`sys.remote_exec`, scheduled on Tk's
event loop) and prints per switch: `show` (zynthian's `show_screen()`, Python), `draw` (Tk's
pending redraws), `events` (remaining Tk events) and `server` (a round trip until the X server
has processed everything), and their total. The tool sets no governor: set `performance` on the
device first (`echo performance | sudo tee
/sys/devices/system/cpu/cpufreq/policy*/scaling_governor`) and restore it afterwards.

Tk's total ends when the X server has drawn the screen; Qt's when the frame is presented. Both
include building the screen; Tk's doesn't include the compositor's frame, which adds up to one
refresh interval (16.7 ms at 60 Hz).

## Start-up, Qt UI

With `ZYNTHIAN_QT_TIMING=1` zynthian also logs its start, in seconds from the process start
(`/proc/self/stat`):

```
QML TIMING QML load starts at process +1.37 s      <- imports, state manager, models done
QML TIMING engine.load 58 ms (done at process +1.43 s)
QML TIMING first frame at process +1.48 s          <- QQuickWindow.frameSwapped
```

`engine.load` compiles the QML (or maps it from the disk cache) and creates the items the first
frame needs; the rest of the UI (Deferred.qml: the other screens, widget views, keypad, launcher
pads) is created after the first frame, in the event loop's idle time.

To compare starts, restart the UI (`RESTART_UI`, e.g. `tools/sync_ui.sh -R` or the OSC
message it sends) a few times and take the median:

- **warm**: the usual start, the QML from the disk cache. Qt keeps it in
  `$XDG_CACHE_HOME/zynthian/zynthian/qmlcache` (`~/.cache/...` without `XDG_CACHE_HOME`; the
  application and organisation name are "zynthian"), one `.qmlc` per QML file, named by the SHA-1
  of its path. Qt 6.12 validates them by the source's content checksum, not its time stamp: a
  `sync_ui.sh` or a package upgrade only recompiles the files whose content changed.
- **no cache**: `export QML_DISABLE_DISK_CACHE=1` in `zynthian_envars.sh` (and `unset
  QML_DISABLE_DISK_CACHE` to go back: the launcher keeps what it exported, see the hot reload
  section of qt-theme-development.md). Each start compiles everything, nothing is written.
- **cold**: the cache directory removed (and the page cache dropped: `sync; echo 3 | sudo tee
  /proc/sys/vm/drop_caches`): the first start after an install; it compiles and writes the cache.
- Whether the cache is used: `export QT_LOGGING_RULES="qt.qml.diskcache.debug=true"` logs each
  file that is missing from or rejected by the cache ("No pre-compiled unit found" is the lookup
  of compiled-in units and appears always; "Error loading ... from disk cache" means a miss). The
  directory must exist and be writable by zynthian's user (`HOME` set; services without a login
  session).
- A slow device in the VM: `taskset -a -p 1 <launcher pid>` before `RESTART_UI` pins the next
  zynthian to one CPU (the launcher's children inherit it). On the fast host this changed
  nothing (the load is single-threaded); the ARM boards are what count.
- Where the time goes inside `engine.load`: the QML profiler. Install `qt6-qtdeclarative-dev`
  (`/usr/lib/qt6/bin/qmlprofiler`), start zynthian with QML debugging and the profiler service
  (`QQmlDebuggingEnabler.enableDebugging(True)` before the `QGuiApplication`, and
  `-qmljsdebugger=port:3768,block,services:CanvasFrameRate,EngineControl,DebugMessages` in
  `sys.argv`; `CanvasFrameRate` is the profiler's service name), then
  `qmlprofiler --interactive --attach 127.0.0.1 -p 3768 -o trace.qtd`, and after the start type
  `r` (stop recording), `o` (write the file), `q`, `y`. The trace is XML: ranges per event type
  (Compiling, Creating, Binding, Javascript) and file. Debugging slows QML down; use it for
  shares, not for absolute times.
- Don't compile Main.qml with a `QQmlComponent` before `engine.load()` to time the two apart:
  `QQmlApplicationEngine` creates its file selector in `load()`, so that component ignores the
  theme's selectors (the UI came up in tk).

Measured in the QEMU VM (x86_64 host, 480x320, `001-Parity Test`, median of 3-4 starts), before
and after the deferred loading (zynthian-stuff `results/2026-11-18-s3neo-zynthian-startup.md`,
"QML load"):

| theme, start | engine.load | load start to first frame |
|---|---|---|
| tk warm | 152 -> 59 ms | 255 -> 115 ms |
| tk no cache | 213 -> 107 ms | 320 -> 170 ms |
| tk cold | 289 -> 194 ms | 400 -> 255 ms |
| v4 warm | 165 -> 68 ms | 275 -> 130 ms |

## On the desktop

`desktop/preview_qt.sh` runs the Qt UI with zynthian's real backend in a headless labwc at the
Duet's 1920×1200 and scale 2, with `ZYNTHIAN_QT_TIMING=1`; `-s CUIA` sends CUIAs and takes
screenshots. The times are in `/tmp/zynthian-qt.log`:

```sh
desktop/preview_qt.sh -w 20 -s main_menu -s screen_audio_mixer -s main_menu
grep "SCREEN TIMING" /tmp/zynthian-qt.log
```

Desktop numbers are only useful relative to each other (finding regressions), not for the device.

## Qt Quick without zynthian (spike)

`zynqt/spike/spike.py` (M0) measures Qt Quick alone: a mock mixer with 16 strips and meters fed
from Python, a long list and the keypad. On the device, in a running Wayland session:

```sh
cd zynqt/spike   # copied to the device
WAYLAND_DISPLAY=wayland-0 QT_QPA_PLATFORM=wayland taskset -c 4-7 \
	python3 spike.py --fullscreen --bench 30 --meter-hz 30 --no-switch
```

It prints every 5 s the frame rate, the Python time per meter update (and how much of it the QML
bindings take) and, without `--no-switch`, the time from each screen switch to the next frame.
Measure the CPU meanwhile with `tools/thread_cpu.sh -p "^python3 spike.py"`.

## Pitfalls

- `pgrep -f PATTERN` over SSH also matches the SSH shell running the command (its command line
  contains the pattern); killing what it finds ends the session. Write patterns that don't match
  themselves (`"[z]ynthian_qt_main"`), as the tools do.
- BusyBox `pgrep` (Nura) has no alternatives in patterns (`a|b`).
- Restarting tinydm restarts whatever kiosk session is the default (`readlink
  /var/lib/tinydm/default-session.desktop`), not necessarily zynthian's.
- `python3 -m compileall` over the whole `zyngine` directory fails on an upstream example file
  with a syntax error; compile the changed files only.
