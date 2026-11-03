#!/bin/sh
usage_text='Record zynthian and Xwayland on the device with perf and print where the CPU time goes.

Usage: perf_profile.sh [-c CONFIG] [-H HOST] [-u USER] [-d SECONDS] [-n LINES]

  -d SECONDS  recording time per process (default 15)
  -n LINES    lines per listing (default 20)

Prints zynthian'"'"'s CPU time by thread and by library, the top symbols of its main thread
(the Tk UI) and of Xwayland. Python functions are not named (Alpine'"'"'s Python has no perf
trampoline): their time shows as libpython; use profile_idle.py for the Python side.
Needs perf on the device (sudo apk add perf).'
set -eu
here=$(cd "$(dirname "$0")" && pwd)
. "$here/common.sh"

secs=15
lines=20
tool_opts="d:n:"
tool_opt() {
	case $1 in
		d) secs=$2 ;;
		n) lines=$2 ;;
	esac
}
parse_common "$@"
setup_target

dev "$ZYN_PID
X=\$(pgrep -x Xwayland | head -n 1)
command -v perf >/dev/null || { echo 'perf is not installed: sudo apk add perf' >&2; exit 1; }
cd /tmp
echo \"Recording zynthian (pid \$P) for $secs s ...\"
sudo perf record -q -F 499 -p \$P -o /tmp/perf-zynthian.data -- sleep $secs 2>/dev/null
if [ -n \"\$X\" ]; then
	echo \"Recording Xwayland (pid \$X) for $secs s ...\"
	sudo perf record -q -F 499 -p \$X -o /tmp/perf-xwayland.data -- sleep $secs 2>/dev/null
fi
report() { sudo perf report --stdio \"\$@\" 2>/dev/null | grep -vE '^#|^\$' | head -n $lines | cut -c1-120; }
echo; echo '== zynthian by thread'; report -i /tmp/perf-zynthian.data --sort comm
echo; echo '== zynthian by library'; report -i /tmp/perf-zynthian.data --sort dso
echo; echo '== zynthian main thread (Tk UI): top symbols'; report -i /tmp/perf-zynthian.data --comm python3 --sort dso,sym
if [ -n \"\$X\" ]; then
	echo; echo '== Xwayland: top symbols'; report -i /tmp/perf-xwayland.data --sort dso,sym
fi
sudo rm -f /tmp/perf-zynthian.data /tmp/perf-xwayland.data"
