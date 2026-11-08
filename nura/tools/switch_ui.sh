#!/bin/sh
usage_text='Switch the device between the zynthian-ui packages, for quick comparisons.

Usage: switch_ui.sh [-c CONFIG] [-H HOST] [-u USER] [-P PORT] [-V] [-R DIR] [-n] [qt | vangelis | tomita]

  qt        zynthian-ui: the Qt UI port (hjanetzek/zynthian-ui, nura branch)
  vangelis  zynthian-ui-vangelis: upstream vangelis (stable), Tk UI, with the port patches
  tomita    zynthian-ui-tomita: upstream tomita (development), Tk UI, with the port patches
  (none)    show which one is installed

  -R DIR    also install from this repository directory on the device (DIR/<arch>/APKINDEX.tar.gz
            with the packages; --allow-untrusted), e.g. packages from a CI artifact
  -n        do not restart the kiosk session

The packages come from the device'"'"'s repositories (nura-builds'"'"' release "aarch64"). Each one
provides zynthian-ui, so apk installs only one; the kiosk package (postmarketos-ui-zynthian) works
with all of them and starts the Tk UI when the installed one has no Qt UI. The settings in
~/.config/zynthian stay; snapshots and presets are shared between the three.'
set -eu
here=$(cd "$(dirname "$0")" && pwd)
. "$here/common.sh"

repo=
restart=1
tool_opts="R:n"
tool_opt() {
	case $1 in
		R) repo=$2 ;;
		n) restart=0 ;;
	esac
}
parse_common "$@"
shift $((OPTIND - 1))
[ $# -le 1 ] || usage 1
setup_target

case ${1:-} in
	"") want= ;;
	qt) want=zynthian-ui ;;
	vangelis | tomita) want=zynthian-ui-$1 ;;
	*) usage 1 ;;
esac

# The installed provider of zynthian-ui
# (by package name: "apk info -e zynthian-ui" also matches the other two, which provide it)
current=$(dev "apk info 2>/dev/null | grep -xE 'zynthian-ui(-vangelis|-tomita)?'" | head -n 1 || true)
if [ -z "$want" ]; then
	echo "installed: $(dev "apk info -v 2>/dev/null | grep -E '^zynthian-ui(-vangelis|-tomita)?-[0-9]'" || echo none)"
	exit 0
fi
if [ "$current" = "$want" ]; then
	echo "$want is already installed"
	exit 0
fi

apk_opts=
[ -z "$repo" ] || apk_opts="--allow-untrusted --repository $repo"

# Remove the current one from the world file only (the kiosk package still needs zynthian-ui, so
# apk keeps it); then adding the other one replaces it in one transaction.
echo "switching ${current:-none} -> $want"
dev "set -e
	[ -z '$current' ] || sudo apk del -q '$current' >/dev/null
	sudo apk add $apk_opts '$want'
	apk info -e '$want' >/dev/null"

if [ $restart = 1 ]; then
	echo "restarting the kiosk session"
	dev 'sudo systemctl restart tinydm'
fi
