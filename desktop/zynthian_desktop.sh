#!/bin/bash
#******************************************************************************
# ZYNTHIAN PROJECT: start zynthian on desktop Linux
#
# Desktop counterpart of zynthian.sh: no splash screens, display rotation,
# first-boot handling, wifi or power off. Expects a running JACK server, which
# on current desktops is PipeWire with pipewire-jack.
#
# Environment: see zynthian_desktop_env.sh for the directories. Also
#   ZYNTHIAN_LOG_LEVEL   10=DEBUG, 20=INFO (default), 30=WARNING, ...
#   ZYNTHIAN_DEBUG=1     same as ZYNTHIAN_LOG_LEVEL=10 plus Python fault handler
#   ZYNTHIAN_FULLSCREEN=1  use the whole screen (kiosk), ignoring DISPLAY_WIDTH/HEIGHT
#******************************************************************************

source "$(dirname "${BASH_SOURCE[0]}")/zynthian_desktop_env.sh"

if [ -n "$ZYNTHIAN_LIB_DIR" ]; then
	# Installed (package): libraries and Python packages come with it, only the
	# user's directories need to be created
	if [ ! -f "$ZYNTHIAN_CONFIG_DIR/zynthian_envars.sh" ]; then
		"$ZYNTHIAN_UI_DIR/desktop/setup_desktop.sh" dirs || exit 1
	fi
else
	# Source checkout
	if [ ! -f "$ZYNTHIAN_CONFIG_DIR/zynthian_envars.sh" ] || [ ! -x "$ZYNTHIAN_VENV_DIR/bin/python3" ]; then
		echo "zynthian is not set up yet, running setup_desktop.sh ..."
		"$ZYNTHIAN_UI_DIR/desktop/setup_desktop.sh" || exit 1
	fi
	if [ ! -f "$ZYNTHIAN_ZYNCODER_DIR/build/libzyncore.so" ]; then
		"$ZYNTHIAN_UI_DIR/desktop/setup_desktop.sh" build || exit 1
	fi
fi

load_config_env() {
	source "$ZYNTHIAN_CONFIG_DIR/zynthian_envars.sh"
	if [ -n "$ZYNTHIAN_SCRIPT_MIDI_PROFILE" ] && [ -f "$ZYNTHIAN_SCRIPT_MIDI_PROFILE" ]; then
		source "$ZYNTHIAN_SCRIPT_MIDI_PROFILE"
	elif [ -f "$ZYNTHIAN_CONFIG_DIR/midi-profiles/default.sh" ]; then
		source "$ZYNTHIAN_CONFIG_DIR/midi-profiles/default.sh"
	fi
	if [ -f "$ZYNTHIAN_CONFIG_DIR/zynthian_custom_config.sh" ]; then
		source "$ZYNTHIAN_CONFIG_DIR/zynthian_custom_config.sh"
	fi
	# Kiosk: use the whole screen, whatever size the config has
	if [ "$ZYNTHIAN_FULLSCREEN" == "1" ]; then
		unset DISPLAY_WIDTH DISPLAY_HEIGHT
	fi
}

del_last_state() {
	local ss_dpath="$ZYNTHIAN_MY_DATA_DIR/snapshots"
	if [ -f "$ss_dpath/last_state.zss" ]; then
		cp -a "$ss_dpath/last_state.zss" "$ss_dpath/recovery.zss"
		rm -f "$ss_dpath/last_state.zss"
	fi
}

if [ "$ZYNTHIAN_DEBUG" == "1" ]; then
	export ZYNTHIAN_LOG_LEVEL=10
	export PYTHONFAULTHANDLER=1
fi

# zyncoder is imported as a package from the UI directory
if [ ! -e "$ZYNTHIAN_UI_DIR/zyncoder" ]; then
	echo "Missing $ZYNTHIAN_UI_DIR/zyncoder (symlink to $ZYNTHIAN_ZYNCODER_DIR, or the zyncoder package)"
	exit 1
fi

# The venv, if there is one (source checkout); a package uses the system Python
if [ -f "$ZYNTHIAN_VENV_DIR/bin/activate" ]; then
	source "$ZYNTHIAN_VENV_DIR/bin/activate"
fi

# LV2 plugin cache, generated on first boot on ZynthianOS. Regenerate it after
# installing plugins with: (cd zyngine && python3 zynthian_lv2.py)
if [ ! -f "$ZYNTHIAN_CONFIG_DIR/engine_config.json" ]; then
	echo "Scanning LV2 plugins ($LV2_PATH) ..."
	load_config_env
	(cd "$ZYNTHIAN_UI_DIR/zyngine" && python3 ./zynthian_lv2.py)
fi

cd "$ZYNTHIAN_UI_DIR"

error_counter=0
while true; do
	load_config_env
	# ZYNTHIAN_UI=qt: the Qt Quick UI (docs/qt-port-plan.md) instead of the Tk UI (if this tree
	# has it: upstream zynthian-ui hasn't)
	if [ "$ZYNTHIAN_UI" == "qt" ] && [ -f ./zynthian_qt_main.py ]; then
		python3 ./zynthian_qt_main.py
	else
		# Tk draws through X11 (XWayland on a Wayland desktop): its OpenGL widgets
		# (pyopengltk) need GLX, PyOpenGL would pick EGL when WAYLAND_DISPLAY is set
		PYOPENGL_PLATFORM="${PYOPENGL_PLATFORM:-glx}" python3 ./zynthian_main.py
	fi
	status=$?
	echo "zynthian exit status: $status"

	case $status in
		0|101)
			# Power off / exit
			break
			;;
		100|102)
			# Reboot / restart UI => restart UI
			error_counter=0
			sleep 1
			;;
		*)
			# Error; 1 => the last state may be the cause, keep it as recovery.zss
			error_counter=$((error_counter + 1))
			[ $status -eq 1 ] && del_last_state
			if [ $error_counter -ge 3 ]; then
				echo "zynthian failed $error_counter times, giving up"
				exit $status
			fi
			sleep 3
			;;
	esac
done
