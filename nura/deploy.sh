#!/bin/sh
# Build Nura packages and install them on a running device over SSH.
#
# Usage: deploy.sh [-c CONFIG] [-H HOST] [-u USER] [-a ARCH] [-z ZYNCODER] [-n] [-S] [-r] [-d] PACKAGE...
#   -c CONFIG    pmbootstrap config (default: ~/.config/pmbootstrap-zynthian.cfg)
#   -H HOST      device address (default: <hostname from the config>.local, via avahi)
#   -u USER      SSH user on the device (default: user from the config)
#   -a ARCH      package architecture (default: aarch64)
#   -z ZYNCODER  zyncoder checkout for the zyncoder package (default: ../zyncoder next to
#                this zynthian-ui checkout)
#   -n           do not build; install the newest packages already built
#   -S           strict build: let pmbootstrap zap the build chroots first (its default).
#                Without it builds run with --lax, which keeps the chroot and the --src copy.
#   -r           restart the kiosk session afterwards (systemctl restart tinydm)
#   -d           dry run: print the commands instead of running them
#
# Examples:
#   deploy.sh -r zynthian-ui                 # build zynthian-ui from this checkout, install, restart
#   deploy.sh zyncoder zynthian-ui           # both checkouts
#   deploy.sh postmarketos-ui-zynthian       # the kiosk package
#
# zynthian-ui is built from this checkout and zyncoder from its checkout (pmbootstrap build
# --src); other packages from their APKBUILDs. A subpackage (-dbg, zynthian-help, ...) is built
# with its main package. Installing uses "pmbootstrap sideload": it copies the newest version of
# each package and runs "sudo apk add" on the device.
set -eu

here=$(cd "$(dirname "$0")" && pwd)
checkout=$(cd "$here/.." && pwd)
zyncoder=$(cd "$checkout/.." && pwd)/zyncoder
cfg=$HOME/.config/pmbootstrap-zynthian.cfg
host=
user=
arch=aarch64
build=1
lax=--lax
restart=0
dry=0

usage() { sed -n '2,/^set -eu/{/^set -eu/d;s/^# \{0,1\}//;p}' "$0"; exit "${1:-0}"; }

while getopts c:H:u:a:z:nSrdh opt; do
	case $opt in
		c) cfg=$OPTARG ;;
		H) host=$OPTARG ;;
		u) user=$OPTARG ;;
		a) arch=$OPTARG ;;
		z) zyncoder=$OPTARG ;;
		n) build=0 ;;
		S) lax= ;;
		r) restart=1 ;;
		d) dry=1 ;;
		h) usage ;;
		*) usage 1 ;;
	esac
done
shift $((OPTIND - 1))
[ $# -gt 0 ] || usage 1
[ -f "$cfg" ] || { echo "no pmbootstrap config: $cfg" >&2; exit 1; }

cfgval() { sed -n "s/^$1 *= *//p" "$cfg" | head -n 1; }
[ -n "$user" ] || user=$(cfgval user)
[ -n "$host" ] || host=$(cfgval hostname).local

run() {
	echo "+ $*"
	[ "$dry" = 1 ] || "$@"
}
pmb() { run pmbootstrap -c "$cfg" "$@"; }

# Main package of a (sub)package name
mainpkg() {
	case $1 in
		*-dbg) echo "${1%-dbg}" ;;
		zynthian-help | zynthian-sys-config) echo zynthian-data ;;
		*) echo "$1" ;;
	esac
}

if [ "$build" = 1 ]; then
	mains=
	for pkg in "$@"; do
		main=$(mainpkg "$pkg")
		case " $mains " in *" $main "*) ;; *) mains="$mains $main" ;; esac
	done
	others=
	for main in $mains; do
		case $main in
			# shellcheck disable=SC2086 # empty $lax is intended
			zynthian-ui) pmb build $lax --arch "$arch" --src="$checkout" zynthian-ui ;;
			# shellcheck disable=SC2086
			zyncoder) pmb build $lax --arch "$arch" --src="$zyncoder" zyncoder ;;
			*) others="$others $main" ;;
		esac
	done
	# Build noarch packages for the device's architecture too: otherwise pmbootstrap builds
	# them for the host and pulls in host builds of their dependencies.
	# shellcheck disable=SC2086 # word splitting intended
	[ -z "$others" ] || pmb build $lax --arch "$arch" $others
fi

pmb sideload --arch "$arch" --host "$host" --user "$user" "$@"

if [ "$restart" = 1 ]; then
	run ssh -t "$user@$host" 'sudo systemctl restart tinydm'
fi
