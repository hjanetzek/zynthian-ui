#!/bin/sh
# Put the remote sources of the packages built with --src into pmbootstrap's distfiles cache,
# so that "pmbootstrap build --src=... zynthian-ui" (which skips $source) builds without network:
# the Python packages that zynthian-ui bundles.
# Usage: seed-distfiles.sh [pmbootstrap config]   (needs sudo: the cache is owned by root)
set -eu

cfg=${1:-$HOME/.config/pmbootstrap-zynthian.cfg}
work=$(sed -n 's/^work *= *//p' "$cfg")
[ -n "$work" ] || { echo "no work dir in $cfg" >&2; exit 1; }
if [ ! -f "$work/version" ]; then
	echo "pmbootstrap work dir $work not initialised: run pmbootstrap -c $cfg init first" >&2
	exit 1
fi
dest="$work/cache_distfiles"
here=$(cd "$(dirname "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

for aport in zynthian-ui; do
	apkbuild="$here/$aport/APKBUILD"
	# Entries are "url" or "name::url"; the APKBUILD's variables expand when it is sourced.
	# shellcheck disable=SC1090 # the APKBUILD
	# (set +u: the APKBUILD uses variables that only abuild sets, like $srcdir)
	for entry in $(set +u; . "$apkbuild" && echo "$source"); do
		case $entry in
			*::*) name=${entry%%::*}; url=${entry#*::} ;;
			*://*) name=${entry##*/}; url=$entry ;;
			*) continue ;; # local file in the aport
		esac
		if [ -e "$dest/$name" ]; then
			echo "have $name"
			continue
		fi
		echo "fetch $name"
		curl -fsSL -o "$tmp/$name" "$url"
	done
	sed -n '/^sha512sums="/,/^"/p' "$apkbuild" | grep '  ' >> "$tmp/sha512sums"
done

# pmbootstrap creates the cache only when it first needs it; same owner and mode as it uses
[ -d "$dest" ] || sudo install -d -o root -g 300 -m 775 "$dest"
for f in "$tmp"/*; do
	name=$(basename "$f")
	[ "$name" = sha512sums ] && continue
	(cd "$tmp" && grep "  $name\$" sha512sums | sha512sum -c -)
	sudo install -m 664 -g 300 "$f" "$dest/$name"
done
ls -l "$dest"
