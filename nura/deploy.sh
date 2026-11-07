#!/bin/sh
# Build Nura packages and install them on a running device over SSH.
#
# Usage: deploy.sh [-c CONFIG] [-H HOST] [-u USER] [-a ARCH] [-z ZYNCODER] [-j JALV] [-m DBM] [-k] [-n] [-S] [-r] [-d] PACKAGE...
#   -c CONFIG    pmbootstrap config (default: ~/.config/pmbootstrap-zynthian.cfg)
#   -H HOST      device address (default: <hostname from the config>.local, via avahi)
#   -u USER      SSH user on the device (default: user from the config)
#   -a ARCH      package architecture (default: aarch64)
#   -z ZYNCODER  zyncoder checkout for the zyncoder package (default: ../zyncoder next to
#                this zynthian-ui checkout)
#   -j JALV      zynthian's jalv checkout for the zynthian-jalv package (default: ../jalv next
#                to this zynthian-ui checkout; without it, the APKBUILD's pinned tarball)
#   -m DBM       drivenbymoss-rust checkout for the drivenbymoss and dbm-nihost packages
#                (default: ../drivenbymoss-rust next to this zynthian-ui checkout; its recipe
#                directory nura/ must be linked into pmaports, see README.md)
#   -k           install this work dir's package signing key on the device if needed (a device
#                whose image was built with another work dir rejects the packages: "UNTRUSTED
#                signature")
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
#   deploy.sh drivenbymoss dbm-nihost        # DrivenByMoss's zynthian drivers and the Maschine host
#
# zynthian-ui is built from this checkout, zyncoder, zynthian-jalv, drivenbymoss and dbm-nihost from
# their checkouts
# (pmbootstrap build --src); other packages from their APKBUILDs. With zynthian-ui, its new
# dependency zynthian-jalv is built and installed too when no package of it exists for ARCH
# yet. A subpackage (-dbg, zynthian-help, ...) is built
# with its main package. Installing uses "pmbootstrap sideload": it copies the newest version of
# each package and runs "sudo apk add" on the device.
set -eu

here=$(cd "$(dirname "$0")" && pwd)
checkout=$(cd "$here/.." && pwd)
zyncoder=$(cd "$checkout/.." && pwd)/zyncoder
jalv=$(cd "$checkout/.." && pwd)/jalv
dbm=$(cd "$checkout/.." && pwd)/drivenbymoss-rust
cfg=$HOME/.config/pmbootstrap-zynthian.cfg
host=
user=
arch=aarch64
build=1
lax=--lax
restart=0
dry=0
installkey=

usage() { sed -n '2,/^set -eu/{/^set -eu/d;s/^# \{0,1\}//;p}' "$0"; exit "${1:-0}"; }

while getopts c:H:u:a:z:j:m:knSrdh opt; do
	case $opt in
		c) cfg=$OPTARG ;;
		H) host=$OPTARG ;;
		u) user=$OPTARG ;;
		a) arch=$OPTARG ;;
		z) zyncoder=$OPTARG ;;
		j) jalv=$OPTARG ;;
		m) dbm=$OPTARG ;;
		k) installkey=--install-key ;;
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
	# Dependencies first: with --src, pmbootstrap doesn't build missing dependencies
	# (zynthian-ui needs zyncoder, zynthian-jalv and zynthian-data, the kiosk needs zynthian-ui).
	# zynthian-jalv comes along with zynthian-ui if no package of it is built for ARCH yet.
	case " $mains " in
		*" zynthian-ui "*)
			case " $mains " in *" zynthian-jalv "*) ;; *)
				workdir=$(cfgval work)
				[ -n "$workdir" ] || workdir=$HOME/.local/var/pmbootstrap
				ls "$workdir"/packages/edge/"$arch"/zynthian-jalv-*.apk >/dev/null 2>&1 ||
					{ mains="$mains zynthian-jalv"; set -- "$@" zynthian-jalv; } ;;
			esac ;;
	esac
	ordered=
	for main in zyncoder zynthian-jalv zynthian-data zynthian-ui drivenbymoss dbm-nihost postmarketos-ui-zynthian; do
		case " $mains " in *" $main "*) ordered="$ordered $main" ;; esac
	done
	for main in $mains; do
		case " $ordered " in *" $main "*) ;; *) ordered="$ordered $main" ;; esac
	done
	for main in $ordered; do
		case $main in
			# shellcheck disable=SC2086 # empty $lax is intended
			zynthian-ui) pmb build $lax --arch "$arch" --src="$checkout" zynthian-ui ;;
			# shellcheck disable=SC2086
			zyncoder) pmb build $lax --arch "$arch" --src="$zyncoder" zyncoder ;;
			# DrivenByMoss: both packages from the drivenbymoss-rust checkout
			# shellcheck disable=SC2086
			drivenbymoss | dbm-nihost) pmb build $lax --arch "$arch" --src="$dbm" "$main" ;;
			zynthian-jalv)
				if [ -d "$jalv" ]; then
					# shellcheck disable=SC2086
					pmb build $lax --arch "$arch" --src="$jalv" zynthian-jalv
				else
					# shellcheck disable=SC2086
					pmb build $lax --arch "$arch" zynthian-jalv
				fi ;;
			# Also noarch packages for the device's architecture: otherwise pmbootstrap builds
			# them for the host and pulls in host builds of their dependencies.
			# shellcheck disable=SC2086
			*) pmb build $lax --arch "$arch" "$main" ;;
		esac
	done
fi

# shellcheck disable=SC2086 # empty $installkey is intended
pmb sideload $installkey --arch "$arch" --host "$host" --user "$user" "$@"

if [ "$restart" = 1 ]; then
	run ssh -t "$user@$host" 'sudo systemctl restart tinydm'
fi
