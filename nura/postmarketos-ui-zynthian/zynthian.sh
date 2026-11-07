# Sourced by /usr/share/cage-ui/cage-ui-session.sh: run zynthian full-screen in cage.
# The session runs with "set -eu -o pipefail" (from cage-ui-autorotate.sh): never fail here.

. /usr/libexec/zynthian/zynthian-session.sh
zynthian_device_defaults
zynthian_session_env

zynthian_set_output() {
	wlr-randr --json | jq -r '.[] | select(.enabled) | .name' |
	while read -r output; do
		wlr-randr --output "$output" "$@"
	done
}

# Output rotation (ZYNTHIAN_OUTPUT_TRANSFORM in /etc/default/zynthian: normal, 90, 180, 270, ...;
# default per device, zynthian-session.sh), for both UIs
if [ -n "$zynthian_output_transform" ]; then
	zynthian_set_output --transform "$zynthian_output_transform" || true
fi

# Output scale for the Qt UI (ZYNTHIAN_OUTPUT_SCALE in /etc/default/zynthian; default 1.5, per
# device, zynthian-session.sh): the Duet's 1920x1200 at 1.5 gives 1280x800 logical pixels (2:
# 960x600, larger); Qt renders at the panel's resolution. The Tk UI stays at scale 1: XWayland's buffer would be
# scaled up (blurry), and it scales its fonts itself (ZYNTHIAN_UI_SCALE).
if [ "$ZYNTHIAN_UI" = qt ] && [ -n "$zynthian_output_scale" ]; then
	zynthian_set_output --scale "$zynthian_output_scale" || true
fi

CAGE_UI_COMMAND=zynthian
