#!/bin/sh
usage_text='Screen switch times of the Qt UI on the device: switches screens over OSC (CUIAs) and
collects the times zynthian logs with ZYNTHIAN_QT_TIMING=1.

Usage: qt_switch_timing.sh [-c CONFIG] [-H HOST] [-u USER] [-r ROUNDS] [-g GOVERNOR] [-U UNIT] [CUIA...]

  -r ROUNDS    rounds through the CUIAs (default 3; the first includes building each view)
  -g GOVERNOR  CPU frequency governor during the measurement (default performance; restored
               afterwards; "-" leaves it as it is)
  -U UNIT      read zynthian'"'"'s output from this systemd user unit (default: the kiosk log
               ~/.local/state/tinydm.log)
  CUIA         screens to switch to (default: screen_audio_mixer main_menu chain_control
               screen_admin screen_snapshot)

Each time is from the start of the switch (ZynUI._set_current_screen) to the next frame on
screen (QQuickWindow.frameSwapped), "build" the Python part. zynthian must run with
ZYNTHIAN_QT_TIMING=1. See docs/performance-measurement.md.'
set -eu
here=$(cd "$(dirname "$0")" && pwd)
. "$here/common.sh"

rounds=3
governor=performance
unit=
tool_opts="r:g:U:"
tool_opt() {
	case $1 in
		r) rounds=$2 ;;
		g) governor=$2 ;;
		U) unit=$2 ;;
	esac
}
parse_common "$@"
shift $((OPTIND - 1))
cuias=${*:-screen_audio_mixer main_menu chain_control screen_admin screen_snapshot}
setup_target

dev "R=$rounds G=$governor UNIT='$unit' CUIAS='$cuias' sh -s" <<'EOF'
set -eu
pgrep -f "^[p]ython3 ./zynthian_qt_main.py" >/dev/null || { echo "the Qt UI is not running" >&2; exit 1; }
log() {
	if [ -n "$UNIT" ]; then
		journalctl --user -u "$UNIT" --no-pager -o cat --since "$since"
	else
		tail -n +"$((lines + 1))" ~/.local/state/tinydm.log
	fi
}
old=
if [ "$G" != "-" ]; then
	old=$(cat /sys/devices/system/cpu/cpufreq/policy0/scaling_governor)
	for p in /sys/devices/system/cpu/cpufreq/policy*; do echo "$G" | sudo tee "$p/scaling_governor" >/dev/null; done
	sleep 2
fi
since=$(date "+%Y-%m-%d %H:%M:%S")
lines=$(wc -l < ~/.local/state/tinydm.log 2>/dev/null || echo 0)
r=0
while [ "$r" -lt "$R" ]; do
	for c in $CUIAS; do
		oscsend localhost 1370 "/cuia/$c"
		sleep 2
	done
	r=$((r + 1))
done
[ -z "$old" ] || for p in /sys/devices/system/cpu/cpufreq/policy*; do echo "$old" | sudo tee "$p/scaling_governor" >/dev/null; done
out=$(log | grep "SCREEN TIMING" | sed 's/.*SCREEN TIMING //')
[ -n "$out" ] || { echo "no timings: is zynthian running with ZYNTHIAN_QT_TIMING=1 (and -U for a unit)?" >&2; exit 1; }
echo "$out"
EOF
