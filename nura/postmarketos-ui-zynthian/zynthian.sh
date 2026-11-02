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

CAGE_UI_COMMAND=zynthian
