# Sourced by /usr/share/cage-ui/cage-ui-session.sh: run zynthian full-screen in cage.
# The session runs with "set -eu -o pipefail" (from cage-ui-autorotate.sh): never fail here.

# zynthian connects to JACK (PipeWire's pipewire-jack) once, at start-up. During login PipeWire is
# only socket-activated and WirePlumber has not set up a sink yet, so wait (up to 10 s) until
# there is a default sink, or zynthian's audio outputs have nothing to connect to.
zynthian_wait_for_audio() {
	i=0
	while [ "$i" -lt 100 ]; do
		wpctl inspect @DEFAULT_AUDIO_SINK@ >/dev/null 2>&1 && return 0
		sleep 0.1
		i=$((i + 1))
	done
	return 1
}
zynthian_wait_for_audio || true

# JACK period: ZynthianOS runs jackd with 256 frames. PipeWire picks the quantum from what its
# clients ask for; force 256 (5.3 ms at 48 kHz) for the whole graph, fine for a kiosk. The
# real-time limit comes from tinydm.service.d/50-zynthian-realtime.conf.
pw-metadata -n settings 0 clock.force-quantum 256 >/dev/null 2>&1 || true
export PIPEWIRE_LATENCY=256/48000

# Use the whole output, whatever window size the user's config has (desktop default 1024x600),
# and scale the UI with it: XWayland reports 96 dpi whatever the panel, so the configured font
# size (made for 1024x600) would be tiny on a high-resolution panel (1920x1200 on the Duet).
# Override in ~/.config/zynthian/zynthian_custom_config.sh, e.g. ZYNTHIAN_UI_SCALE=1.5.
export ZYNTHIAN_FULLSCREEN=1
export ZYNTHIAN_UI_SCALE=auto

# Qt Quick UI (ZYNTHIAN_UI=qt in ~/.config/zynthian/zynthian_custom_config.sh): a native Wayland
# client in cage, no XWayland. cage rotates the panel (cage-ui-autorotate.sh) but leaves the
# output scale at 1; the output scale is set below.
export QT_QPA_PLATFORM=wayland
export QT_WAYLAND_DISABLE_WINDOWDECORATION=1

# Device defaults (first device-tree compatible), overridden by /etc/default/zynthian: the output
# rotation for panels that report no DRM panel orientation (cage-ui-autorotate.sh rotates the
# others), and the Qt UI's output scale
zynthian_transform=
zynthian_scale=1.5
case "$(tr '\0' '\n' < /proc/device-tree/compatible 2>/dev/null | head -n 1)" in
	google,blueline)
		# Pixel 3: portrait panel (1080x2160) without panel orientation; landscape, and at 443 ppi
		# a larger scale than the Duet's (224 ppi): 1200x600 logical pixels
		zynthian_transform=90
		zynthian_scale=1.8
		;;
esac

# UI (qt or tk) from /etc/default/zynthian, switched by kiosk-session; zynthian's own config
# (~/.config/zynthian/zynthian_custom_config.sh) can still override it
ZYNTHIAN_UI=qt
[ -f /etc/default/zynthian ] && . /etc/default/zynthian
export ZYNTHIAN_UI

zynthian_set_output() {
	wlr-randr --json | jq -r '.[] | select(.enabled) | .name' |
	while read -r output; do
		wlr-randr --output "$output" "$@"
	done
}

# Output rotation (ZYNTHIAN_OUTPUT_TRANSFORM in /etc/default/zynthian: normal, 90, 180, 270, ...;
# default per device, above), for both UIs
if [ -n "${ZYNTHIAN_OUTPUT_TRANSFORM-$zynthian_transform}" ]; then
	zynthian_set_output --transform "${ZYNTHIAN_OUTPUT_TRANSFORM-$zynthian_transform}" || true
fi

# Output scale for the Qt UI (ZYNTHIAN_OUTPUT_SCALE in /etc/default/zynthian; default 1.5, per
# device above): the Duet's 1920x1200 at 1.5 gives 1280x800 logical pixels (2: 960x600, larger);
# Qt renders at the panel's resolution. The Tk UI stays at scale 1: XWayland's buffer would be
# scaled up (blurry), and it scales its fonts itself (ZYNTHIAN_UI_SCALE).
if [ "$ZYNTHIAN_UI" = qt ] && [ -n "${ZYNTHIAN_OUTPUT_SCALE-$zynthian_scale}" ]; then
	zynthian_set_output --scale "${ZYNTHIAN_OUTPUT_SCALE-$zynthian_scale}" || true
fi

CAGE_UI_COMMAND=zynthian
