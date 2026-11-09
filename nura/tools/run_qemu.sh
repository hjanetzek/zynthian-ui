#!/bin/sh
# Run a Nura amd64 image (nura-builds' qemu-amd64 device) on this desktop in QEMU: KVM, OpenGL through virgl
# (virtio-vga-gl: the guest's Mesa renders on the desktop's GPU), PipeWire audio, SSH and webconf
# forwarded, USB devices (MIDI controllers) passed through.
#
#   nura/tools/run_qemu.sh [options] [IMAGE]
#
# IMAGE: an .img or .img.zst. Default: the latest build of nura-builds (release
# "zynthian-latest", zynthian-qemu-amd64.img.zst), downloaded to the cache directory and
# unpacked once; later runs boot the same disk (state kept) until -r or -u.
#
#   -u          download the newest image (if the release has a newer one) and start from it
#   -r          start from a fresh copy of the downloaded image (discards the VM's changes)
#   -s SIZE     disk size of a fresh copy (default 8G; postmarketOS grows its root partition to the
#               disk at the first boot)
#   -m MEM      memory (default 4G)
#   -c CPUS     virtual CPUs (default: half of this machine's)
#   -R WxH      the screen's resolution (default 1280x800: 16:10 as the Duet, whose 1920x1200 at
#               the kiosk's scale 1.5 is the same 1280x800 logical pixels), e.g. 1024x600, 800x480
#   -D DISPLAY  gtk (default), sdl, or none: no window (agents, tests; screenshots with grim in the
#               guest): OpenGL through egl-headless if QEMU has it (qemu-ui-egl-headless), else
#               software rendering in the guest. Headless (or without a terminal) the serial console
#               goes to serial.log in the cache directory, QEMU's PID to qemu.pid
#   -n          no OpenGL (software rendering in the guest: slow, for checking a GL problem)
#   -A AUDIO    virtio (default: virtio-sound, QEMU 8.2+) or hda (emulated Intel HDA), none, or
#               silent (Intel HDA without host output: the guest's audio clock runs, nothing is
#               heard; for long unattended zynthian tests, where -A none can stall PipeWire's graph)
#   -U VID:PID  pass a USB device through (repeatable), e.g. -U 17cc:1140 (Maschine Mk2). Needs
#               write access to its /dev/bus/usb node (a udev rule, or run as root)
#   -p PORT     host port for the VM's SSH (default 2222, or the next free one: ssh -p PORT user@localhost)
#   -w PORT     host port for the VM's webconf (default 8080, or the next free one: http://localhost:PORT)
#   -d DIR      cache directory (default ~/.cache/nura-builds)
#
# Needs qemu-system-x86_64 (with the virtio-vga-gl device: QEMU's GL/virglrenderer support),
# OVMF (edk2-ovmf / ovmf), zstd, curl; /dev/kvm for full speed (without it QEMU emulates, slowly).
set -eu

usage() { sed -n '2,/^set -eu/{/^set -eu/d;s/^# \{0,1\}//;p}' "$0"; exit "${1:-0}"; }

url=https://github.com/hjanetzek/nura-builds/releases/download/zynthian-latest/zynthian-qemu-amd64.img.zst
cache=${XDG_CACHE_HOME:-$HOME/.cache}/nura-builds
update=0 reset=0 size=8G mem=4G cpus= res=1280x800 display=gtk gl=on audio=virtio usb= ssh_port= web_port=
while getopts urs:m:c:R:D:nA:U:p:w:d:h opt; do
	case $opt in
		u) update=1 ;;
		r) reset=1 ;;
		s) size=$OPTARG ;;
		m) mem=$OPTARG ;;
		c) cpus=$OPTARG ;;
		R) res=$OPTARG ;;
		D) display=$OPTARG ;;
		n) gl=off ;;
		A) audio=$OPTARG ;;
		U) usb="$usb $OPTARG" ;;
		p) ssh_port=$OPTARG ;;
		w) web_port=$OPTARG ;;
		d) cache=$OPTARG ;;
		h) usage ;;
		*) usage 1 ;;
	esac
done
shift $((OPTIND - 1))
[ $# -le 1 ] || usage 1

for cmd in qemu-system-x86_64 zstd; do
	command -v "$cmd" >/dev/null || { echo "$cmd not found" >&2; exit 1; }
done

# The release file through GitHub's API (when the download URL fails: seen with HTTP 504 for
# release downloads while the API's asset URL worked); without authentication (60 API calls/hour)
download_api() {
	echo "retrying through the GitHub API" >&2
	api=https://api.github.com/repos/hjanetzek/nura-builds/releases/tags/zynthian-latest
	asset=$(curl -fsL "$api" | tr '{},' '\n\n\n' | grep -B8 '"name": *"zynthian-qemu-amd64.img.zst"' |
		sed -n 's|.*"url": *"\(https://api.github.com/[^"]*/assets/[0-9]*\)".*|\1|p' | tail -n 1)
	[ -n "$asset" ] || { echo "no zynthian-qemu-amd64.img.zst in the release" >&2; return 1; }
	curl -fLR --progress-bar "$@" -H "Accept: application/octet-stream" -o "$zst.part" "$asset"
}

# The disk: a given .img as it is; a .img.zst (given or downloaded) unpacked to the cache
mkdir -p "$cache"
if [ $# -eq 1 ] && [ "${1%.zst}" = "$1" ]; then
	disk=$1
else
	if [ $# -eq 1 ]; then
		zst=$1
	else
		zst=$cache/zynthian-qemu-amd64.img.zst
		if [ ! -f "$zst" ] || [ $update = 1 ]; then
			echo "downloading $url"
			old=$(stat -c %Y "$zst" 2>/dev/null || echo 0)
			# -z: only if the release's file is newer than the local copy; -R: keep its time
			if [ -f "$zst" ]; then
				set -- -z "$zst"
			else
				set --
			fi
			if ! curl -fLR --progress-bar "$@" -o "$zst.part" "$url" && ! download_api "$@"; then
				rm -f "$zst.part"
				echo "can't download the image: is it published yet? (the release zynthian-latest gets it" >&2
				echo "from Run workflow > architecture x86_64 with images)" >&2
				[ -f "$zst" ] || exit 1
				echo "using the downloaded $zst" >&2
			fi
			set --
			if [ -s "$zst.part" ]; then
				mv "$zst.part" "$zst"
			else
				rm -f "$zst.part"
			fi
			[ "$(stat -c %Y "$zst")" = "$old" ] || reset=1
		fi
	fi
	disk=$cache/$(basename "${zst%.zst}")
	if [ ! -f "$disk" ] || [ $reset = 1 ]; then
		echo "unpacking $zst"
		zstd -d -q -f "$zst" -o "$disk"
		truncate -s ">$size" "$disk"
	fi
fi

# UEFI firmware (the image boots with systemd-boot)
ovmf=
for f in /usr/share/edk2/x64/OVMF.4m.fd /usr/share/edk2/x64/OVMF.fd /usr/share/OVMF/OVMF.fd \
	/usr/share/edk2/ovmf/OVMF.fd /usr/share/qemu/ovmf-x86_64.bin /usr/share/ovmf/OVMF.fd; do
	[ -f "$f" ] && { ovmf=$f; break; }
done
[ -n "$ovmf" ] || { echo "no OVMF firmware found: install edk2-ovmf (or ovmf)" >&2; exit 1; }

# QEMU's optional modules (distributions package them separately: on Arch qemu-hw-display-*,
# qemu-ui-*, qemu-audio-*, qemu-hw-usb-host; Debian/Ubuntu: qemu-system-gui, qemu-system-modules-*)
devices=$(qemu-system-x86_64 -device help 2>/dev/null)
audiodevs=$(qemu-system-x86_64 -audiodev help 2>/dev/null)
displays=$(qemu-system-x86_64 -display help 2>/dev/null)
missing=
has_device() { echo "$devices" | grep -q "name \"$1\""; }
if [ "$gl" = on ] && [ "$display" != none ]; then
	# (the -gl modules need the plain virtio-gpu/-vga ones too: without them QEMU lists none)
	has_device virtio-vga-gl || missing="$missing qemu-hw-display-virtio-gpu qemu-hw-display-virtio-gpu-gl qemu-hw-display-virtio-gpu-pci qemu-hw-display-virtio-gpu-pci-gl qemu-hw-display-virtio-vga qemu-hw-display-virtio-vga-gl qemu-ui-opengl"
else
	has_device virtio-vga || missing="$missing qemu-hw-display-virtio-vga qemu-hw-display-virtio-gpu"
fi
if [ "$display" = none ]; then
	# Headless: OpenGL only through egl-headless
	echo "$displays" | grep -qx egl-headless || gl=off
	has_device virtio-vga-gl || gl=off
else
	echo "$displays" | grep -qx "$display" || missing="$missing qemu-ui-$display"
fi
if [ "$audio" != none ] && [ "$audio" != silent ]; then
	echo "$audiodevs" | grep -qx -e pipewire -e pa || missing="$missing qemu-audio-pipewire"
fi
if [ -n "$usb" ]; then
	has_device usb-host || missing="$missing qemu-hw-usb-host"
fi
if [ -n "$missing" ]; then
	echo "QEMU lacks modules this needs; on Arch: sudo pacman -S$missing" >&2
	echo "(or -n for no OpenGL, -A none for no audio)" >&2
	exit 1
fi

[ -n "$cpus" ] || cpus=$(( $(nproc) / 2 ))
[ "$cpus" -ge 1 ] || cpus=1

# Host ports: the given ones, else the first free one from the default on
port_free() { ! ss -Hltn "sport = :$1" 2>/dev/null | grep -q .; }
free_port() {
	p=$1
	while ! port_free "$p"; do p=$((p + 1)); done
	echo "$p"
}
[ -n "$ssh_port" ] || ssh_port=$(free_port 2222)
[ -n "$web_port" ] || web_port=$(free_port 8080)
[ "$web_port" != "$ssh_port" ] || web_port=$(free_port $((web_port + 1)))

set -- -nodefaults -machine q35 -smp "$cpus" -m "$mem" \
	-drive "if=pflash,format=raw,readonly=on,file=$ovmf" \
	-drive "file=$disk,format=raw,if=none,id=disk" -device virtio-blk-pci,drive=disk,bootindex=0 \
	-device virtio-tablet-pci -device virtio-keyboard-pci \
	-netdev "user,id=net,hostfwd=tcp:127.0.0.1:$ssh_port-:22,hostfwd=tcp:127.0.0.1:$web_port-:8080" \
	-device virtio-net-pci,netdev=net,romfile= \
	-fw_cfg name=opt/org.tianocore/IPv4PXESupport,string=n \
	-fw_cfg name=opt/org.tianocore/IPv6PXESupport,string=n

if [ -w /dev/kvm ]; then
	set -- "$@" -enable-kvm -cpu host
else
	echo "warning: no access to /dev/kvm, QEMU emulates the CPU (slow)" >&2
fi

# The screen: the guest's preferred mode (virtio-gpu's EDID). A GTK window reports its own first
# size instead, so the size also goes to the guest as SMBIOS SKU "nura-screen=WxH": the kiosk
# session (postmarketos-ui-zynthian's zynthian-session.sh) sets that mode.
xres=${res%x*} yres=${res#*x}
set -- "$@" -smbios "type=1,sku=nura-screen=${xres}x${yres}"
if [ "$display" = none ]; then
	if [ "$gl" = on ]; then
		set -- "$@" -device "virtio-vga-gl,xres=$xres,yres=$yres" -display egl-headless
	else
		set -- "$@" -device "virtio-vga,xres=$xres,yres=$yres" -display none
	fi
elif [ "$gl" = on ]; then
	set -- "$@" -device "virtio-vga-gl,xres=$xres,yres=$yres" -display "$display,gl=on,show-cursor=on"
else
	set -- "$@" -device "virtio-vga,xres=$xres,yres=$yres" -display "$display,show-cursor=on"
fi

# Serial console: here, or (headless, no terminal) in a file; the PID for stopping a background VM
serial_log=
if [ "$display" = none ] || [ ! -t 0 ]; then
	serial_log=$cache/serial.log
	set -- "$@" -serial "file:$serial_log"
else
	set -- "$@" -serial mon:stdio
fi
set -- "$@" -pidfile "$cache/qemu.pid"

# Audio through the desktop's PipeWire (or PulseAudio)
if [ "$audio" = silent ]; then
	set -- "$@" -audiodev none,id=snd -device intel-hda -device hda-duplex,audiodev=snd
elif [ "$audio" != none ]; then
	if command -v pw-cli >/dev/null; then
		set -- "$@" -audiodev pipewire,id=snd
	else
		set -- "$@" -audiodev pa,id=snd
	fi
	case $audio in
		virtio) set -- "$@" -device virtio-sound-pci,audiodev=snd ;;
		hda) set -- "$@" -device intel-hda -device hda-duplex,audiodev=snd ;;
		*) echo "unknown audio $audio" >&2; exit 1 ;;
	esac
fi

# USB passthrough (xHCI)
if [ -n "$usb" ]; then
	set -- "$@" -device qemu-xhci,id=xhci
	for dev in $usb; do
		set -- "$@" -device "usb-host,bus=xhci.0,vendorid=0x${dev%%:*},productid=0x${dev#*:}"
	done
fi

echo "disk:    $disk"
echo "screen:  ${xres}x${yres}"
echo "ssh:     ssh -p $ssh_port <user>@localhost"
echo "webconf: http://localhost:$web_port"
echo "opengl:  $gl"
if [ -n "$serial_log" ]; then
	echo "serial:  $serial_log; stop: kill \$(cat $cache/qemu.pid)"
else
	echo "serial console here (Ctrl-A x quits QEMU, Ctrl-A c the monitor)"
fi
exec qemu-system-x86_64 "$@"
