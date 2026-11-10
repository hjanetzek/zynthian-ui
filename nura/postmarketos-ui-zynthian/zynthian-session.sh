# Shared by zynthian's sessions (sourced; /etc/cage-ui/zynthian.sh for cage, zynthian-niri for niri).
# Sourced from scripts running with "set -eu": never fail here.

# Device defaults (first device-tree compatible), overridden by /etc/default/zynthian: the output
# rotation for panels that report no DRM panel orientation (the compositors rotate the others
# themselves: cage-ui-autorotate.sh, niri), and the Qt UI's output scale. Then the UI (qt or tk)
# from /etc/default/zynthian, switched by kiosk-session; zynthian's own config
# (~/.config/zynthian/zynthian_custom_config.sh) can still override it.
zynthian_device_defaults() {
	zynthian_transform=
	zynthian_scale=1.5
	zynthian_mode=
	case "$(tr '\0' '\n' < /proc/device-tree/compatible 2>/dev/null | head -n 1)" in
		google,blueline)
			# Pixel 3: portrait panel (1080x2160) without panel orientation; landscape, and at 443 ppi
			# a larger scale than the Duet's (224 ppi): 1200x600 logical pixels
			zynthian_transform=90
			zynthian_scale=1.8
			;;
		raspberrypi,*)
			# zynthian kits: small panels (the V4's 480x320 SPI panel, the V5's 800x480 DSI
			# panel) at their own resolution, as on ZynthianOS
			zynthian_scale=1
			;;
	esac
	# A virtual machine (nura-builds' qemu-amd64 image, nura/tools/run_qemu.sh): a window on a desktop
	# screen, no device tree; scale 1 (the default window, 1280x800, then shows the Duet's layout)
	# and the screen size run_qemu.sh's -R asked for (its SMBIOS SKU "nura-screen=WxH"): QEMU's GTK
	# window otherwise reports its first size, the firmware's 640x480, as the preferred mode
	case "$(cat /sys/class/dmi/id/sys_vendor 2>/dev/null)" in
		QEMU*)
			zynthian_scale=1
			case "$(cat /sys/class/dmi/id/product_sku 2>/dev/null)" in
				nura-screen=*x*) zynthian_mode=$(sed -n 's/^nura-screen=\([0-9]*x[0-9]*\)$/\1/p' /sys/class/dmi/id/product_sku) ;;
			esac
			;;
	esac
	ZYNTHIAN_UI=qt
	[ -f /etc/default/zynthian ] && . /etc/default/zynthian
	# Upstream zynthian-ui (zynthian-ui-vangelis, -tomita from nura-builds) has no Qt UI
	[ -f /usr/share/zynthian/zynthian-ui/zynthian_qt_main.py ] || ZYNTHIAN_UI=tk
	export ZYNTHIAN_UI
	# shellcheck disable=SC2034 # used by the sourcing scripts
	zynthian_output_transform=${ZYNTHIAN_OUTPUT_TRANSFORM-$zynthian_transform}
	# shellcheck disable=SC2034
	zynthian_output_scale=${ZYNTHIAN_OUTPUT_SCALE-$zynthian_scale}
	# shellcheck disable=SC2034
	zynthian_output_mode=${ZYNTHIAN_OUTPUT_MODE-$zynthian_mode}
}

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

# Audio and the environment zynthian runs in
zynthian_session_env() {
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

	# Qt Quick UI: a native Wayland client, no XWayland
	export QT_QPA_PLATFORM=wayland
	export QT_WAYLAND_DISABLE_WINDOWDECORATION=1
}
