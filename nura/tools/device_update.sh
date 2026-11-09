#!/bin/sh
# Check Nura devices for updates, and apply them: over SSH, from the host.
#
#   nura/tools/device_update.sh [-y] [-a] [-r] [-f] HOST...
#
# Without options: apk update, then list the pending upgrades and the packages of nura-builds'
# package repository (release "aarch64") that aren't installed (without -dev, -dbg,
# -doc, -pyc, and the Qt/PySide packages, which come as dependencies).
#   -y  apply the upgrades (apk upgrade), then upgrade by name the packages of nura-builds
#       that apk upgrade left at an older version (seen with zynthian-ui)
#   -a  also install the packages that aren't installed (optional data, help, new plugins)
#   -r  after changes to plugins or zynthian: rescan the LV2 plugins and restart the session
#   -f  even while abuild or pmbootstrap runs on the device (an upgrade can remove build
#       dependencies or restart services under a running build)
#
# HOST: an SSH destination with passwordless sudo, e.g. jeff@kick-duet.local, jeff@pixel3.local.
set -eu

usage() { sed -n '2,/^$/s/^# \{0,1\}//p' "$0" >&2; exit 2; }
apply= all= restart= force=
while getopts yarfh opt; do
	case $opt in
		y) apply=1 ;;
		a) all=1; apply=1 ;;
		r) restart=1 ;;
		f) force=1 ;;
		*) usage ;;
	esac
done
shift $((OPTIND - 1))
[ $# -gt 0 ] || usage

repo=${NURA_REPOSITORY:-https://github.com/hjanetzek/nura-builds/releases/download}
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Packages of the repository: name and version
curl -sfL "$repo/aarch64/APKINDEX.tar.gz" | tar -xzO APKINDEX |
	awk -F: '/^P:/ {p = $2} /^V:/ {print p, $2}' | sort -u > "$tmp/repo" ||
	{ echo "can't read $repo/aarch64/APKINDEX.tar.gz" >&2; exit 1; }
cut -d' ' -f1 "$tmp/repo" | sort -u > "$tmp/repo-names"

for host in "$@"; do
	echo "=== $host"
	if ! ssh -o ConnectTimeout=8 "$host" true 2>/dev/null; then
		echo "not reachable"
		continue
	fi
	if [ -n "$apply" ] && [ -z "$force" ] &&
		ssh "$host" 'pgrep -x abuild >/dev/null || pgrep -f "[p]mbootstrap" >/dev/null'; then
		echo "abuild or pmbootstrap is running: not changing anything (-f to do it anyway)"
		apply= all=
	fi

	ssh "$host" 'sudo apk update >/dev/null 2>&1; sudo apk upgrade --simulate 2>/dev/null' |
		grep -E '(Upgrading|Installing|Downgrading|Purging) ' | sed -E 's/^\( *[0-9]+\/[0-9]+\) //' \
		> "$tmp/upgrades" || true
	ssh "$host" 'apk info 2>/dev/null' | sort -u > "$tmp/installed"
	comm -23 "$tmp/repo-names" "$tmp/installed" |
		grep -vE -- '-(dev|dbg|doc|pyc)$|^qt6-|^pyside6' > "$tmp/missing" || true

	echo "upgrades: $(grep -c . "$tmp/upgrades" || true)"
	sed 's/^/  /' "$tmp/upgrades"
	grep -q 'Upgrading linux-' "$tmp/upgrades" && echo "  (new kernel: reboot afterwards)"
	echo "not installed, from $repo: $(grep -c . "$tmp/missing" || true)"
	[ ! -s "$tmp/missing" ] || echo "  $(tr '\n' ' ' < "$tmp/missing")"

	[ -n "$apply" ] || continue
	changed=$(grep -cE 'zynthian|-lv2|^.*(Upgrading|Installing) pd-' "$tmp/upgrades" || true)
	ssh "$host" 'sudo apk upgrade 2>&1 | grep -E "ERROR|WARNING|^OK"' || true
	# Packages of nura-builds that are still older than what is available (apk upgrade leaves
	# some, seen with zynthian-ui and zyncoder): apk version -l '<' lists them
	stale=$(ssh "$host" "apk version -l '<' -q 2>/dev/null" | sort -u | comm -12 - "$tmp/repo-names" |
		tr '\n' ' ')
	stale=${stale% }
	if [ -n "$stale" ]; then
		echo "upgrading by name: $stale"
		# shellcheck disable=SC2029 # expanded here on purpose
		ssh "$host" "sudo apk add -u $stale 2>&1 | grep -E 'ERROR|^OK'" || true
		changed=1
	fi
	if [ -n "$all" ] && [ -s "$tmp/missing" ]; then
		echo "installing: $(tr '\n' ' ' < "$tmp/missing")"
		# shellcheck disable=SC2029
		ssh "$host" "sudo apk add $(tr '\n' ' ' < "$tmp/missing") 2>&1 | grep -E 'ERROR|^OK'" || true
		changed=1
	fi
	if [ -n "$restart" ] && [ "${changed:-0}" != 0 ]; then
		echo "rescanning LV2 plugins, restarting the session"
		ssh "$host" 'cd /usr/share/zynthian/zynthian-ui/zyngine &&
			env PYTHONPATH=/usr/share/zynthian/python ZYNTHIAN_DIR=/usr/share/zynthian ZYNTHIAN_LIB_DIR=/usr/lib/zynthian \
			sh -c ". ../desktop/zynthian_desktop_env.sh 2>/dev/null; timeout 600 python3 ./zynthian_lv2.py engines" 2>&1 | tail -n 1
			sudo systemctl daemon-reload; sudo systemctl restart tinydm'
	fi
done
