#!/bin/sh
# Shared option handling of the tools: device address from the pmbootstrap config, as deploy.sh;
# -P PORT for another SSH port, -V for the local QEMU VM (user@127.0.0.1:2222, docs/qemu-testing.md).
# Sourced by the tools after setting $usage_text; leaves the remaining arguments in "$@".

cfg=$HOME/.config/pmbootstrap-zynthian.cfg
host=
user=
port=
# SSH options (-V adds the VM's: its host key changes with every fresh disk)
ssh_opts="-o BatchMode=yes"

usage() { printf '%s\n' "$usage_text"; exit "${1:-0}"; }

# Options common to all tools; a tool's own options are passed in $tool_opts (getopts letters)
parse_common() {
	while getopts "c:H:u:P:Vh${tool_opts:-}" opt; do
		case $opt in
			c) cfg=$OPTARG ;;
			H) host=$OPTARG ;;
			u) user=$OPTARG ;;
			P) port=$OPTARG ;;
			# The local QEMU VM (nura-builds' tools/run-qemu.sh, docs/qemu-testing.md)
			V) host=127.0.0.1; user=${user:-user}; port=${NURA_VM_PORT:-2222}
			   ssh_opts="$ssh_opts -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR" ;;
			h) usage ;;
			\?) usage 1 ;;
			*) tool_opt "$opt" "${OPTARG:-}" ;;
		esac
	done
}

setup_target() {
	if [ -z "$host" ] || [ -z "$user" ]; then
		[ -f "$cfg" ] || { echo "no pmbootstrap config: $cfg (or use -H HOST -u USER)" >&2; exit 1; }
		cfgval() { sed -n "s/^$1 *= *//p" "$cfg" | head -n 1; }
		[ -n "$user" ] || user=$(cfgval user)
		[ -n "$host" ] || host=$(cfgval hostname).local
	fi
	target=$user@$host
}

# Run a command on the device; copy files from/to it (devcp SRC... DST, remote paths as $target:PATH)
# shellcheck disable=SC2086 # $ssh_opts: several options
dev() { ssh $ssh_opts ${port:+-p "$port"} "$target" "$@"; }
# shellcheck disable=SC2086
devcp() { scp -q $ssh_opts ${port:+-P "$port"} "$@"; }

# Shell snippet (for dev) that sets $P to zynthian's PID or fails
ZYN_PID='P=$(pgrep -f "^python3 ./zynthian_main.py" | head -n 1); [ -n "$P" ] || { echo "zynthian is not running" >&2; exit 1; }'

# Environment of the kiosk session (cage), for Wayland tools like grim
SESSION_ENV='XDG_RUNTIME_DIR=/run/user/$(id -u) WAYLAND_DISPLAY=wayland-0'
