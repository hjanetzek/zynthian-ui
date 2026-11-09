#!/bin/sh
usage_text='Run a Python script inside the running zynthian on the device and print its result.

Usage: zyninject.sh [-c CONFIG] [-H HOST] [-u USER] [-P PORT] [-V] [-s NAME=VALUE]... [-t TIMEOUT] SCRIPT

  -s NAME=VALUE  replace the line "NAME = ..." in SCRIPT (a parameter), e.g. -s DURATION=20
  -t TIMEOUT     seconds to wait for the result (default 60)

The script runs in zynthian'"'"'s main thread (where Tk or Qt lives), from the event loop like a
timer callback (Tk UI: zynthian_main.py, Tk after(); Qt UI: zynthian_qt_main.py, QTimer): sys.remote_exec() (Python 3.14, needs sudo on the device) only injects a
bootstrap that schedules it. Running it directly at the point where remote_exec interrupts
the main thread can deadlock zynthian: that point may be inside code holding one of its
locks. The script writes its result to the file in its OUTPUT variable, which this tool
waits for, prints and removes; an exception is reported instead. Device: from the pmbootstrap config
(default ~/.config/pmbootstrap-zynthian.cfg), as deploy.sh.

Scripts in this directory: profile_idle.py, profile_screen.py, screen_timing.py.'
set -eu
here=$(cd "$(dirname "$0")" && pwd)
. "$here/common.sh"

subst=
timeout=60
tool_opts="s:t:"
tool_opt() {
	case $1 in
		s) subst="$subst
$2" ;;
		t) timeout=$2 ;;
	esac
}
parse_common "$@"
shift $((OPTIND - 1))
[ $# -eq 1 ] || usage 1
script=$1
[ -f "$script" ] || script=$here/$1
[ -f "$script" ] || { echo "no such script: $1" >&2; exit 1; }
setup_target

# Parameters: replace "NAME = ..." lines
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
cp "$script" "$tmp"
while IFS= read -r kv; do
	[ -n "$kv" ] || continue
	name=${kv%%=*}
	value=${kv#*=}
	grep -q "^$name = " "$tmp" || { echo "no parameter $name in $script" >&2; exit 1; }
	sed -i "s|^$name = .*|$name = $value|" "$tmp"
done <<EOF
$subst
EOF
output=$(sed -n 's/^OUTPUT = "\(.*\)"$/\1/p' "$tmp" | head -n 1)
[ -n "$output" ] || { echo "$script has no OUTPUT = \"...\" line" >&2; exit 1; }

remote=/tmp/zyninject-$(basename "$script")
boot=$(mktemp)
trap 'rm -f "$tmp" "$boot"' EXIT
cat > "$boot" <<EOB
# zyninject bootstrap, run by sys.remote_exec() wherever the main thread was interrupted:
# don't run anything here (no imports, no zynthian calls), only schedule the script on
# the UI's event loop (Qt's in the Qt UI, else Tk's).
import sys as _zi_sys

def _zi_run(path="$remote", output="$output"):
    try:
        with open(path) as f:
            code = compile(f.read(), path, "exec")
        exec(code, {"__name__": "__zyninject__"})
    except BaseException:
        import traceback
        with open(output, "w") as f:
            f.write("zyninject: the script failed:\\n" + traceback.format_exc())

if "zynqt.ui" in _zi_sys.modules:
    _zi_sys.modules["PySide6.QtCore"].QTimer.singleShot(1, _zi_run)
else:
    _zi_sys.modules["zyngui.zynthian_gui_config"].top.after(1, _zi_run)
EOB
devcp "$tmp" "$target:$remote"
devcp "$boot" "$target:$remote.boot.py"
dev "$ZYN_PID
rm -f '$output'
sudo python3 -c \"import sys; sys.remote_exec(\$P, '$remote.boot.py')\"
i=0
# Polled every 50 ms (an injection takes a few ms); once there, a moment for the write to end
while [ ! -f '$output' ] && [ \$i -lt $((timeout * 20)) ]; do sleep 0.05; i=\$((i + 1)); done
[ -f '$output' ] && sleep 0.05
rm -f '$remote' '$remote.boot.py'
[ -f '$output' ] || { echo 'no result after ${timeout} s; errors are in ~/.local/state/tinydm.log' >&2; exit 1; }
sed 's|/usr/share/zynthian/zynthian-ui/||g; s|/usr/share/zynthian/python/||g; s|/usr/lib/python3[.0-9]*/||g' '$output'
rm -f '$output'"
