#!/bin/sh
usage_text='Copy this checkout'"'"'s Python code into the zynthian-ui installed on the device (or the QEMU
VM with -V), for testing changes without building packages.

Usage: sync_ui.sh [-c CONFIG] [-H HOST] [-u USER] [-P PORT] [-V] [-r] [-n]

  -r   restart the kiosk session afterwards (systemctl restart tinydm), so zynthian runs the new code
  -n   dry run: list what would be copied

Copies what desktop/install.sh installs as Python: zyngui, zyngine, zynconf, zynautoconnect, zynqt,
the zynlibs modules, fonts, icons, img and the main scripts, into /usr/share/zynthian/zynthian-ui
(over ssh, with sudo; old files of these directories are removed first, so deleted modules go
too; files other packages install there, as the zyngine/ctrldev drivers of drivenbymoss, are kept).
Native libraries (zynlibs/*/build, zyncoder) are not copied: changes to them need the
package (deploy.sh). The next package upgrade replaces the copied files.'
set -eu
here=$(cd "$(dirname "$0")" && pwd)
. "$here/common.sh"

checkout=$(cd "$here/../.." && pwd)
restart=0
dry=0
tool_opts="rn"
tool_opt() {
	case $1 in
		r) restart=1 ;;
		n) dry=1 ;;
	esac
}
parse_common "$@"
shift $((OPTIND - 1))
setup_target

dst=/usr/share/zynthian/zynthian-ui
dirs="zyngui zyngine zynconf zynautoconnect zynqt fonts icons img"
files=$(cd "$checkout" && {
	for d in $dirs; do
		[ -d "$d" ] && find "$d" -name __pycache__ -prune -o \( -type f -o -type l \) -print
	done
	find zynlibs -name '*.py' ! -name 'unit_tests.py' ! -name 'test.py' ! -name 'format_docs.py'
	for f in zynthian_main.py zynthian_qt_main.py; do [ -f "$f" ] && echo "$f"; done
})
if [ $dry = 1 ]; then
	echo "$files"
	echo "$(echo "$files" | wc -l) files to $target:$dst"
	exit 0
fi

dev "test -d $dst" || { echo "no zynthian-ui installed on $target ($dst)" >&2; exit 1; }
# shellcheck disable=SC2086 # $dirs: a list
# Unpacked to a temporary directory first, then the directories are replaced (a broken connection
# doesn't leave a half-copied tree)
echo "$files" | (cd "$checkout" && tar -cf - -T -) |
	dev "set -e; t=\$(mktemp -d); tar -C \"\$t\" -xf -
		cd $dst
		# Keep the files other packages install into these directories (drivenbymoss's
		# zyngine/ctrldev drivers, zyncoder's module): copy them into the new tree first
		awk -v pre=\"${dst#/}/\" '/^P:/ { p = substr(\$0, 3) } /^F:/ { d = substr(\$0, 3) }
			/^R:/ && p != \"zynthian-ui\" && index(d \"/\", pre) == 1 { f = d \"/\" substr(\$0, 3); print substr(f, length(pre) + 1) }' \
			/lib/apk/db/installed | while read -r f; do [ -e \"\$f\" ] && echo \"\$f\"; done |
			tar -cf - -T - | tar -C \"\$t\" -xkf - 2>/dev/null || true
		for d in $dirs; do [ -d \"\$t/\$d\" ] || continue; sudo rm -rf \"\$d\"; sudo cp -R \"\$t/\$d\" .; done
		sudo cp -R \"\$t\"/zynlibs .
		for f in zynthian_main.py zynthian_qt_main.py; do [ -f \"\$t/\$f\" ] && sudo cp \"\$t/\$f\" .; done
		sudo chown -R root:root $dst; rm -rf \"\$t\""
echo "copied $(echo "$files" | wc -l) files to $target:$dst"

if [ $restart = 1 ]; then
	dev 'sudo systemctl restart tinydm'
	echo "kiosk session restarted"
fi
