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
#   ZYNTHIAN_STOP_TIMEOUT  seconds zynthian gets to stop on TERM/HUP/INT (default 30)
#
# Stopping: TERM, HUP (the kiosk session's end hangs up its terminal) or INT (Ctrl-C) ask
# zynthian to stop (TERM: it saves its state and stops its engines), wait up to
# ZYNTHIAN_STOP_TIMEOUT, then kill what is left of its process group: zynthian runs in its
# own, with the engines it started. After every exit (a crash too) the group is killed, so no
# engine outlives zynthian. A second launcher with the same configuration waits until the
# first one has finished (a lock in ZYNTHIAN_CONFIG_DIR).
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

stop_timeout=${ZYNTHIAN_STOP_TIMEOUT:-30}
case $stop_timeout in '' | *[!0-9]*) stop_timeout=30 ;; esac

# One launcher per configuration: a new kiosk session starts while the old zynthian may still be
# stopping its engines (their JACK client names would clash). Not inherited by zynthian.
if command -v flock >/dev/null && exec 9>>"$ZYNTHIAN_CONFIG_DIR/.launcher.lock"; then
	if ! flock -n 9; then
		echo "Waiting for the previous zynthian to stop ..."
		flock -w $((stop_timeout + 10)) 9 || echo "The previous zynthian launcher is still running, starting anyway"
	fi
fi

zpid=
stop_signal=
on_signal() {
	echo "zynthian launcher: $1, stopping zynthian"
	stop_signal=$1
	[ -n "$zpid" ] && kill -TERM "$zpid" 2>/dev/null
}
trap 'on_signal TERM' TERM
trap 'on_signal HUP' HUP
trap 'on_signal INT' INT

# Wait until process $1 (in this shell: a child) is gone, or $1 = -PGID: process group PGID
# is empty, at most $2 seconds
wait_gone() {
	local deadline=$((SECONDS + $2))
	while kill -0 -- "$1" 2>/dev/null && [ $SECONDS -lt "$deadline" ]; do
		sleep 0.2
	done
	! kill -0 -- "$1" 2>/dev/null
}

# Run zynthian (the command line) in its own process group, its engines with it, and wait for it;
# status: its exit status
run_zynthian() {
	# set -m: the background job gets its own process group. Not the terminal's foreground group
	# any more: the session's hangup reaches the launcher only, which asks zynthian to stop.
	# TTOU/TTIN ignored: terminal calls from the background group (Qt's linuxfb on the VT) must not
	# stop it.
	set -m
	(trap '' TTOU TTIN; exec "$@" 9>&-) &
	zpid=$!
	set +m
	[ -n "$stop_signal" ] && kill -TERM "$zpid" 2>/dev/null
	# wait returns early (> 128) when a trapped signal comes in
	while kill -0 "$zpid" 2>/dev/null && [ -z "$stop_signal" ]; do
		wait "$zpid"
	done
	if [ -n "$stop_signal" ] && ! wait_gone "$zpid" "$stop_timeout"; then
		echo "zynthian didn't stop within ${stop_timeout}s, killing it"
		kill -KILL -- "-$zpid" 2>/dev/null
	fi
	wait "$zpid" 2>/dev/null
	status=$?
	# What is left of the group: engines of a zynthian that crashed or didn't stop in time
	if kill -0 -- "-$zpid" 2>/dev/null; then
		echo "zynthian launcher: stopping what zynthian left behind (process group $zpid)"
		kill -TERM -- "-$zpid" 2>/dev/null
		wait_gone "-$zpid" 5 || kill -KILL -- "-$zpid" 2>/dev/null
	fi
	zpid=
}

error_counter=0
while [ -z "$stop_signal" ]; do
	load_config_env
	# ZYNTHIAN_UI=qt: the Qt Quick UI (docs/qt-port-plan.md) instead of the Tk UI (if this tree
	# has it: upstream zynthian-ui hasn't)
	if [ "$ZYNTHIAN_UI" == "qt" ] && [ -f ./zynthian_qt_main.py ]; then
		run_zynthian python3 ./zynthian_qt_main.py
	else
		# Tk draws through X11 (XWayland on a Wayland desktop): its OpenGL widgets
		# (pyopengltk) need GLX, PyOpenGL would pick EGL when WAYLAND_DISPLAY is set
		run_zynthian env PYOPENGL_PLATFORM="${PYOPENGL_PLATFORM:-glx}" python3 ./zynthian_main.py
	fi
	echo "zynthian exit status: $status"
	[ -n "$stop_signal" ] && break

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
