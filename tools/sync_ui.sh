#!/bin/sh
usage_text='Copy this checkout'"'"'s Python code into the zynthian-ui installed on the device (or the QEMU
VM with -V), for testing changes without building packages.

Usage: sync_ui.sh [-c CONFIG] [-H HOST] [-u USER] [-P PORT] [-V] [-r | -R [-t SECONDS]] [-q] [-n]

  -r   restart the kiosk session afterwards (systemctl restart tinydm), so zynthian runs the new code
  -R   restart only zynthian (CUIA RESTART_UI over OSC: the launcher starts it again inside the
       running compositor, no new session; it re-reads ~/.config/zynthian/zynthian_envars.sh and
       zynthian_custom_config.sh, not /etc/default/zynthian). Falls back to -r without a running UI.
       Checked (zynthian ignores RESTART_UI while busy; nothing is killed): waits until zynthian is
       idle (OSC query /STATUS/BUSY; shows what it is busy with), sends RESTART_UI, waits until that
       process has ended, a new one runs and answers idle (started, snapshot loaded). Exits non-zero
       with the reason otherwise: 2 still busy (RESTART_UI not sent), 3 no restart, 4 no new
       process, 5 the new one isn'"'"'t ready. A zynthian without the query (older code) gets
       RESTART_UI unchecked after 10 s without an answer; the restart is still checked.
  -t   seconds to wait for each of these steps (default 60)
  -q   QML only: copy zynqt/qml and nothing else, no restart (with ZYNTHIAN_QT_QMLPREVIEW=1 and
       qmlpreview watching the copy, docs/qt-theming.md: the running UI reloads it)
  -n   dry run: list what would be copied

Copies what desktop/install.sh installs as Python: zyngui, zyngine, zynconf, zynautoconnect, zynqt,
the zynlibs modules, fonts, icons, img, lv2 (widget bundles), the main scripts, the launcher and its environment (desktop/zynthian_desktop.sh, _env.sh), into /usr/share/zynthian/zynthian-ui
(over ssh, with sudo; old files of these directories are removed first, so deleted modules go
too; files other packages install there, as the zyngine/ctrldev drivers of drivenbymoss, are kept).
Native libraries (zynlibs/*/build, zyncoder) are not copied: changes to them need the
package (deploy.sh). The next package upgrade replaces the copied files.'
set -eu
here=$(cd "$(dirname "$0")" && pwd)
. "$here/common.sh"

checkout=$(cd "$here/.." && pwd)
restart=0
dry=0
wait=60
tool_opts="rRqnt:"
qml_only=0
tool_opt() {
	case $1 in
		r) restart=1 ;;
		R) restart=2 ;;
		q) qml_only=1 ;;
		n) dry=1 ;;
		t) wait=$2 ;;
	esac
}
parse_common "$@"
shift $((OPTIND - 1))
setup_target

dst=/usr/share/zynthian/zynthian-ui
if [ $qml_only = 1 ]; then
	# Replaced file by file (not the directory: qmlpreview watches the files)
	(cd "$checkout" && tar -cf - zynqt/qml) | dev "set -e; t=\$(mktemp -d); tar -C \"\$t\" -xf -
		sudo cp -R \"\$t\"/zynqt/qml/. $dst/zynqt/qml/; sudo chown -R root:root $dst/zynqt/qml; rm -rf \"\$t\""
	echo "copied zynqt/qml to $target:$dst"
	exit 0
fi
dirs="zyngui zyngine zynconf zynautoconnect zynqt fonts icons img lv2"
files=$(cd "$checkout" && {
	for d in $dirs; do
		[ -d "$d" ] && find "$d" -name __pycache__ -prune -o \( -type f -o -type l \) -print
	done
	find zynlibs -name '*.py' ! -name 'unit_tests.py' ! -name 'test.py' ! -name 'format_docs.py'
	for f in zynthian_main.py zynthian_qt_main.py desktop/zynthian_desktop.sh desktop/zynthian_desktop_env.sh; do [ -f "$f" ] && echo "$f"; done
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
		# The launcher (ZYNTHIAN_QT_QMLPREVIEW): the running one reads its file as it goes, so a new
		# file moved over it (the old inode stays with the running shell), never overwritten
		if [ -f \"\$t/desktop/zynthian_desktop.sh\" ]; then sudo cp \"\$t/desktop/zynthian_desktop.sh\" desktop/.zynthian_desktop.sh.new; sudo mv desktop/.zynthian_desktop.sh.new desktop/zynthian_desktop.sh; fi
		if [ -f \"\$t/desktop/zynthian_desktop_env.sh\" ]; then sudo cp \"\$t/desktop/zynthian_desktop_env.sh\" desktop/; fi
		sudo chown -R root:root $dst; rm -rf \"\$t\""
echo "copied $(echo "$files" | wc -l) files to $target:$dst"

if [ $restart = 2 ]; then
	# restart_ui.py runs on the device: waits for idle, sends RESTART_UI, checks the new process
	rc=0
	dev "python3 - $wait" < "$here/restart_ui.py" || rc=$?
	case $rc in
		0) ;;
		10) restart=1 ;;   # zynthian isn't running
		*) exit "$rc" ;;
	esac
fi
if [ $restart = 1 ]; then
	dev 'sudo systemctl restart tinydm'
	echo "kiosk session restarted"
fi
