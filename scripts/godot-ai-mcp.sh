#!/usr/bin/env bash
# MCP entry for godot-ai. Outside a Godot project it is a zero-tool stub, so the
# plugin costs nothing in other workspaces; inside one, godot_dev.py execs the bridge.
set -u
DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$DIR/lib.sh"
set_host "${1:-}"

if ! find_godot_root >/dev/null || ! pick_python; then
	mcp_stub
	exit 0
fi
exec "${PY[@]}" "$DIR/godot_dev.py" mcp
