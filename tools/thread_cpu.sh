#!/bin/sh
usage_text='CPU use of zynthian (per thread), the compositor and the engines on the device.

Usage: thread_cpu.sh [-c CONFIG] [-H HOST] [-u USER] [-P PORT] [-V] [-t SECONDS] [-g GOVERNOR] [-p PATTERN]

  -t SECONDS   measuring time (default 20)
  -g GOVERNOR  CPU frequency governor during the measurement (default performance; the previous
               one is restored afterwards; "-" leaves it as it is)
  -p PATTERN   measure the process matching this pgrep -f pattern instead of zynthian (e.g.
               "^python3 spike.py"; the M0 spike)

Percent of one core, from /proc/<pid>/task/*/stat (utime + stime) over the measuring time.
zynthian is the Tk (zynthian_main.py) or Qt (zynthian_qt_main.py) UI; the compositor cage or
labwc; engines are the processes zynthian starts (fluidsynth, sfizz, zynaddsubfx, jalv, ...).
Device: from the pmbootstrap config (default ~/.config/pmbootstrap-zynthian.cfg).
See docs/performance-measurement.md.'
set -eu
here=$(cd "$(dirname "$0")" && pwd)
. "$here/common.sh"

secs=20
governor=performance
pattern=
tool_opts="t:g:p:"
tool_opt() {
	case $1 in
		t) secs=$2 ;;
		g) governor=$2 ;;
		p) pattern=$2 ;;
	esac
}
parse_common "$@"
shift $((OPTIND - 1))
setup_target

dev "T=$secs G=$governor PAT='$pattern' sh -s" <<'EOF'
set -eu
# [p]/[c]/[l]: the patterns must not match this shell's own command line
# (BusyBox pgrep: plain patterns, no alternatives)
if [ -n "$PAT" ]; then
	P=$(pgrep -f "$PAT" | grep -vx "$$" | head -n 1 || true)
else
	P=$(pgrep -f "^[p]ython3 ./zynthian_qt_main.py" | head -n 1 || true)
	[ -n "$P" ] || P=$(pgrep -f "^[p]ython3 ./zynthian_main.py" | head -n 1 || true)
fi
[ -n "$P" ] || { echo "no process found${PAT:+ for $PAT} (is zynthian running?)" >&2; exit 1; }
C=$(pgrep -x cage | head -n 1 || true)
[ -n "$C" ] || C=$(pgrep -x labwc | head -n 1 || true)
E=
for name in fluidsynth sfizz_jack zynaddsubfx jalv setBfree aeolus linuxsampler sooperlooper pd; do
	E="$E $(pgrep -x "$name" || true)"
done

old=
if [ "$G" != "-" ]; then
	old=$(cat /sys/devices/system/cpu/cpufreq/policy0/scaling_governor)
	for p in /sys/devices/system/cpu/cpufreq/policy*; do echo "$G" | sudo tee "$p/scaling_governor" >/dev/null; done
	sleep 2
fi

snap() {
	for t in /proc/$P/task/*; do
		echo "$(tr ' ' _ < "$t/comm") $(awk '{print $14 + $15}' "$t/stat")"
	done | awk '{a[$1] += $2} END {for (k in a) print "zynthian:" k, a[k]}'
	[ -z "$C" ] || echo "compositor:$(cat /proc/$C/comm) $(awk '{print $14 + $15}' /proc/$C/stat)"
	for e in $E; do echo "engine:$(cat /proc/$e/comm) $(awk '{print $14 + $15}' /proc/$e/stat)"; done
}
snap > /tmp/thread_cpu.1
sleep "$T"
snap > /tmp/thread_cpu.2
[ -z "$old" ] || for p in /sys/devices/system/cpu/cpufreq/policy*; do echo "$old" | sudo tee "$p/scaling_governor" >/dev/null; done

echo "$(cat /proc/$P/cmdline | tr '\0' ' ') (pid $P), ${T} s, governor $G"
awk -v hz="$(getconf CLK_TCK)" -v t="$T" '
	NR == FNR {a[$1] = $2; next}
	{d = $2 - a[$1]; if (d > 0) printf "  %-32s %5.1f %%\n", $1, 100 * d / hz / t}' \
	/tmp/thread_cpu.1 /tmp/thread_cpu.2 | sort -k2 -rn
rm -f /tmp/thread_cpu.1 /tmp/thread_cpu.2
EOF
