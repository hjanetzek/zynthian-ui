#!/bin/bash
#******************************************************************************
# ZYNTHIAN PROJECT: set up zynthian on desktop Linux
#
# Builds the native libraries, creates the Python venv and the user's config
# and data directories. Safe to run again: existing user files are kept.
#
#   desktop/setup_desktop.sh            everything
#   desktop/setup_desktop.sh build      only build zyncore, the zynlibs and zynthian's jalv
#   desktop/setup_desktop.sh jalv       only build zynthian's jalv (../jalv, branch asyncli)
#   desktop/setup_desktop.sh venv       only create/update the venv
#   desktop/setup_desktop.sh dirs       only create config and data dirs
#
# ZYNTHIAN_TK_WIDGETS=1 adds the Python packages of the Tk OpenGL widgets (audio file
# waveform), which the Qt UI doesn't need.
#
# Needs uv. System packages are not installed here; see desktop/README.md.
#******************************************************************************

set -e

source "$(dirname "${BASH_SOURCE[0]}")/zynthian_desktop_env.sh"

DESKTOP_DIR="$ZYNTHIAN_UI_DIR/desktop"

# Python packages for the venv, all installed with uv: the venv does not see the
# distribution's packages, so the desktop runs with a known set, kept in line with the
# Nura package's py3-* dependencies (nura/zynthian-ui/APKBUILD). PySide6 at the Qt
# version of the Duet (Zrythm's Qt 6.12 packages).
PY_PACKAGES=(
	"pyside6-essentials==6.12.*"   # the core modules, as the Duet's PySide6 build
	typing-extensions
	dbus-python
	cffi
	pillow
	numpy
	scipy
	psutil
	requests
	evdev
	pyudev
	pexpect
	pyyaml
	oyaml
	rdflib
	soundfile
	websocket-client
	alsa-midi
	Levenshtein
	ffmpeg-python
	pyrubberband
	sox
	wavio
	abletonparsing
	hwmon
	tkinterweb
	beautifulsoup4
	pyliblo3
	pyalsaaudio
	JACK-Client
	pyusb
)

# Tk OpenGL widgets (zynthian_widget_audio_file), optional: ZYNTHIAN_TK_WIDGETS=1
PY_PACKAGES_TK_WIDGETS=(
	moderngl
	moderngl-window
	pyopengltk
)

# check_dirs <dir>... => fail if one is missing
check_dirs() {
	local missing=0
	for d in "$@"; do
		if [ ! -d "$d" ]; then
			echo "Missing: $d (clone it next to zynthian-ui, see desktop/README.md)"
			missing=1
		fi
	done
	[ $missing -eq 0 ]
}

do_build() {
	# The build scripts configure with the default generator and run make
	unset CMAKE_GENERATOR
	echo "=== Building zyncore (no GPIO) ..."
	ZYNTHIAN_WIRING_LAYOUT=DUMMIES "$ZYNTHIAN_ZYNCODER_DIR/build.sh"
	echo "=== Building zynlibs ..."
	"$ZYNTHIAN_UI_DIR/zynlibs/build.sh" Release
	do_jalv
}

# zynthian's jalv (ZynthianOS: zynthian-sys/scripts/recipes/install_lv2_jalv.sh), only the
# JACK command line host the jalv engine runs; into ZYNTHIAN_SW_DIR, on PATH through
# zynthian_desktop_env.sh
do_jalv() {
	if [ ! -d "$ZYNTHIAN_JALV_SRC_DIR" ]; then
		echo "=== No $ZYNTHIAN_JALV_SRC_DIR: LV2 engines need zynthian's jalv, clone it with"
		echo "    git clone --recursive -b asyncli https://github.com/zynthian/jalv.git $ZYNTHIAN_JALV_SRC_DIR"
		return 0
	fi
	echo "=== Building zynthian's jalv ..."
	local build_dir="$ZYNTHIAN_SW_DIR/build/jalv"
	if [ ! -f "$build_dir/build.ninja" ]; then
		meson setup "$build_dir" "$ZYNTHIAN_JALV_SRC_DIR" --prefix="$ZYNTHIAN_SW_DIR" \
			-Djack=enabled -Dgtk3=disabled -Dqt5=disabled -Dportaudio=disabled -Dsuil=disabled -Dtests=disabled
	fi
	meson compile -C "$build_dir"
	meson install -C "$build_dir"
}

do_venv() {
	echo "=== Python venv in $ZYNTHIAN_VENV_DIR ..."
	if [ -f "$ZYNTHIAN_VENV_DIR/pyvenv.cfg" ] && grep -q "include-system-site-packages = true" "$ZYNTHIAN_VENV_DIR/pyvenv.cfg"; then
		# An older venv that saw the distribution's packages: recreate it
		echo "Recreating the venv without system site-packages ..."
		rm -rf "$ZYNTHIAN_VENV_DIR"
	fi
	if [ ! -x "$ZYNTHIAN_VENV_DIR/bin/python3" ]; then
		mkdir -p "$(dirname "$ZYNTHIAN_VENV_DIR")"
		# The system Python for its tkinter; its site-packages stay out of the venv
		uv venv --python /usr/bin/python3 "$ZYNTHIAN_VENV_DIR"
	fi
	local packages=("${PY_PACKAGES[@]}")
	if [ "${ZYNTHIAN_TK_WIDGETS:-0}" = 1 ]; then
		packages+=("${PY_PACKAGES_TK_WIDGETS[@]}")
	fi
	uv pip install --python "$ZYNTHIAN_VENV_DIR/bin/python3" "${packages[@]}"

	# lilv's Python bindings are one ctypes module, not on PyPI and not packaged
	# by every distribution (Arch). Take it from upstream, matching the system liblilv.
	if ! "$ZYNTHIAN_VENV_DIR/bin/python3" -c "import lilv" 2>/dev/null; then
		local lilv_version site_dir
		lilv_version=$(pkg-config --modversion lilv-0)
		site_dir=$("$ZYNTHIAN_VENV_DIR/bin/python3" -c "import sysconfig; print(sysconfig.get_paths()['purelib'])")
		echo "=== lilv.py $lilv_version from upstream ..."
		curl -fsSL -o "$site_dir/lilv.py" "https://gitlab.com/lv2/lilv/-/raw/v$lilv_version/bindings/python/lilv.py"
	fi
}

# mkdir -p for each argument, relative to $1
mkdirs() {
	local base="$1"; shift
	for d in "$@"; do
		mkdir -p "$base/$d"
	done
}

do_dirs() {
	echo "=== Config in $ZYNTHIAN_CONFIG_DIR ..."
	mkdir -p "$ZYNTHIAN_CONFIG_DIR"
	if [ ! -f "$ZYNTHIAN_CONFIG_DIR/zynthian_envars.sh" ]; then
		cp "$DESKTOP_DIR/zynthian_envars_desktop.sh" "$ZYNTHIAN_CONFIG_DIR/zynthian_envars.sh"
	fi
	# Factory config from zynthian-sys; files the user may change are copied only once.
	# No cp -a: the sources may belong to root (installed package), the copies are the user's.
	cp -R "$ZYNTHIAN_SYS_DIR/config/wiring-profiles" "$ZYNTHIAN_CONFIG_DIR"
	cp "$ZYNTHIAN_SYS_DIR/config/sidechain.json" "$ZYNTHIAN_CONFIG_DIR"
	for f in config_backup_items.txt data_backup_items.txt; do
		[ -f "$ZYNTHIAN_CONFIG_DIR/$f" ] || cp "$ZYNTHIAN_SYS_DIR/config/$f" "$ZYNTHIAN_CONFIG_DIR"
	done
	if [ ! -f "$ZYNTHIAN_CONFIG_DIR/midi-profiles/default.sh" ]; then
		mkdir -p "$ZYNTHIAN_CONFIG_DIR/midi-profiles"
		cp "$ZYNTHIAN_SYS_DIR/config/default_midi_profile.sh" "$ZYNTHIAN_CONFIG_DIR/midi-profiles/default.sh"
	fi
	mkdirs "$ZYNTHIAN_CONFIG_DIR" jalv ctrldev touchscreen

	echo "=== User data in $ZYNTHIAN_MY_DATA_DIR ..."
	mkdirs "$ZYNTHIAN_MY_DATA_DIR" \
		presets/lv2 presets/zynaddsubfx/banks presets/zynaddsubfx/presets \
		presets/mod-ui/pedalboards presets/puredata/generative presets/puredata/synths \
		presets/sysex preset-favorites \
		soundfonts/sf2 soundfonts/sfz soundfonts/gig soundfonts/hydrogen \
		snapshots/000 zynseq capture collections ctrldev \
		files/Audio/Tracks files/Samples/Percussion files/Samples/One-Shot files/Samples/Loops \
		files/Midi/patterns files/IRs/Cabinet files/IRs/Reverbs files/IRs/deconvolved \
		"files/Neural Models" files/Tuning files/Patterns
	for l in files/Audio/capture files/Midi/capture; do
		[ -e "$ZYNTHIAN_MY_DATA_DIR/$l" ] || ln -s "$ZYNTHIAN_MY_DATA_DIR/capture" "$ZYNTHIAN_MY_DATA_DIR/$l"
	done
	[ -e "$ZYNTHIAN_MY_DATA_DIR/files/Samples/sfz" ] || ln -s "$ZYNTHIAN_MY_DATA_DIR/soundfonts/sfz" "$ZYNTHIAN_MY_DATA_DIR/files/Samples/sfz"
	# Factory snapshots
	mkdir -p "$ZYNTHIAN_MY_DATA_DIR/snapshots/000-Factory"
	cp -Ru "$ZYNTHIAN_DATA_DIR/snapshots/." "$ZYNTHIAN_MY_DATA_DIR/snapshots/000-Factory/"

	mkdir -p "$ZYNTHIAN_LV2_DIR" "$ZYNTHIAN_SW_DIR"
}

case "${1:-all}" in
	build) check_dirs "$ZYNTHIAN_ZYNCODER_DIR"; do_build ;;
	jalv) do_jalv ;;
	venv) do_venv ;;
	dirs) check_dirs "$ZYNTHIAN_SYS_DIR" "$ZYNTHIAN_DATA_DIR"; do_dirs ;;
	all) check_dirs "$ZYNTHIAN_SYS_DIR" "$ZYNTHIAN_DATA_DIR" "$ZYNTHIAN_ZYNCODER_DIR"; do_build; do_venv; do_dirs ;;
	*) echo "Usage: $0 [all|build|jalv|venv|dirs]"; exit 1 ;;
esac

echo "=== Done. Start with: $DESKTOP_DIR/zynthian_desktop.sh"
