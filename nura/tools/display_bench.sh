#!/bin/sh
usage_text='Measure a display device on the device: how fast full frames reach the panel, below the UI.
For comparing the drivers of a kit'"'"'s panel (fbtft framebuffer against DRM, nura-builds
docs/zynthian-rpi.md), e.g. the V4 kit'"'"'s ZynScreen 3.5 over SPI.

Usage: display_bench.sh [-c CONFIG] [-H HOST] [-u USER] [-P PORT] [-V] [-n FRAMES] [list | fb DEV | drm DRIVER]

  list        the framebuffers and DRM devices with their drivers and modes (default)
  fb DEV      write FRAMES full frames to /dev/DEV (e.g. fb1) and report frames per second
              (fbtft sends the written pages to the panel)
  drm DRIVER  page flips on the DRM device of DRIVER (e.g. ili9486) with libdrm'"'"'s modetest,
              which reports the rate (needs libdrm-tests; the display must be free: stop the
              kiosk session first, sudo systemctl stop tinydm)
  -n FRAMES   frames for "fb" (default 100)'
set -eu
here=$(cd "$(dirname "$0")" && pwd)
. "$here/common.sh"

frames=100
tool_opts="n:"
tool_opt() {
	case $1 in
		n) frames=$2 ;;
	esac
}
parse_common "$@"
shift $((OPTIND - 1))
setup_target

case ${1:-list} in
	list)
		dev 'for f in /sys/class/graphics/fb[0-9]*; do
				[ -e "$f" ] || continue
				echo "$(basename $f): $(cat $f/name 2>/dev/null) $(cat $f/virtual_size 2>/dev/null | tr , x) $(cat $f/bits_per_pixel 2>/dev/null) bpp"
			done
			for c in /sys/class/drm/card[0-9]; do
				[ -e "$c" ] || continue
				drv=$(basename "$(readlink -f $c/device/driver)" 2>/dev/null)
				echo "$(basename $c): driver $drv"
				for k in $c-*; do
					[ -e "$k/status" ] || continue
					echo "  $(basename $k): $(cat $k/status), modes $(tr "\n" " " < $k/modes)"
				done
			done'
		;;
	fb)
		[ $# -eq 2 ] || usage 1
		fb=$2
		case $fb in *[!a-z0-9]*) usage 1 ;; esac
		dev "set -e
			f=/sys/class/graphics/$fb
			size=\$(cat \$f/virtual_size); bpp=\$(cat \$f/bits_per_pixel)
			bytes=\$(( \${size%,*} * \${size#*,} * bpp / 8 ))
			echo \"$fb: \$(cat \$f/name) \${size%,*}x\${size#*,} \$bpp bpp, \$bytes bytes per frame\"
			head -c \$bytes /dev/urandom > /tmp/frame.raw
			start=\$(date +%s%N)
			i=0
			while [ \$i -lt $frames ]; do sudo dd if=/tmp/frame.raw of=/dev/$fb bs=\$bytes count=1 status=none; i=\$((i + 1)); done
			# fbtft sends the pages it was given after its deferred I/O delay: let it finish
			sync; sleep 0.5
			end=\$(date +%s%N)
			rm -f /tmp/frame.raw
			awk -v n=$frames -v ns=\$((end - start)) 'BEGIN { printf \"%d frames in %.2f s: %.1f fps (written; the panel may skip frames under load)\\n\", n, ns / 1e9, n / (ns / 1e9) }'"
		;;
	drm)
		[ $# -eq 2 ] || usage 1
		drv=$2
		case $drv in *[!a-z0-9_-]*) usage 1 ;; esac
		dev "set -e
			command -v modetest >/dev/null || { echo 'modetest not found: sudo apk add libdrm-tests' >&2; exit 1; }
			conn=\$(sudo modetest -M $drv -c | awk '/connected/ && \$3 == \"connected\" { print \$1; exit }')
			mode=\$(sudo modetest -M $drv -c | awk '/^  #0 / { print \$2; exit }')
			[ -n \"\$conn\" ] && [ -n \"\$mode\" ] || { echo 'no connected connector on $drv' >&2; exit 1; }
			echo \"$drv: connector \$conn, mode \$mode; page flips for 10 s:\"
			sudo timeout -s INT 10 modetest -M $drv -s \$conn:\$mode -v 2>&1 | grep -E 'freq|Hz' | tail -n 3 || true"
		;;
	*) usage 1 ;;
esac
