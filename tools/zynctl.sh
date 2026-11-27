#!/bin/sh
# Drive a zynthian UI over its websocket (CUIAs, screen state as text) with the zynthian-operator
# skill's client, without installing websocket-client: uv caches it once for every worktree.
#
# Usage: tools/zynctl.sh [--host HOST] [--port PORT] [--settle MS] [--full] [STEP...]
#   e.g. tools/zynctl.sh --host localhost --port 8390 chains   (compare VM 2242's websocket)
#        tools/zynctl.sh --host kick-duet.local "CUIA BACK"
# Steps and options: .claude/skills/zynthian-operator/SKILL.md, or tools/zynctl.sh -h.
here=$(cd "$(dirname "$0")" && pwd)
exec uv run -q --no-project --with websocket-client python3 \
	"$here/../.claude/skills/zynthian-operator/scripts/zynctl.py" "$@"
