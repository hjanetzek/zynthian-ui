#!/bin/bash
#******************************************************************************
# ZYNTHIAN PROJECT: set up zynthian on desktop Linux
#
# Builds the native libraries, creates the Python venv and the user's config
# and data directories. Safe to run again: existing user files are kept.
#
#   desktop/setup_desktop.sh            everything
#   desktop/setup_desktop.sh build      only build zyncore and the zynlibs
#   desktop/setup_desktop.sh venv       only create/update the venv
#   desktop/setup_desktop.sh dirs       only create config and data dirs
#
# Needs uv. System packages are not installed here; see desktop/README.md.
#******************************************************************************

set -e

source "$(dirname "${BASH_SOURCE[0]}")/zynthian_desktop_env.sh"

DESKTOP_DIR="$ZYNTHIAN_UI_DIR/desktop"

# Python packages for the venv, installed with uv. The venv is created with
# --system-site-packages, so packages from the distribution are used where
# installed (a Nura package will depend on those instead).
PY_PACKAGES=(
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
}

do_venv() {
	echo "=== Python venv in $ZYNTHIAN_VENV_DIR ..."
	if [ ! -x "$ZYNTHIAN_VENV_DIR/bin/python3" ]; then
		mkdir -p "$(dirname "$ZYNTHIAN_VENV_DIR")"
		# The system Python: it has tkinter, and the venv sees its packages
		uv venv --python /usr/bin/python3 --system-site-packages "$ZYNTHIAN_VENV_DIR"
	fi
	uv pip install --python "$ZYNTHIAN_VENV_DIR/bin/python3" "${PY_PACKAGES[@]}"

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
	venv) do_venv ;;
	dirs) check_dirs "$ZYNTHIAN_SYS_DIR" "$ZYNTHIAN_DATA_DIR"; do_dirs ;;
	all) check_dirs "$ZYNTHIAN_SYS_DIR" "$ZYNTHIAN_DATA_DIR" "$ZYNTHIAN_ZYNCODER_DIR"; do_build; do_venv; do_dirs ;;
	*) echo "Usage: $0 [all|build|venv|dirs]"; exit 1 ;;
esac

echo "=== Done. Start with: $DESKTOP_DIR/zynthian_desktop.sh"
