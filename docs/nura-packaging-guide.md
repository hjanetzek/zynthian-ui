# Packaging plugins and engines for Nura: problems and patterns

Status: 2026-11-06. What went wrong while packaging zynthian's LV2 plugins, Pure Data externals
and engines for Nura (postmarketOS, aarch64, musl, GCC 15), and how the packages in `nura/lv2/`,
`nura/pd/` and `nura/engines/` deal with it. Read this before packaging the next plugin; the
state of the plugins themselves is in [nura-lv2-plugins.md](nura-lv2-plugins.md).

## Workflow

- **Build on the Duet with abuild**, not under qemu: seconds to minutes per package, no sudo on
  the host. `abuild checksum && abuild -r` in a copy of the package directory, then
  `sudo apk add -u --repository ~/.local/share/abuild/aports <pkg>` (`-u`: `apk add` alone keeps
  an installed older pkgrel). The images are built from the same APKBUILDs with pmbootstrap.
- **One build at a time.** Two abuild runs of the same package share `src/`, the log and the
  `.makedepends-<pkg>` virtual package: the one that ends first removes the build dependencies
  of the other (seen: `meson: not found` in `package()` after a successful compile). Queue builds
  (one after another, keep going on failure) instead of starting a second one.
- **Long builds in the background, without a time limit.** Killing the local ssh client kills the
  remote abuild (SIGHUP). If one is orphaned: find its PID and `kill` it; never `pkill -f` a
  pattern that also appears in your own ssh command line (it kills that shell). Afterwards remove
  leftover `.makedepends-*` virtual packages (`apk info | grep '^\.makedepends'`).
- **`rootpkg` doesn't index**: after re-running only the packaging step
  (`abuild deps && abuild rootpkg`), run `abuild index` before `apk add`.
- **The network can be missing** right after the Duet resumes ("bad address", checksum failed):
  wait for DNS (`getent hosts github.com`), then retry. Transient DNS failures also happen
  mid-session; retry before debugging.
- **Installing build dependencies can upgrade the system.** `mesa-dev` and other `-dev` packages
  pin exact versions, so installing them (directly, or through Qt's `-dev` packages) upgrades Mesa
  and systemd. `apk add --simulate` first, and check for `Upgrading`. Packages installed outside
  the distribution (Qt 6.12 from the Zrythm build) need their own `-dev` packages from the
  pmbootstrap repository (`~/postmarketos/kick-pi4/packages/edge/aarch64/`), or apk falls back to
  Alpine's older version and downgrades.
- **The Duet isn't a clean build environment**: bash, python3, git, cmake and gettext-dev are
  installed there anyway, so a missing makedepends doesn't show until CI (pmbootstrap's minimal
  chroot): `/bin/sh: .../generate-lv2.sh: not found` is a `#!/bin/bash` script without bash.
  Check the shebangs of the scripts the build runs (DPF's `generate-ttl.sh`, DISTRHO-Ports'
  `generate-lv2.sh`: bash) and list every tool the build calls.
  The same for headers: since the Qt 6.12 and `mesa-dev` installs, about 100 `-dev` packages are
  on the Duet as their dependencies (`linux-headers`, X11, cairo, glib, ...): xsimd's
  `<asm/hwcap.h>` (`linux-headers`) only failed in CI. List what the device has
  (`apk info | grep -- '-dev$'`) and don't trust a Duet build to prove the makedepends complete.
  Keep the Duet clean: build-only packages installed by hand go again after use (2026-11-06: the
  Qt dev stack, 134 packages, removed; Qt 6.12's `-dev` packages now come from the nura-builds
  repository, `https://github.com/hjanetzek/nura-builds/releases/download`, with its key in
  `/etc/apk/keys`, so abuild installs them as makedepends like CI). What stays installed and can
  still hide a missing makedepends: bash, python3, git (zynthian needs them).
  Add a makedepends only for a cause you have seen (the error, or the build log compiling the
  file that needs it: `juce_opengl.cpp` for mesa-dev, xsimd for linux-headers), not to every
  similar package on suspicion.
- **Rebuilding without a pkgrel bump installs nothing**: `apk add -u` keeps an installed package of
  the same version, so a fix tested that way tests the old files. Bump pkgrel for every rebuild
  that is installed and tested.
- **Memory**: JUCE's amalgamated translation units need about 1 GB each; with 8 jobs on the Duet's
  4 GB the compiler is killed (`Killed signal terminated program cc1plus`). `cmake --build build
  --parallel 3` for the JUCE packages.
- **`apk add -u` upgrades dependencies too**, and every apk run executes pending triggers. A failing
  trigger makes apk exit with an error, and then every later abuild stops at `builddeps failed`.
  Seen: `postmarketos-mkinitfs` failing on a missing `/usr/lib/udev/rules.d/10-dm.rules` after
  `device-mapper-udev` disappeared (fixed by installing it again). Run `sudo apk fix` to see the
  trigger's output, and fix the system before rebuilding.
- **After installing plugins**, zynthian must rescan (`zynthian_lv2.py engines` with zynthian's
  environment; see nura-lv2-plugins.md), then restart the session
  (`sudo systemctl --no-block restart tinydm`; without `--no-block` it dies with the ssh session).

## Sources

GitHub's archive tarballs don't contain git submodules, and pmbootstrap builds have no network.

- **Prefer a release tarball that includes the submodules** when the project publishes one:
  GxPlugins (`gxplugins_1.0_src.tar.bz2`, 43 submodules), Surge XT (`surge-src-1.3.4.tar.gz` in
  `surge-synthesizer/releases-xt`), Guitarix (`guitarix2-*.tar.xz`). Avoid "Nightly" assets: they
  are replaced.
- **Otherwise one source per submodule**: `nura/tools/gh-submodule-sources.py OWNER/REPO REF`
  resolves the submodules recursively and prints the `_vars`, the `source` entries and the
  `prepare()` moves (outer submodules first). It uses the GitHub API: 60 requests per hour without
  a token, so run it with `GITHUB_TOKEN=$(gh auth token)`. Submodules outside GitHub (Eigen on
  GitLab) it only reports: add those by hand (`https://gitlab.com/OWNER/REPO/-/archive/SHA/REPO-SHA.tar.gz`).
- **CMake FetchContent** (JC303) downloads at configure time: give each dependency as a source and
  pass `-DFETCHCONTENT_FULLY_DISCONNECTED=ON -DFETCHCONTENT_SOURCE_DIR_<NAME>=...` (the name as
  declared, upper case).
- FetchContent can also sit in subdirectories (JC303's `src/dsp/guitarml-byod` fetches RTNeural,
  math_approx and Variant): grep every `CMakeLists.txt` for `FetchContent_Declare`, and give
  fetched projects their own submodules (RTNeural's xsimd).
- **Debian's source and patches** are a good base for old, unmaintained projects (EQ10Q, QMidiArp,
  Invada, SooperLooper): the `.orig` tarball and `debian/patches/` from deb.debian.org's pool,
  minus the patches for the GUI or packaging we don't build. Their patches can have CRLF files;
  copy them as they are.
- **Old DPF**: DPF's `generate-ttl.sh` from before ~2021 finds its generator relative to `$0`
  after a `cd`: call it by absolute path (`"$builddir"/dpf/utils/generate-ttl.sh`). Some old DPF
  versions build but don't instantiate (SHIRO): build against a newer DPF, with
  `DISTRHO_PLUGIN_USES_MODGUI 0`.

## Build: what to switch off

- **GUIs**: zynthian doesn't open plugin GUIs, and GUI toolkits drag in X11, GTK, NTK or Qt.
  - DPF: build `lv2_dsp` per plugin (`make -C plugins/X NOOPT=true HAVE_OPENGL=false lv2_dsp`),
    then `make -C dpf/utils/lv2-ttl-generator` and `dpf/utils/generate-ttl.sh`. If the plugin
    declares `DISTRHO_PLUGIN_HAS_UI 1`, set it to 0 in `prepare()`, or the TTL names a UI binary
    that isn't built.
  - waf/make projects: `--no-lv2-gui`, `nogui`, `--without-gui`, `--disable-*uis`.
  - DISTRHO-Ports: `-Dlinux-headless=true`.
  - JUCE plugins (CMake): the GUI is part of the plugin binary and can't be left out, so the X11,
    freetype and fontconfig headers are build dependencies (JUCE loads libX11 only when the editor
    opens). Build only the `<Target>_LV2` target and set the `FORMATS` list to LV2.
- **modgui**: MOD's web GUI resources (images, HTML) are useless on Nura; remove the `modgui/`
  directories in `package()` (70 MB for Guitarix and GxPlugins), keep `modgui.ttl` (the manifest
  refers to it).
- **x86 flags**: many Makefiles add `-msse -mfpmath=sse` or `-march=...` from `/proc/cpuinfo` or
  unconditionally: `NOOPT=true` (DPF/MOD), `SSE_CFLAGS=` (GxPlugins), `--disable-sse` (Guitarix),
  `BUILD_SSE=OFF` (ArtyFX), empty `CPU=`/`PLATFORM=` (Dexed: Cortex-A53 and `-mcmodel=tiny`).
- **Build-time measurements**: MOD's pitch shifters generate FFTW wisdom during the build (slow
  and only valid for the build machine): ship it empty.
- **Command-line make variables override `+=`**: `make CXXFLAGS=...` replaces the Makefile's own
  flags (include paths lost: `gx_pluginlv2.h: No such file`). Pass extra flags in the environment
  (`CXXFLAGS="$CXXFLAGS -include cstdint" make ...`), which the Makefile then appends to.
- **Data**: SoundFonts, samples and preset libraries go to a `-data` subpackage (FluidPlug,
  AVL drums), so images can leave them out; split further if part of it is optional (Surge XT:
  factory content needed, third-party patches optional).

## musl

| Symptom | Cause | Fix |
|---|---|---|
| `__int16_t` and friends unknown | glibc-internal type names | the standard names (`sed 's/__\(u\{0,1\}int[0-9]*_t\)/\1/g'`) and `#include <stdint.h>` (mod-caps-lv2) |
| `execinfo.h: No such file` | no `backtrace()` in musl; every JUCE version includes it | a stub header in `prepare()` (`backtrace()` returns 0) and `-I` to it; see the JUCE packages |
| `stat64`/`fstat64` incomplete type | musl 1.2.4+ has the LFS64 names only with `_LARGEFILE64_SOURCE` | `-D_LARGEFILE64_SOURCE` |
| `_NL_IDENTIFICATION_LANGUAGE`, `_NL_ADDRESS_LANG_AB`, ... undeclared | glibc locale items (JUCE's `getUserLanguage()`) | define them as items of a category musl doesn't have (`0x60000`...): `nl_langinfo()` returns "" |
| `static_cast<char>(NULL)` invalid | `NULL` is `nullptr` in C++ on musl | `0` (sed) |
| `fts.h: No such file` | fts is a separate library | `musl-fts-dev`, `LIBS=-lfts` |
| `soundcard.h`, `linux/...` missing | kernel headers aren't pulled in implicitly | `linux-headers` |
| `st_atimespec` | the code picks BSD field names unless `_POSIX_C_SOURCE` is defined, which glibc defines implicitly and musl doesn't | take the POSIX branch on Linux too (`\|\| defined(__linux__)`, pd-hcs) |
| a symbol "not found" when the plugin loads | see "C99 inline" below | |

## GCC 14/15 and current C/C++

| Symptom | Fix |
|---|---|
| `int32_t`, `uint8_t` not declared (C++) | `-include cstdint` (GCC 13+ no longer includes it indirectly) |
| `std::exchange` not a member of `std` (older JUCE) | `-include utility` |
| `... has no member named ...` `[-Wtemplate-body]` | GCC 15 checks templates that are never instantiated and makes it an error: `-Wno-template-body` |
| implicit `int`, implicit function declarations, incompatible pointer types (old C) | `-std=gnu17 -fpermissive` (GCC 14 made these errors; GCC 15 defaults to C23) |
| unresolved `inline` helper at load time ("symbol not found") | `-fgnu89-inline`: GNU89 `inline` code; Alpine's `-Os` doesn't inline every call, so no external definition exists (glibc distributions build with `-O2` and don't see it) |
| `Compatibility with CMake < 3.5 has been removed` (CMake 4) | `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| `lv2/lv2plug.in/ns/lv2core/lv2.h: No such file` (old JUCE LV2 wrappers, old plugins) | LV2 1.18 moved the headers to `lv2/core`, `lv2/atom`, ...: a symlink tree with the old paths in an `-I` directory (chow-matrix-lv2) |
| `jack/jack.h: No such file` (JUCE) | JUCE's audio device module builds JACK support on Linux: `jack-dev` |
| `#warning redirecting incorrect #include <sys/errno.h>` as an error | musl warns about non-standard headers; with the project's `-Werror` that's fatal: `-Wno-error=cpp` (Monique) |
| `internal compiler error: in write_symbol, at lto-streamer-out.cc` | GCC 15 LTO bug: drop the project's LTO flags (`juce::juce_recommended_lto_flags`, ChowMultiTool) |
| `-Werror` in the project's flags | remove it, or the project's switch (`SURGE_SKIP_WERROR`) |

## Packaging

- **Data subpackages**, named by what installs them:
  - `<pkg>-data`: data the plugin needs (Surge XT's factory patches, FluidPlug's and AVL's
    SoundFonts). It comes with the main package by `install_if="$pkgname=$pkgver-r$pkgrel"` in
    the subpackage, and resets `depends=""` (subpackages inherit the main package's `depends`).
    Not `depends="$pkgname-data"` in the main package: abuild accepts it, pmbootstrap can't order
    a package that depends on its own subpackage ("cyclical build dependency: can't build ...",
    "Can't resolve build order"). A subpackage depending on a sibling is fine.
  - `<pkg>-data-<what>` (`surge-xt-lv2-data-3rdparty`): optional data, which nothing depends on and
    no `install_if` pulls in; installed by hand (later by zynthian's admin menu). It may depend on
    `<pkg>-data`.
  - Images: whatever the meta packages pull in, with the `-data` of those packages. A plugin whose
    data is too big for images (FluidPlug, AVL drums) stays out of the meta packages; if it should
    be in images without its data, its data becomes `-data-<what>` instead.
- Bundle and file names can contain spaces (`Ultramaster KR-106.lv2`): copy with
  `find ... -exec cp -r {} dest \;`, not `for d in $(find ...)`.
- Optional parts of a build can reference targets that are switched off (Surge XT's pluginval
  targets query the effects bank, `SURGE_BUILD_FX=OFF`): comment out the include.

## BusyBox

Alpine's `/bin/sh` is BusyBox ash, and `sed`, `grep`, `find`, `install` are BusyBox applets unless
the GNU packages are installed. Scripts written for Debian (dash as `/bin/sh`, GNU tools) can work
differently:

- `echo` with backslashes: dash interprets escapes, ash doesn't. MiMi-d's fixup script left literal
  `\n` and `\t` in the TTL ("bad verb"): run it with `dash` (makedepends) and GNU `sed`.
- `install` options and `sed -i` edge cases (FluidPlug's install block, after a careless edit);
  `sed` `a\` text with escapes needs GNU sed.
- When a generated file is broken, look at it (`cat -A`) before suspecting the compiler.

## Pure Data externals

- Pd 0.55+ no longer declares `error()` and `COSTABSIZE`; pd still exports `error` and the 512-entry
  `cos_table`: a compat header via `-include`.
- Pd 0.57 asserts that the main signal inlet field is a `t_float` (a `double` field fails).
- cyclone loaded with `-lib` doesn't add its own directory to the search path: the puredata engine
  adds every directory in `/usr/lib/pd/extra` with `-path`.
- iemlib: one binary per object as symlinks to the library.
- pd-lib-builder is a submodule of most externals: an extra source.

## Testing

- `nura/tools/lv2-coverage.py --missing --load` on the device: which of zynthian's enabled plugins
  are installed, and a `dlopen(RTLD_NOW)` of every LV2 library (finds unresolved symbols).
- lilv's instantiate without host features fails for every plugin that requires `urid:map` or
  `options` (most DPF, JUCE, x42 plugins): that says nothing. Start those in jalv on PipeWire:
  `timeout 6 jalv -n test -i URI </dev/null`, exit status 0 and no "Failed to instantiate".
- A crash only at shutdown (jalv exits on EOF) may not show under gdb (timing); the core dump is in
  `coredumpctl`. Plugin libraries are stripped, so the trace names only the library and offset.
- Engines that aren't plugins (SooperLooper, setBfree, ZynAddSubFX): start them as the engine does
  (the command in `zyngine/zynthian_engine_*.py`), check their JACK ports (`pw-link -io`) and their
  control protocol (OSC ping), then load a chain in zynthian.
- zynthian enables an engine only if its program is found (`engine2program` and `shutil.which`
  in the chain manager): install the binary in `PATH`.

## Keeping up with upstream

`GITHUB_TOKEN=$(gh auth token) nura/tools/check-updates.py [--all]` checks each package's main
GitHub source: pinned commits against the default branch (or `_branch=` in the APKBUILD, e.g.
MiMi-d's `zynthian` branch), tags against the latest release and newest tag. Debian, SourceForge
and website tarballs are skipped, submodules aren't checked. Packages with updates are marked `*`.

## Licences and names

- Take the licence from the project's licence file, not from GitHub's detection (`NOASSERTION`
  for dual licences: Monique is `GPL-3.0-only OR MIT`; Odin 2 includes an OFL font).
- `pkgver` for untagged projects: `0_gitYYYYMMDD` (the commit date), `_commit` pinned.
- Name LV2 packages `<project>-lv2`, and add them to the meta package `zynthian-lv2-plugins`
  (bump its pkgrel); keep optional data packages out of the meta.
