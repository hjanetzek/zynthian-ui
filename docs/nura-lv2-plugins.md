# LV2 plugins on Nura: state and plan

Status: 2026-11-05, measured on the Lenovo Duet (Nura edge, aarch64, musl).

zynthian's default engine configuration (`zynthian-sys/config/engine_config.json`) lists 1300
LV2 plugins, **313 of them enabled by default** (the rest are installed on ZynthianOS but
switched off). This document records which of the 313 a Nura install provides, and how to get the
rest.

## How it was measured

The enabled plugin URIs from `engine_config.json`, compared with the plugins lilv finds on the
device (`py3-lilv`):

```python
import lilv
w = lilv.World(); w.load_all()
have = {str(p.get_uri()) for p in w.get_all_plugins()}
# enabled: the URLs of the entries with ENABLED in engine_config.json
print(sum(1 for u in enabled if u in have), "of", len(enabled))
```

After installing plugins, zynthian has to rescan them (it takes the enabled state from its
defaults):

```sh
cd /usr/share/zynthian/zynthian-ui/zyngine && python3 ./zynthian_lv2.py engines
```

with zynthian's environment (`ZYNTHIAN_DIR`, `ZYNTHIAN_LIB_DIR`, `PYTHONPATH` as in
`/usr/bin/zynthian`, then `desktop/zynthian_desktop_env.sh`), then restart the session.

## Installed: 71 of 313

From Alpine packages, all dependencies of `postmarketos-ui-zynthian`:

| Package | Enabled zynthian plugins it provides |
|---|---|
| `x42-plugins` | 36 of 43 (missing: the AVL drumkits, which are the separate project avldrums.lv2, and x42 Whirl, which comes with setBfree) |
| `calf-lv2` | 26 of 27 (Wavetable missing in Alpine's build) |
| `zam-plugins-lv2` | 8 |
| `amsynth-lv2` | 1 |

`mda-lv2` is installed too, but it is drobilla's MDA with `http://drobilla.net/plugins/mda/` URIs;
zynthian enables the MOD fork's (`http://moddevices.com/plugins/mda/`). After the rescan 18 of
drobilla's were enabled (why, not checked), so the MDA effects are there, but snapshots made on ZynthianOS
refer to the MOD URIs and don't find them.

Before 2026-11-05 the kiosk package depended on `calf` instead of `calf-lv2` (Alpine puts the LV2
plugins in a subpackage): none of the Calf plugins were installed. Fixed in `abd64c11`.

Available in Alpine but **not** in zynthian's defaults (all disabled there): `lsp-plugins-lv2`
(0 of 194 enabled), `airwindows-lv2` (0 of 187), `noise-repellent`, `bankstown-lv2`. Not
installed.

## Missing: 242

None of these are packaged in Alpine. Source: how ZynthianOS gets them (Debian/KXStudio package
from `setup_plugins_rbpi.sh`, a recipe in `zynthian-sys/scripts/recipes/`, or a prebuilt binary).

| Project | Missing | Type | ZynthianOS source | Build | Notes |
|---|---|---|---|---|---|
| Guitarix + GxPlugins | 59 | effects (amps, pedals) | recipes `install_guitarix.sh` (`--mod-lv2 --no-standalone`), `install_gxplugins.sh`; Debian `gxplugins` | waf; make | largest group; Guitarix needs Boost, glibmm, fftw, lilv, zita-convolver/resampler |
| FluidPlug | 19 | instruments (SF2 sound sets) | recipe `install_fluidplug.sh` (fork `zynthian/FluidPlug`) | make, downloads the SF2s | data-heavy (soundfonts); needs fluidsynth |
| MDA, MOD fork | 18 | effects, synths (DX10, JX10, ePiano) | recipe `install_mod-mda.sh` (`mod-audio/mda-lv2`) | waf (old, Python 3 fixes in the recipe) | URIs differ from Alpine's `mda-lv2`, see above |
| MOD plugins | 17 | effects (gain, crossover, filters, DS1, Big Muff, pitch shifters, harmonizer) | Debian `mod-utilities`, `mod-distortion`, `mod-pitchshifter` | make | pitch shifters need FFTW |
| SWH LV2 | 11 | effects | recipe `install_swh.sh` (`swh/lv2`) | make (generates code with XSLT) | |
| DPF-Plugins | 7 | effects, synths (3 Band EQ, MVerb, Ping Pong Pan, Kars, Nekobi, Ma*) | Debian `dpf-plugins`, recipe `install_dpf_plugins.sh` | make (DPF) | build without UIs |
| x42 extras | 7 | drumkits (5), Whirl (2) | recipes `install_avldrums.sh` (x42 binaries), `install_setbfree.sh` | make | avldrums: large sample data; setBfree is also a zynthian engine |
| CAPS, MOD fork | 6 | effects, generators | recipe `install_mod-caps.sh`; Debian `caps-lv2` | make | |
| TAP, MOD fork | 6 | effects | recipe `install_mod-tap.sh`; Debian `tap-lv2` | make | |
| DISTRHO-Ports (JUCE) | 6 | TAL effects, Vex | Debian `distrho-plugin-ports-lv2`, recipe `install_distrho_ports.sh` | meson, JUCE (legacy) | long build |
| EQ10Q | 8 | EQs, compressors | Debian `eq10q`, recipe `install_eq10q.sh` | cmake | GUI (gtkmm) to switch off |
| Dusk Audio | 6 | effects, synth | prebuilt only (`install_dusk_*_prebuilt.sh`) | JUCE | sources to check; prebuilt glibc binaries can't run on musl |
| Invada | 5 | effects, generator | Debian `invada-studio-plugins-lv2` | make | |
| CHOW | 4 | effects (Centaur, Phaser, Tape) | recipes (source and prebuilt) | JUCE, cmake | |
| Dragonfly Reverb | 4 | reverbs | Debian `dragonfly-reverb`, recipe `install_dragonfly.sh` (3.0.0 + patch) | make (DPF) | |
| jpcima | 4 | String machine, MiniOPL3 | recipes `install_string-machine.sh`, `install_miniopl3.sh` | make (DPF) | |
| infamous, SHIRO, artyfx, QMidiArp | 3, 3, 2, 2 | effects, MIDI tools | Debian / recipes | make, cmake | |
| rncbc synths | 3 | padthv1, samplv1, synthv1 | Debian `*-lv2` | cmake, Qt | GUI-less build |
| Synths (JUCE and others) | ~20 | Surge XT, Monique, Odin2, Vaporizer2, OB-Xd, Dexed, Helm, TAL-NoiseMaker, JC303, KR-106, RipplerX, MiMi-d, Mutated Instruments, Triceratops, Foo YC20, SO-kl5, Fabla, … | recipes, some prebuilt only | mostly JUCE, cmake | long builds; check each on aarch64/musl |
| Single plugins | ~25 | AIDA-X, Neural Amp Modeler, Aether, Argotlunar2, Temper, Roboverb, Ratatouille, TalentedHack, Regrader, SAFE, gula, Luftikus, ChaosChimp, Granulator (Faust), abGate, Bollie Delay, YK Chorus, AMS Bitgrinder, The Pilgrim, Punk Console, Calf Wavetable, … | Debian / recipes / prebuilt | various | AIDA-X and NAM need RTNeural/Eigen and are CPU-heavy |

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
| 1. Small C/C++ effects | MOD MDA, MOD utilities/distortion/pitchshifter, CAPS, TAP, SWH, Invada, infamous, SHIRO, artyfx, abGate, Bollie Delay, YK Chorus | ~80 | 2–4 days: make/waf, few dependencies |
| 2. DPF family | DPF-Plugins, Dragonfly Reverb, string-machine, MiniOPL3 | ~20 | 1–2 days: one build system, UIs off |
| 3. Guitarix | Guitarix (`--mod-lv2 --no-standalone`), GxPlugins | 59 | 2–4 days: waf, Boost/glibmm, musl fixes likely |
| 4. Instruments with data | FluidPlug, avldrums, setBfree (also as engine) | ~26 | 2–3 days: data packages, download sizes |
| 5. EQ10Q, QMidiArp, rncbc synths | EQ10Q, QMidiArp, padthv1/samplv1/synthv1 | ~13 | 1–2 days: cmake, GUIs off |
| 6. JUCE | DISTRHO-Ports (TAL, Vex), CHOW, Surge XT, Odin2, OB-Xd, Dexed, Helm, Monique, Vaporizer2, … | ~30 | 1–2 weeks: long builds (under qemu: hours each), JUCE on musl, check each |
| 7. Neural and the rest | AIDA-X, NAM, Dusk (if sources), single plugins | ~25 | case by case |

After each phase: build, install on the Duet, rescan, measure coverage, and load each new plugin
once (zynthian's `zynthian_lv2.test_lv2_plugin`, or jalv) to catch missing symbols and crashes;
`lv2lint` for the TTL.

### Open questions

- **Build time under qemu:** JUCE plugins and Guitarix take long when pmbootstrap emulates
  aarch64. Options: pmbootstrap's cross-compilation (crossdirect) where the build allows, or
  building on an aarch64 machine.
- **Image size:** soundfonts and drum samples are hundreds of MB. Optional data packages, or a
  download on first use as ZynthianOS does for some.
- **MDA URIs:** keep drobilla's `mda-lv2` next to the MOD fork, or replace it (both install
  `mda.lv2` bundles; the MOD fork's needs another bundle name or a conflict).
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
- **CPU:** some plugins are too heavy for the Duet's A73 cores at a 256-frame quantum (neural amp
  models, Surge XT with many voices); enable them, but expect limits.
