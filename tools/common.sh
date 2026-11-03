#!/bin/sh
# Shared option handling of the tools: device address from the pmbootstrap config, as deploy.sh.
# Sourced by the tools after setting $usage_text; leaves the remaining arguments in "$@".

cfg=$HOME/.config/pmbootstrap-zynthian.cfg
host=
user=

usage() { printf '%s\n' "$usage_text"; exit "${1:-0}"; }

# Options common to all tools; a tool's own options are passed in $tool_opts (getopts letters)
parse_common() {
	while getopts "c:H:u:h${tool_opts:-}" opt; do
		case $opt in
			c) cfg=$OPTARG ;;
			H) host=$OPTARG ;;
			u) user=$OPTARG ;;
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

# Run a command on the device
dev() { ssh -o BatchMode=yes "$target" "$@"; }

# Shell snippet (for dev) that sets $P to zynthian's PID or fails
ZYN_PID='P=$(pgrep -f "^python3 ./zynthian_main.py" | head -n 1); [ -n "$P" ] || { echo "zynthian is not running" >&2; exit 1; }'

# Environment of the kiosk session (cage), for Wayland tools like grim
SESSION_ENV='XDG_RUNTIME_DIR=/run/user/$(id -u) WAYLAND_DISPLAY=wayland-0'
