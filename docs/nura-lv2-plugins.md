# LV2 plugins on Nura: state and plan

Status: 2026-11-05, measured on the Lenovo Duet (Nura edge, aarch64, musl). Phase 1 of the plan
done: 144 of the 313 default plugins installed and loading (from 36 before).

zynthian's default engine configuration (`zynthian-sys/config/engine_config.json`) lists 1300
LV2 plugins, **313 of them enabled by default** (the rest are installed on ZynthianOS but
switched off). This document records which of the 313 a Nura install provides, and how to get the
rest.

## How it was measured

`nura/tools/lv2-coverage.py` compares the enabled plugin URIs of zynthian's default
`engine_config.json` with the plugins lilv finds on the device; `--missing` lists the missing ones by
project, `--load` dlopens every LV2 library (unresolved symbols) and instantiates the enabled
plugins that need no host features:

```sh
ssh jeff@kick-duet.local python3 - --missing --load < nura/tools/lv2-coverage.py
```

Plugins that need host features (`urid:map`, `options`, ...) only show they load; start them in
jalv on PipeWire (`jalv -n test -i URI </dev/null`: exit status 0, no "Failed to instantiate").

After installing plugins, zynthian has to rescan them (it takes the enabled state from its
defaults):

```sh
cd /usr/share/zynthian/zynthian-ui/zyngine && python3 ./zynthian_lv2.py engines
```

with zynthian's environment (`ZYNTHIAN_DIR`, `ZYNTHIAN_LIB_DIR`, `PYTHONPATH` as in
`/usr/bin/zynthian`, then `desktop/zynthian_desktop_env.sh`), then restart the session.

## Installed: 180 of 313

All pulled in by the meta package `zynthian-lv2-plugins` (`nura/lv2/`), which
`postmarketos-ui-zynthian` depends on. From Alpine:

| Package | Enabled zynthian plugins it provides |
|---|---|
| `x42-plugins` | 36 of 43 (missing: the AVL drumkits, which are the separate project avldrums.lv2, and x42 Whirl, which comes with setBfree) |
| `calf-lv2` | 26 of 27 (Wavetable missing in Alpine's build) |
| `zam-plugins-lv2` | 8 |
| `amsynth-lv2` | 1 |

`mda-lv2` is installed too, but it is drobilla's MDA with `http://drobilla.net/plugins/mda/` URIs;
zynthian enables the MOD fork's (`http://moddevices.com/plugins/mda/`), now packaged as
`mod-mda-lv2` (bundles `mod-mda-*.lv2`, no conflict with drobilla's `mda.lv2`). After a rescan 18 of
drobilla's were enabled too (why, not checked).

Packaged in `nura/lv2/` (phase 1, built and tested on the Duet):

| Package | Enabled zynthian plugins | Notes |
|---|---|---|
| `mod-mda-lv2` | 18 | MOD's MDA fork; built without its waf |
| `mod-utilities-lv2`, `mod-distortion-lv2`, `mod-pitchshifter-lv2` | 17 | pitch shifters with an empty FFTW wisdom file |
| `swh-lv2` | 11 | `-fgnu89-inline` |
| `mod-caps-lv2` | 6 | musl integer types |
| `mod-tap-lv2` | 6 | without `-Werror` |
| `invada-lv2` | 5 | Debian's source and patches, without the GTK 2 GUIs |
| `infamous-lv2` | 3 | without GUIs (NTK isn't packaged) |
| `shiro-lv2` | 3 | built against a newer DPF, modgui off |
| `artyfx-lv2` | 2 | without GUI and SSE |
| `abgate-lv2`, `bolliedelay-lv2`, `ykchorus-lv2` | 3 | DSP only |
| `setbfree` (`nura/engines/`) | 2 | x42 Whirl (b_whirl); also zynthian's setBfree engine |
| `fluidplug-lv2` (+ `-data`) | 19 (of 23) | SoundFont instruments, zynthian's fork with the SoundFonts (284 MB in `-data`); FluidGM left out (no SoundFont in the fork); `-fpermissive`; optional |
| `avldrums-lv2` (+ `-data`) | 5 | x42 AVL Drumkits (145 MB in `-data`), without GUI and x86 flags; optional |
| `dpf-plugins-lv2` | 7 | DPF-Plugins 1.7, DSP only (`lv2_dsp` per plugin), without ProM/glBars |
| `dragonfly-reverb-lv2` | 4 | Dragonfly Reverb 3.2.10 (release source with DPF), DSP only |

Before 2026-11-05 the kiosk package depended on `calf` instead of `calf-lv2` (Alpine puts the LV2
plugins in a subpackage): none of the Calf plugins were installed. Fixed in `abd64c11`.

Available in Alpine but **not** in zynthian's defaults (all disabled there): `lsp-plugins-lv2`
(0 of 194 enabled), `airwindows-lv2` (0 of 187), `noise-repellent`, `bankstown-lv2`. Not
installed.

## Missing: 133

None of these are packaged in Alpine. Source: how ZynthianOS gets them (Debian/KXStudio package
from `setup_plugins_rbpi.sh`, a recipe in `zynthian-sys/scripts/recipes/`, or a prebuilt binary).

| Project | Missing | Type | ZynthianOS source | Build | Notes |
|---|---|---|---|---|---|
| Guitarix + GxPlugins | 59 | effects (amps, pedals) | recipes `install_guitarix.sh` (`--mod-lv2 --no-standalone`), `install_gxplugins.sh`; Debian `gxplugins` | waf; make | largest group; Guitarix needs Boost, glibmm, fftw, lilv, zita-convolver/resampler |
| DISTRHO-Ports (JUCE) | 6 | TAL effects, Vex | Debian `distrho-plugin-ports-lv2`, recipe `install_distrho_ports.sh` | meson, JUCE (legacy) | long build |
| EQ10Q | 8 | EQs, compressors | Debian `eq10q`, recipe `install_eq10q.sh` | cmake | GUI (gtkmm) to switch off |
| Dusk Audio | 6 | effects, synth | prebuilt only (`install_dusk_*_prebuilt.sh`) | JUCE | sources to check; prebuilt glibc binaries can't run on musl |
| CHOW | 4 | effects (Centaur, Phaser, Tape) | recipes (source and prebuilt) | JUCE, cmake | |
| jpcima | 4 | String machine, MiniOPL3 | recipes `install_string-machine.sh`, `install_miniopl3.sh` | make (DPF) | |
| QMidiArp | 2 | MIDI tools | Debian / recipes | cmake | |
| rncbc synths | 3 | padthv1, samplv1, synthv1 | Debian `*-lv2` | cmake, Qt | GUI-less build |
| Synths (JUCE and others) | ~20 | Surge XT, Monique, Odin2, Vaporizer2, OB-Xd, Dexed, Helm, TAL-NoiseMaker, JC303, KR-106, RipplerX, MiMi-d, Mutated Instruments, Triceratops, Foo YC20, SO-kl5, Fabla, … | recipes, some prebuilt only | mostly JUCE, cmake | long builds; check each on aarch64/musl |
| Single plugins | ~22 | AIDA-X, Neural Amp Modeler, Aether, Argotlunar2, Temper, Roboverb, Ratatouille, TalentedHack, Regrader, SAFE, gula, Luftikus, ChaosChimp, Granulator (Faust), AMS Bitgrinder, The Pilgrim, Punk Console, Calf Wavetable, … | Debian / recipes / prebuilt | various | AIDA-X and NAM need RTNeural/Eigen and are CPU-heavy |

(The full list, plugin by plugin: regenerate with the measurement above; the table groups it.)

## Plan

### Principles

- **Same URIs as ZynthianOS.** Snapshots, presets and the engine configuration refer to plugin URIs.
  Build the forks zynthian uses (MOD's MDA/CAPS/TAP, `zynthian/FluidPlug`), not other variants.
- **Source builds only.** ZynthianOS's prebuilt binaries are glibc/Raspberry Pi builds; on musl
  they don't load. Plugins that only exist as binaries stay out until there is a source.
- **No plugin GUIs.** The kiosk has no X11/GTK plugin windows: build with UIs off (`nogui`,
  `--no-lv2-gui`, DPF `HAVE_OPENGL=false`, …). Fewer dependencies, faster builds.
- **Generic CPU flags.** Drop the x86 flags several builds set (`-msse`, `-mfpmath=sse`, as the
  zynthian recipes do with `sed`); `-mcpu=cortex-a73` as in Zrythm's Nura build, or Alpine's
  default.
- **Upstream where it fits.** Generic projects (SWH, Dragonfly, DPF-Plugins, Invada, Guitarix,
  avldrums, setBfree, …) belong in Alpine's aports; zynthian-specific forks (MOD MDA/CAPS/TAP,
  FluidPlug fork) stay in `nura/`.

### Layout

- One APKBUILD per upstream project in `nura/lv2/<project>/`, linked into pmaports with the
  other `nura/` packages; normal `$source` tarballs (GitHub archives) pinned to the version or
  commit the zynthian recipe uses, with checksums. These are ordinary pmbootstrap builds (no
  `--src`).
- Package names as Alpine would name them (`swh-lv2`, `dragonfly-reverb-lv2`, `mod-mda-lv2`, …),
  installing to `/usr/lib/lv2`.
- A meta package `zynthian-lv2-plugins` depending on all of them; `postmarketos-ui-zynthian`
  depends on the meta package. Data-heavy ones (FluidPlug soundfonts, AVL drumkits) as separate
  packages the meta package may only recommend (install_if or optional), to keep images small.
- `nura/tools/lv2-coverage.py`: the measurement above as a tool (counts, missing by project), to
  run after each batch.

### Phases

| Phase | Projects | Plugins | Effort |
|---|---|---|---|
| 1. Small C/C++ effects (**done**) | MOD MDA, MOD utilities/distortion/pitchshifter, CAPS, TAP, SWH, Invada, infamous, SHIRO, artyfx, abGate, Bollie Delay, YK Chorus | 73 | one day, see "Phase 1: lessons" |
| 2. DPF family | DPF-Plugins, Dragonfly Reverb (**done**); string-machine, MiniOPL3 | ~20 | DSP only per plugin, as ykchorus |
| 3. Guitarix | Guitarix (`--mod-lv2 --no-standalone`), GxPlugins | 59 | 2–4 days: waf, Boost/glibmm, musl fixes likely |
| 4. Instruments with data (**done**) | FluidPlug, avldrums, setBfree (also as engine) | 26 | SoundFonts in optional `-data` packages, not in images |
| 5. EQ10Q, QMidiArp, rncbc synths | EQ10Q, QMidiArp, padthv1/samplv1/synthv1 | ~13 | 1–2 days: cmake, GUIs off |
| 6. JUCE | DISTRHO-Ports (TAL, Vex), CHOW, Surge XT, Odin2, OB-Xd, Dexed, Helm, Monique, Vaporizer2, … | ~30 | 1–2 weeks: long builds (under qemu: hours each), JUCE on musl, check each |
| 7. Neural and the rest | AIDA-X, NAM, Dusk (if sources), single plugins | ~25 | case by case |

After each phase: build, install on the Duet, rescan, measure coverage, and load each new plugin
once (`nura/tools/lv2-coverage.py --load`, and jalv for the ones that need host features) to catch
missing symbols and crashes; `lv2lint` for the TTL.

### Phase 1: lessons

Built with abuild on the Duet itself (the target: aarch64, musl), which takes seconds to minutes per
package and needs no sudo on the host; pmbootstrap builds the same APKBUILDs for images. Setup on
the device: `sudo apk add alpine-sdk`, `sudo addgroup $USER abuild`, `abuild-keygen -a -n -i`; then
in a copy of `nura/lv2/<pkg>`: `abuild checksum && abuild -r`, and
`sudo apk add -u --repository ~/.local/share/abuild/aports <pkg>` (`-u`: `apk add` alone doesn't
upgrade an installed package to a new pkgrel).

Problems found, and how the packages handle them:

- **Old waf** (MOD's MDA: waf 1.7, a self-extracting script) doesn't start on Python 3.12+
  ("source code cannot contain null bytes"), and autowaf isn't packaged: `build()` compiles one
  module per plugin as the wscript does.
- **glibc-only types**: CAPS uses `__int16_t` and friends; musl has only the standard `int16_t`.
- **C99 inline**: SWH declares helpers `inline` (GNU89 meaning). With Alpine's `-Os` not every call
  is inlined, no external definition exists, and the library doesn't load ("partition: symbol not
  found", Signal sifter): `-fgnu89-inline`. glibc distributions build with `-O2`/`-O3`, which hides
  it.
- **`-Werror`** in TAP's flags: removed.
- **Old DPF**: SHIRO's DPF (2020) builds, but the plugins don't instantiate in jalv ("Failed to
  instantiate plugin", without a reason; jalv then crashes). Built against the newer DPF of YK Chorus,
  with the MOD web GUI description off (`DISTRHO_PLUGIN_USES_MODGUI 0`; the newer DPF needs more
  settings for it, and the old bundles referred to a `modgui.ttl` that wasn't installed).
- **DPF as a git submodule**: GitHub's archives don't contain submodules; DPF is a second source at
  the right commit. DPF's top-level `all` builds the GUI library (and needs pugl, another submodule):
  build `lv2_dsp` per plugin, then the TTL generator.
- **Build-time FFTW wisdom**: MOD's pitch shifters generate exhaustive FFTW wisdom for 34 sizes
  during the build (slow, and only valid on the machine that builds). Shipped empty: the plugins fall
  back to FFTW_ESTIMATE plans. Better plans: generate system wisdom on the device once
  (`fftwf-wisdom`, from Alpine's `fftw`; the plugins import the system wisdom first).
- **x86 flags**: the MOD Makefiles add `-msse -mfpmath=sse` unless `NOOPT=true`; ArtyFX has
  `BUILD_SSE=OFF`; infamous checks whether the compiler takes them.
- **Testing**: lilv's instantiate without host features fails for every plugin that requires
  `urid:map` or `options` (most DPF and x42 plugins); that says nothing. dlopen with `RTLD_NOW`
  finds unresolved symbols, jalv on PipeWire tests the rest.

### Optional data (TBD)

Large sample data is kept out of device images: `fluidplug-lv2` and `avldrums-lv2` put their
SoundFonts into `-data` subpackages (284 and 145 MB), and neither is in `zynthian-lv2-plugins`.
The plugin packages depend on their data, so `apk add avldrums-lv2` installs a working instrument.

- **TBD: admin menu entry** in zynthian to install (and remove) optional data packages on the
  device (apk, with progress and the download size), then rescan the LV2 plugins
  (`zynthian_lv2.py engines`). Until then: `apk add` over ssh.
- **Other heavy packages** (installed sizes on the Duet): `zynaddsubfx` 53 MB (its banks),
  `pd-cyclone` 22 MB, `mod-caps-lv2` 26 MB, and `zynthian-data` 616 MB:
- **TBD: split `zynthian-data`** into essential (or too small to matter) and extra data. Measured
  (MB): `presets/puredata/sampler` 180 (Pd sampler patches with samples), `tts/voices` 140 (ZynVoice
  voices; TTS is off by default), `files/Neural Models` 113 (NAM/AIDA-X models; those plugins aren't
  packaged yet), `presets/puredata/synth` 72, `presets/lv2` 70 (plugin presets: essential),
  `files/Midi` 67 (MIDI files), `aeolus` 44 (Aeolus engine, not packaged), the rest about 30
  (setBfree, zynseq, snapshots, Organelle abstractions, other presets: essential). Proposal:
  `zynthian-data` (essential, ~100 MB with the LV2 presets) plus optional `zynthian-data-pd-samples`,
  `-tts`, `-nam-models`, `-midi`, `-aeolus` (the latter with the Aeolus engine), installable from the
  admin menu above. Check what zynthian expects to exist (e.g. TTS, the MIDI player's file list)
  when a part is missing.

### Open questions

- **Build time under qemu:** JUCE plugins and Guitarix take long when pmbootstrap emulates
  aarch64. Options: pmbootstrap's cross-compilation (crossdirect) where the build allows, or
  building on an aarch64 machine.
- **Image size:** soundfonts and drum samples are hundreds of MB. Optional data packages, or a
  download on first use as ZynthianOS does for some.
- **MDA:** drobilla's `mda-lv2` and MOD's fork are both installed (no file conflict); drop
  drobilla's from the meta package if its duplicate entries in zynthian's lists are a nuisance.
- **FFTW wisdom** for the pitch shifters: generate it on the device (see Phase 1: lessons).
- **Licences:** most are GPL/LGPL/ISC; check the few with unclear terms before adding them to an
  image.
- **SooperLooper:** zynthian runs SooperLooper as its own engine (`zynthian_engine_sooperlooper`:
  the `sooperlooper` binary, controlled over OSC, with the `zynthian_widget_sooperlooper` widget),
  not as a plugin. Better to make it work with the SooperLooper LV2 version
  (`sooperlooper.lv2`, AUR `sooperlooper.lv2-git`) through the jalv engine: one fewer separate
  program and OSC link, chains and snapshots like any other plugin, and no wxWidgets-era
  package to build for Nura. Needs a look at what the engine and widget use (loop state,
  positions, multiple loops) and whether the LV2 version exposes it as ports. Meanwhile the
  widget is ported to the Qt UI for the current engine (5bce848a; desktop: AUR `sooperlooper-headless`).
- **Pure Data:** the puredata engine (`zynthian_engine_puredata`, patches in
  `zynthian-data/presets/puredata`) needs `pd` and the externals the patches declare from
  `/usr/lib/pd/extra`: cyclone, iemlib, osc (`packOSC`/`unpackOSC`, which zynthian's OSC
  controllers use), hcs, ggee (ZynthianOS: Debian's `puredata` and `pd-*` packages). Alpine
  packages neither Pure Data nor these externals (its `cyclone` is a Scheme compiler), so the
  Duet has no puredata engine yet: package `pd` (vanilla) and the externals (pd-lib-builder,
  sources on GitHub) in `nura/`, with a `/usr/lib/pd/extra` layout so the patches' absolute
  `declare -path` lines work. Some patches also declare
  `/zynthian/zynthian-data/puredata/organelle` (ZynthianOS path).
  On the desktop (Arch: `pd`, but no externals in the repos or the AUR) they come from Pure
  Data's package manager deken: the Linux-amd64 builds of cyclone, iemlib, osc, hcs and ggee
  unpacked into `~/Documents/Pd/externals`, and `~/.pdsettings` adding each library folder to
  pd's search path (`npath: 5`, `path1: ~/Documents/Pd/externals/cyclone`, …), since the patches
  only declare the `/usr/lib/pd/extra` folders. Checked with EuclidSeq6: no "couldn't create".
  Some Organelle patches also use `abl_link~` (Ableton Link; on the desktop from deken too,
  `abl_link~[v0.6](Linux-amd64-32)`, `path6`) and zynthian's own `clocker`, `clockfill`, `midiclocker`, which exist
  only as prebuilt arm64 glibc binaries in `zynthian-data/puredata/pd-externals-arm64`: no
  x86_64 build, and on musl (Nura) they won't load either; their sources are needed. Without
  them those patches run but lose Link/MIDI clock sync.
- **Pure Data on Nura (2026-11-05): done.** Packaged from source in `nura/pd/`, built and tested
  on the Duet; the meta package `zynthian-puredata` (a dependency of `postmarketos-ui-zynthian`)
  pulls in `puredata` 0.57.0 (`-nogui`, JACK, ALSA MIDI; Alpine only has libpd) and the externals,
  all in `/usr/lib/pd/extra`: `pd-cyclone`, `pd-iemlib`, `pd-ggee`, `pd-hcs`, `pd-osc`,
  `pd-freeverb`, `pd-unauthorized` ([grid]), `pd-midifile`, `pd-tb-peakcomp`, `pd-grids`
  (Mutable Instruments Grids), `pd-plaits` ([plts~], Mutable Instruments Plaits), `pd-abl-link`
  (Ableton Link, with Link and asio; Link uses asio on Linux too), `pd-clocker` (clocker,
  clockfill, midiclocker from Owen Osborn's sources, BSD-3-Clause, instead of zynthian-data's
  arm64/glibc binaries). All 116 patches in `zynthian-data/presets/puredata` load headless without
  a missing object; in zynthian (Qt UI on the Duet) an Organelle patch loads and plays.
  Fixes: old C with GCC 14+/15 (`-std=gnu17 -fpermissive`); Pd 0.55+ no longer declaring `error()`
  and `COSTABSIZE` (a compat header, also for C++; pd still exports them, `cos_table` with 512
  entries); Pd 0.57 asserting `t_float` for the signal inlet field (tb_peakcomp~); hcs' stat on
  musl; iemlib's objects linked to its library binary; `linux-headers` for asio.
  Engine: cyclone 0.9 loaded with `declare -lib cyclone` no longer adds its folder for its single
  objects ([split]); `zynthian_engine_puredata` adds every library folder of pd's system `extra`
  directory to the search path when zynthian-data is not in the ZynthianOS location (like the
  Organelle path). Pd's settings for the desktop (deken externals in `~/Documents/Pd/externals`)
  are described above.
- **Engines (2026-11-05):** `nura/engines/zynaddsubfx` (3.0.6, release tarball with rtosc and the
  banks, no GUI; GCC 13+ needs `-include cstdint`, OSS headers from `linux-headers`; banks in
  `/usr/share/zynaddsubfx/banks`, where zynthian-data's `zynbanks` symlink points) and
  `nura/engines/setbfree` (0.8.17, no UI, without the x86 flags; its LV2 plugins too), both
  dependencies of `postmarketos-ui-zynthian`: zynthian's ZY and BF engines are available on Nura.
- **CPU:** some plugins are too heavy for the Duet's A73 cores at a 256-frame quantum (neural amp
  models, Surge XT with many voices); enable them, but expect limits.
