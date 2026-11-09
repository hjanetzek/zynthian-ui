#!/bin/sh
usage_text='Run upstream zynthian (Tk UI) and the Qt port side by side in two QEMU VMs, at the V5 kit'"'"'s
screen size, to compare them (docs/qemu-testing.md, "Side by side").

Usage: qemu_compare.sh [options] [start | stop | status | shot [DIR] | ssh qt|tk [CMD...]]

  start       start both VMs (default): set them up on the first start (SSH key, sudo, grim) and
              install the UI package each one runs
  stop        shut both down (sudo poweroff, then kill)
  status      their ports, PIDs and installed zynthian-ui packages
  shot [DIR]  a screenshot of each (DIR/qt.png, DIR/tk.png, and DIR/side-by-side.png with
              ImageMagick on this machine); DIR default: the current directory
  ssh qt|tk   a shell (or CMD) in one of them

  -g          windows and sound: GTK windows, audio through the desktop'"'"'s PipeWire (default:
              headless, a silent sound card; screenshots with "shot")
  -T BRANCH   the upstream zynthian-ui in the Tk VM: tomita (default: development, the branch the
              Qt port is based on) or vangelis (stable); "port" for this repository'"'"'s own Tk UI
              (ZYNTHIAN_UI=tk) instead
  -R WxH      screen size (default 800x480: the V5 kit'"'"'s display)
  -r          fresh disks from the image (discards both VMs'"'"' changes)
  -i IMAGE    the image (.img.zst) for new disks (default: the user'"'"'s downloaded one,
              ~/.cache/nura-builds/zynthian-qemu-amd64.img.zst, else run_qemu.sh downloads it)
  -d BASE     directories BASE-qt and BASE-tk (default ~/.cache/nura-builds-compare)
  -p PORT     SSH ports PORT (Qt) and PORT+1 (Tk), webconf 8080 + the same offset
              (default 2242: 2242/2243, webconf 8100/8101)
  -m MEM      memory per VM (default 3G)

The Qt VM runs the image'"'"'s zynthian-ui (the Qt port), the Tk VM zynthian-ui-tomita or -vangelis
from nura-builds'"'"' x86_64 package repository (upstream zynthian-ui with the port patches). To
test changes of this checkout in the Qt VM: NURA_VM_PORT=2242 nura/tools/sync_ui.sh -V -r.'
set -eu
here=$(cd "$(dirname "$0")" && pwd)

usage() { printf '%s\n' "$usage_text"; exit "${1:-0}"; }

gui=0 tk=tomita res=800x480 reset=0 base=$HOME/.cache/nura-builds-compare port=2242 mem=3G
image=${XDG_CACHE_HOME:-$HOME/.cache}/nura-builds/zynthian-qemu-amd64.img.zst
while getopts gT:R:ri:d:p:m:h opt; do
	case $opt in
		g) gui=1 ;;
		T) tk=$OPTARG ;;
		R) res=$OPTARG ;;
		r) reset=1 ;;
		i) image=$OPTARG ;;
		d) base=$OPTARG ;;
		p) port=$OPTARG ;;
		m) mem=$OPTARG ;;
		h) usage ;;
		*) usage 1 ;;
	esac
done
shift $((OPTIND - 1))
cmd=${1:-start}
[ $# -eq 0 ] || shift
case $tk in vangelis | tomita | port) ;; *) usage 1 ;; esac

# The two VMs: name, directory, SSH and webconf ports
vm_dir() { echo "$base-$1"; }
vm_port() { if [ "$1" = qt ]; then echo "$port"; else echo $((port + 1)); fi; }
vm_web() { echo $((8080 + $(vm_port "$1") - 2222)); }

ssh_opts="-o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=10"
# shellcheck disable=SC2086 # $ssh_opts: several options
vm_ssh() { v=$1; shift; ssh $ssh_opts -p "$(vm_port "$v")" user@127.0.0.1 "$@"; }

vm_pid() {
	f=$(vm_dir "$1")/qemu.pid
	[ -f "$f" ] && kill -0 "$(cat "$f")" 2>/dev/null && cat "$f"
}

start_vm() {
	v=$1 dir=$(vm_dir "$1")
	if [ -n "$(vm_pid "$v")" ]; then
		echo "$v: running (PID $(vm_pid "$v"))"
		return
	fi
	mkdir -p "$dir"
	# A new disk from the image: run_qemu.sh unpacks the .img.zst it finds in its directory (a link
	# to the user's download, so it isn't downloaded again)
	if [ ! -e "$dir/zynthian-qemu-amd64.img.zst" ] && [ -f "$image" ]; then
		ln -sf "$image" "$dir/zynthian-qemu-amd64.img.zst"
	fi
	set -- -d "$dir" -R "$res" -m "$mem" -p "$(vm_port "$v")" -w "$(vm_web "$v")"
	[ $reset = 0 ] || set -- "$@" -r
	if [ $gui = 1 ]; then
		set -- "$@" -D gtk
	else
		set -- "$@" -D none -A silent
	fi
	echo "$v: starting (SSH $(vm_port "$v"), webconf $(vm_web "$v"), log $dir/run.log)"
	setsid "$here/run_qemu.sh" "$@" < /dev/null > "$dir/run.log" 2>&1 &
	# the next VM uses the image this one may be downloading: wait until its disk exists
	i=0
	while [ ! -f "$dir/zynthian-qemu-amd64.img" ] || [ -z "$(vm_pid "$v")" ]; do
		i=$((i + 1))
		if [ $i -gt 600 ] || ! kill -0 $! 2>/dev/null; then
			echo "$v: QEMU didn't start:" >&2
			tail -n 20 "$dir/run.log" >&2
			exit 1
		fi
		sleep 1
	done
	[ -e "$image" ] || image=$dir/zynthian-qemu-amd64.img.zst
}

# Wait for SSH; on a new disk install the SSH key and passwordless sudo (qemu_setup.sh) and bring
# the packages up to date (the image may be older than nura-builds' x86_64 repository). Both VMs
# show the UI at scale 1, as the V5 kit (kiosk packages before r21 use the Duet's 1.5 in a VM too).
nura_repo=https://github.com/hjanetzek/nura-builds/releases/download
nura_key=https://raw.githubusercontent.com/hjanetzek/nura-builds/main/keys/nura-builds-ci.rsa.pub
setup_vm() {
	v=$1 upgrade=0
	if ! vm_ssh "$v" true 2>/dev/null; then
		echo "$v: setting up SSH (first boot of a new disk takes about a minute)"
		"$here/qemu_setup.sh" -p "$(vm_port "$v")" > /dev/null
		upgrade=1
	fi
	# nura-builds' package repository (release x86_64: apk appends the architecture), which the
	# image doesn't have: zynthian-ui-tomita/-vangelis and everything newer than the image
	if ! vm_ssh "$v" "grep -qxF '$nura_repo' /etc/apk/repositories"; then
		echo "$v: adding nura-builds' package repository"
		vm_ssh "$v" "set -e
			sudo wget -q -O /etc/apk/keys/nura-builds-ci.rsa.pub '$nura_key'
			echo '$nura_repo' | sudo tee -a /etc/apk/repositories >/dev/null"
		upgrade=1
	fi
	if [ $upgrade = 1 ]; then
		echo "$v: upgrading the packages"
		vm_ssh "$v" 'sudo apk update -q 2>&1 | grep -v "^WARNING: Permanently redirected"
			sudo apk upgrade -q 2>&1 | grep -v "^WARNING: Permanently redirected" || true'
	fi
	# grim for screenshots; font-dejavu: the Tk UI's mixer loads DejaVuSans.ttf and dies without it
	# (a dependency of zynthian-ui since 2026-11-09, missing in older images and packages)
	vm_ssh "$v" 'sudo apk add -q grim font-dejavu 2>/dev/null
		if ! grep -qx "ZYNTHIAN_OUTPUT_SCALE=1" /etc/default/zynthian 2>/dev/null; then
			sudo sed -i "/^ZYNTHIAN_OUTPUT_SCALE=/d" /etc/default/zynthian 2>/dev/null || true
			echo ZYNTHIAN_OUTPUT_SCALE=1 | sudo tee -a /etc/default/zynthian >/dev/null
			sudo systemctl restart tinydm
		fi'
}

# The UI package of each VM (switch_ui.sh; a restart of the kiosk session when it changes)
setup_ui() {
	v=$1
	if [ "$v" = qt ]; then
		NURA_VM_PORT=$(vm_port qt) "$here/switch_ui.sh" -V qt
	elif [ "$tk" = port ]; then
		NURA_VM_PORT=$(vm_port tk) "$here/switch_ui.sh" -V qt
		vm_ssh tk 'grep -qx "ZYNTHIAN_UI=tk" /etc/default/zynthian 2>/dev/null || {
			sudo sed -i "/^ZYNTHIAN_UI=/d" /etc/default/zynthian 2>/dev/null || true
			echo ZYNTHIAN_UI=tk | sudo tee -a /etc/default/zynthian >/dev/null
			sudo systemctl restart tinydm; }'
	else
		vm_ssh tk 'sudo apk update -q >/dev/null 2>&1 || true'
		NURA_VM_PORT=$(vm_port tk) "$here/switch_ui.sh" -V "$tk" || {
			echo "tk: zynthian-ui-$tk isn't available (published in nura-builds' x86_64 release?)" >&2
			echo "    -T port runs this repository's Tk UI instead" >&2
			exit 1
		}
	fi
}

case $cmd in
	start)
		start_vm qt
		start_vm tk
		setup_vm qt
		setup_vm tk
		setup_ui qt
		setup_ui tk
		echo "ready: Qt port on SSH $(vm_port qt) (webconf http://localhost:$(vm_web qt)), upstream on SSH $(vm_port tk) (webconf http://localhost:$(vm_web tk))"
		echo "screenshots: $0 shot DIR"
		;;
	stop)
		for v in qt tk; do
			pid=$(vm_pid "$v") || true
			[ -n "$pid" ] || { echo "$v: not running"; continue; }
			vm_ssh "$v" 'sudo poweroff' 2>/dev/null || true
			i=0
			while kill -0 "$pid" 2>/dev/null && [ $i -lt 30 ]; do sleep 1; i=$((i + 1)); done
			kill "$pid" 2>/dev/null || true
			echo "$v: stopped"
		done
		;;
	status)
		for v in qt tk; do
			pid=$(vm_pid "$v") || true
			if [ -z "$pid" ]; then
				echo "$v: not running ($(vm_dir "$v"))"
				continue
			fi
			ui=$(vm_ssh "$v" "apk info -v 2>/dev/null | grep -E '^zynthian-ui(-vangelis|-tomita)?-[0-9]'; grep -h '^ZYNTHIAN_UI=' /etc/default/zynthian 2>/dev/null" 2>/dev/null | tr '\n' ' ') || true
			echo "$v: PID $pid, SSH $(vm_port "$v"), webconf $(vm_web "$v"), ${ui:-no SSH yet}"
		done
		;;
	shot)
		dir=${1:-.}
		mkdir -p "$dir"
		for v in qt tk; do
			NURA_VM_PORT=$(vm_port "$v") "$here/screenshot.sh" -V -s 1 "$dir/$v.png" > /dev/null
		done
		if command -v magick >/dev/null; then
			magick "$dir/tk.png" "$dir/qt.png" +append "$dir/side-by-side.png"
		elif command -v convert >/dev/null; then
			convert "$dir/tk.png" "$dir/qt.png" +append "$dir/side-by-side.png"
		fi
		ls "$dir"/qt.png "$dir"/tk.png "$dir"/side-by-side.png 2>/dev/null
		;;
	ssh)
		[ $# -ge 1 ] || usage 1
		v=$1; shift
		case $v in qt | tk) ;; *) usage 1 ;; esac
		# shellcheck disable=SC2086
		exec ssh $ssh_opts -t -p "$(vm_port "$v")" user@127.0.0.1 "$@"
		;;
	*) usage 1 ;;
esac
