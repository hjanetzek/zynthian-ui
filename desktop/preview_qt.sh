#!/bin/sh
usage_text='Run the Qt UI (zynthian_qt_main.py, through zynthian_desktop.sh) in a headless labwc
with the Duet kiosk'"'"'s output (1920x1200 at scale 1.5, i.e. 1280x800 logical pixels; PREVIEW_SCALE
overrides the scale), take screenshots, and stop it again.

Usage: preview_qt.sh [-o FILE] [-w SECONDS] [-s CUIA]... [-k]

  -o FILE     screenshot (PNG; default /tmp/zynthian-qt.png)
  -w SECONDS  wait before the first screenshot (default 20: snapshot loading)
  -s CUIA     after the first screenshot, send this CUIA over OSC (e.g. "screen_mixer",
              "show_screen main_menu"), wait 2 s and take another screenshot (FILE-1.png, ...)
  -k          keep it running afterwards (WAYLAND_DISPLAY printed; stop with Ctrl+C)

Output of zynthian goes to /tmp/zynthian-qt.log. Needs labwc, grim, wlr-randr, oscsend.'
set -eu

out=/tmp/zynthian-qt.png
wait=20
keep=
cuias=
while getopts "o:w:s:kh" opt; do
	case $opt in
		o) out=$OPTARG ;;
		w) wait=$OPTARG ;;
		s) cuias="$cuias
$OPTARG" ;;
		k) keep=1 ;;
		h) echo "$usage_text"; exit 0 ;;
		*) echo "$usage_text" >&2; exit 1 ;;
	esac
done
here=$(cd "$(dirname "$0")" && pwd)

tmp=$(mktemp -d)
labwc_pid=
zyn_pid=
cleanup() {
	# SIGTERM to zynthian itself (exit code 101 ends the launcher's loop): the launcher, a shell
	# waiting for it, would only act on a signal after zynthian exits
	[ -z "$zyn_pid" ] || pkill -TERM -P "$zyn_pid" 2>/dev/null || true
	# zynthian stops its engines on SIGTERM; give it time
	i=0
	while [ -n "$zyn_pid" ] && kill -0 "$zyn_pid" 2>/dev/null && [ $i -lt 100 ]; do sleep 0.1; i=$((i + 1)); done
	[ -z "$labwc_pid" ] || kill "$labwc_pid" 2>/dev/null || true
	rm -rf "$tmp"
}
trap cleanup EXIT INT TERM

# Headless compositor in its own runtime dir; PipeWire stays the user's (its socket path)
pw_runtime=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}
WLR_BACKENDS=headless WLR_HEADLESS_OUTPUTS=1 WLR_LIBINPUT_NO_DEVICES=1 XDG_RUNTIME_DIR=$tmp \
	labwc -C "$tmp" > "$tmp/labwc.log" 2>&1 &
labwc_pid=$!
i=0
while [ ! -S "$tmp/wayland-0" ]; do
	[ $i -lt 100 ] || { cat "$tmp/labwc.log" >&2; echo "labwc did not start" >&2; exit 1; }
	sleep 0.1
	i=$((i + 1))
done
output=$(XDG_RUNTIME_DIR=$tmp WAYLAND_DISPLAY=wayland-0 wlr-randr | sed -n '1s/ .*//p')
XDG_RUNTIME_DIR=$tmp WAYLAND_DISPLAY=wayland-0 wlr-randr --output "$output" --custom-mode 1920x1200 --scale "${PREVIEW_SCALE:-1.5}"

# zynthian: Wayland display of the headless labwc, everything else from the user's session
env WAYLAND_DISPLAY="$tmp/wayland-0" XDG_RUNTIME_DIR="$pw_runtime" QT_QPA_PLATFORM=wayland \
	QT_WAYLAND_DISABLE_WINDOWDECORATION=1 ZYNTHIAN_UI=qt ZYNTHIAN_FULLSCREEN=1 ZYNTHIAN_QT_TIMING=1 \
	"$here/zynthian_desktop.sh" > /tmp/zynthian-qt.log 2>&1 &
zyn_pid=$!

shot() {
	XDG_RUNTIME_DIR=$tmp WAYLAND_DISPLAY=wayland-0 grim "$1"
	echo "$1"
}
sleep "$wait"
kill -0 "$zyn_pid" 2>/dev/null || { tail -20 /tmp/zynthian-qt.log >&2; echo "zynthian exited" >&2; exit 1; }
shot "$out"
n=0
printf '%s\n' "$cuias" | while IFS= read -r cuia; do
	[ -n "$cuia" ] || continue
	n=$((n + 1))
	name=${cuia%% *}
	args=
	[ "$name" = "$cuia" ] || args=${cuia#* }
	if [ -n "$args" ]; then
		# shellcheck disable=SC2086 # args: one OSC string argument per word
		oscsend localhost 1370 "/cuia/$name" "$(printf 's%.0s' $args)" $args
	else
		oscsend localhost 1370 "/cuia/$name"
	fi
	sleep 2
	shot "${out%.png}-$n.png"
done

if [ -n "$keep" ]; then
	echo "running: WAYLAND_DISPLAY=$tmp/wayland-0 (Ctrl+C to stop)"
	wait "$zyn_pid" || true
fi
