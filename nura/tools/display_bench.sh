#!/bin/sh
usage_text='Measure a display device on the device: how fast full frames reach the panel, below the UI.
For comparing the drivers of a kit'"'"'s panel (fbtft framebuffer against DRM, nura-builds
docs/zynthian-rpi.md), e.g. the V4 kit'"'"'s ZynScreen 3.5 over SPI.

Usage: display_bench.sh [-c CONFIG] [-H HOST] [-u USER] [-P PORT] [-V] [-n FRAMES] [list | fb DEV | drm DRIVER | watch SECONDS | scroll SECONDS]

  list        the framebuffers and DRM devices with their drivers and modes (default)
  fb DEV      write FRAMES full frames to /dev/DEV (e.g. fb1) and report frames per second:
              written, and sent to an SPI panel (its bytes sent through SPI: fbtft collects
              writes and sends at most its fps)
  drm DRIVER  page flips on the DRM device of DRIVER (e.g. ili9486) with libdrm'"'"'s modetest,
              which reports the rate (needs libdrm-tests; the display must be free: stop the
              kiosk session first, sudo systemctl stop tinydm)
  watch SECS  the traffic to the SPI panels during SECS seconds of normal use (the UI running):
              bytes per second and full frames per second
  scroll SECS like watch, while the UI scrolls a list: ARROW_DOWN/ARROW_UP over OSC (the
              CUIA of zynthian, localhost:1370) 5 times a second, alternating every 10; also the CPU time
              of the UI and the display server (Xorg, cage, Xwayland) in percent of one core
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
			spi=\$(readlink -f \$f/device)/statistics/bytes_tx
			[ -r \$spi ] && spi0=\$(cat \$spi) || spi=
			start=\$(date +%s%N)
			i=0
			while [ \$i -lt $frames ]; do sudo dd if=/tmp/frame.raw of=/dev/$fb bs=\$bytes count=1 status=none; i=\$((i + 1)); done
			# fbtft sends the pages it was given after its deferred I/O delay: let it finish
			sync; sleep 0.5
			end=\$(date +%s%N)
			[ -z \"\$spi\" ] || spi1=\$(cat \$spi)
			rm -f /tmp/frame.raw
			awk -v n=$frames -v ns=\$((end - start)) 'BEGIN { printf \"%d frames in %.2f s: %.1f fps written\\n\", n, ns / 1e9, n / (ns / 1e9) }'
			[ -z \"\$spi\" ] || awk -v b=\$((spi1 - spi0)) -v fb=\$bytes -v ns=\$((end - start)) 'BEGIN { printf \"panel (SPI): %.1f MB, %.1f full frames, %.1f fps\\n\", b / 1e6, b / fb, b / fb / (ns / 1e9) }'"
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
	watch)
		[ $# -eq 2 ] || usage 1
		secs=$2
		case $secs in *[!0-9]*) usage 1 ;; esac
		dev "set -e
			for f in /sys/class/graphics/fb[0-9]*; do
				s=\$(readlink -f \$f/device)/statistics/bytes_tx
				[ -r \$s ] || continue
				size=\$(cat \$f/virtual_size); bpp=\$(cat \$f/bits_per_pixel)
				echo \"\$(basename \$f) \$s \$(( \${size%,*} * \${size#*,} * bpp / 8 )) \$(cat \$s)\"
			done > /tmp/spi0
			[ -s /tmp/spi0 ] || { echo 'no SPI panel with statistics' >&2; exit 1; }
			sleep $secs
			while read -r fb s bytes b0; do
				b1=\$(cat \$s)
				awk -v fb=\$fb -v b=\$((b1 - b0)) -v fr=\$bytes -v t=$secs 'BEGIN { printf \"%s: %.1f kB/s, %.2f full frames/s over %d s\\n\", fb, b / t / 1e3, b / fr / t, t }'
			done < /tmp/spi0
			rm -f /tmp/spi0"
		;;
	scroll)
		[ $# -eq 2 ] || usage 1
		secs=$2
		case $secs in *[!0-9]*) usage 1 ;; esac
		dev "python3 - $secs" <<'PY'
import os, sys, time, glob
secs = int(sys.argv[1])
try:
    import liblo
except ImportError:
    import pyliblo3 as liblo
hz = os.sysconf("SC_CLK_TCK")
def procs():
    found = {}
    for d in glob.glob("/proc/[0-9]*"):
        try:
            cmd = open(d + "/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        for name, pat in (("ui", "zynthian_"), ("Xorg", "Xorg"), ("Xwayland", "Xwayland"), ("cage", "cage ")):
            if pat in cmd and "python3 -" not in cmd and (name != "ui" or "python" in cmd or "zynthian_gui" in cmd):
                found.setdefault(name, []).append(d)
    return found
def cpu(paths):
    t = 0
    for d in paths:
        try:
            f = open(d + "/stat").read().rsplit(")", 1)[1].split()
            t += int(f[11]) + int(f[12])
        except OSError:
            pass
    return t
def spi():
    out = []
    for f in glob.glob("/sys/class/graphics/fb[0-9]*"):
        s = os.path.realpath(f + "/device") + "/statistics/bytes_tx"
        if os.path.exists(s):
            w, h = open(f + "/virtual_size").read().strip().split(",")
            bpp = int(open(f + "/bits_per_pixel").read())
            out.append((os.path.basename(f), s, int(w) * int(h) * bpp // 8))
    return out
p = procs()
panels = spi()
c0 = {n: cpu(ds) for n, ds in p.items()}
b0 = {fb: int(open(s).read()) for fb, s, _ in panels}
t0 = time.time()
target = liblo.Address("localhost", 1370)
i = 0
while time.time() - t0 < secs:
    liblo.send(target, "/cuia/ARROW_DOWN" if (i // 10) % 2 == 0 else "/cuia/ARROW_UP")
    i += 1
    time.sleep(0.2)
t = time.time() - t0
print("%d arrow presses in %.1f s" % (i, t))
for fb, s, fr in panels:
    b = int(open(s).read()) - b0[fb]
    print("%s: %.1f kB/s, %.2f full frames/s" % (fb, b / t / 1e3, b / fr / t))
for n, ds in sorted(p.items()):
    print("%s: %.1f %% CPU" % (n, 100.0 * (cpu(ds) - c0[n]) / hz / t))
PY
		;;
	*) usage 1 ;;
esac
