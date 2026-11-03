#!/bin/sh
usage_text='Take a screenshot of the kiosk session on the device.

Usage: screenshot.sh [-c CONFIG] [-H HOST] [-u USER] [-s SCALE] [FILE]

  -s SCALE  scale factor (default 0.5: half size, enough to read the UI)
  FILE      where to save it (default zynthian-YYYYmmdd-HHMMSS.png)

Needs grim on the device (sudo apk add grim).'
set -eu
here=$(cd "$(dirname "$0")" && pwd)
. "$here/common.sh"

scale=0.5
tool_opts="s:"
tool_opt() {
	case $1 in
		s) scale=$2 ;;
	esac
}
parse_common "$@"
shift $((OPTIND - 1))
file=${1:-zynthian-$(date +%Y%m%d-%H%M%S).png}
setup_target

dev "command -v grim >/dev/null || { echo 'grim is not installed: sudo apk add grim' >&2; exit 1; }
$SESSION_ENV grim -s $scale /tmp/zynthian-screenshot.png"
scp -q "$target:/tmp/zynthian-screenshot.png" "$file"
dev 'rm -f /tmp/zynthian-screenshot.png'
echo "$file"
