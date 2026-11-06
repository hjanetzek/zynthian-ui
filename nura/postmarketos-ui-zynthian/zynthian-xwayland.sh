# Sourced by tinydm before it starts the session (cage): XWayland without glamor on Panfrost GPUs,
# where glamor leaves regions undrawn (black rectangles in zynthian's Tk widgets, see
# docs/nura-display.md in zynthian-ui). Rotation and presentation stay on the GPU in cage.
# Applies to every Wayland session; an XWayland client using OpenGL renders in software then.
# Keeps a WLR_XWAYLAND set before; files in /etc/tinydm.d/env-wayland.d/ (sourced later) override.
if [ -z "${WLR_XWAYLAND:-}" ] && ls -d /sys/bus/platform/drivers/panfrost/*.gpu >/dev/null 2>&1; then
	export WLR_XWAYLAND=/usr/libexec/zynthian/xwayland-noglamor
fi
