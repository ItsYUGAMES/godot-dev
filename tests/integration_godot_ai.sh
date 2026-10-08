#!/usr/bin/env bash
# End-to-end: hook auto-installs godot-ai into a fresh 4.7 project, a headless editor loads it,
# and the plugin's MCP launcher attaches and answers editor_state.
# Isolated: temp HOME (own editor settings, capability dir), temp runtime dir, ports 18000/19500,
# so a godot-ai backend already running on 8000/9500 is not touched. Needs network (uvx/PyPI)
# unless the uv cache is warm.
# Usage: bash tests/integration_godot_ai.sh RELEASE_DIR [GODOT_BIN]
set -u
PLUGIN=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
RELEASE=${1:?usage: integration_godot_ai.sh RELEASE_DIR [GODOT_BIN]}
GODOT=${2:-${GODOT:-/Applications/Godot.app/Contents/MacOS/Godot}}
REAL_HOME=$HOME
# godot-ai refuses capability dirs with group/world-writable ancestors (e.g. /tmp), so the
# isolated HOME lives under the real home by default.
mkdir -p "${GODOT_DEV_E2E_DIR:-$HOME/.cache}"
WORK=$(mktemp -d "${GODOT_DEV_E2E_DIR:-$HOME/.cache}/godot-dev-e2e.XXXXXX")
EDITOR_PID=""
cleanup() {
	[ -n "$EDITOR_PID" ] && kill "$EDITOR_PID" 2>/dev/null
	pkill -f -- "--port 18000 --ws-port 19500" 2>/dev/null
	rm -rf "$WORK"
}
trap cleanup EXIT

export HOME="$WORK/home" GODOT_AI_RUNTIME_DIR="$WORK/runtime" GODOT_AI_DISABLE_TELEMETRY=true
mkdir -p "$HOME/.cache" "$HOME/.local/share" "$GODOT_AI_RUNTIME_DIR"
chmod 700 "$GODOT_AI_RUNTIME_DIR"
# Reuse the real uv binaries, caches and managed Pythons (safe for concurrent use).
ln -s "$REAL_HOME/.local/bin" "$HOME/.local/bin"
[ -d "$REAL_HOME/.cache/uv" ] && ln -s "$REAL_HOME/.cache/uv" "$HOME/.cache/uv"
[ -d "$REAL_HOME/.local/share/uv" ] && ln -s "$REAL_HOME/.local/share/uv" "$HOME/.local/share/uv"
SETTINGS="$HOME/Library/Application Support/Godot"
mkdir -p "$SETTINGS"
printf '[gd_resource type="EditorSettings" format=3]\n\n[resource]\ngodot_ai/http_port = 18000\ngodot_ai/ws_port = 19500\ngodot_ai/telemetry_enabled = false\n' \
	> "$SETTINGS/editor_settings-4.7.tres"

P="$WORK/game"
mkdir -p "$P"
printf 'config_version=5\n\n[application]\n\nconfig/name="E2E"\nconfig/features=PackedStringArray("4.7")\n' > "$P/project.godot"
export CLAUDE_CONFIG_DIR="$WORK/claude" CLAUDE_PLUGIN_DATA="$WORK/data" CLAUDE_PROJECT_DIR="$P"
mkdir -p "$CLAUDE_CONFIG_DIR" "$CLAUDE_PLUGIN_DATA"

echo "== hook"
(cd "$P" && GODOT_DEV_RELEASE_BASE_URL="file://$RELEASE" bash "$PLUGIN/scripts/session-start.sh")
[ -f "$P/addons/godot_ai/plugin.cfg" ] || { echo "FAIL: add-on not installed"; exit 1; }

ORDER=${ORDER:-editor-first}
RECORD="$HOME/Library/Application Support/godot-ai/capabilities/http-18000.json"
wait_record() {
	for _ in $(seq 1 240); do
		[ -f "$RECORD" ] && lsof -nP -iTCP:18000 -sTCP:LISTEN >/dev/null 2>&1 && return 0
		sleep 1
	done
	return 1
}
start_editor() {
	"$GODOT" --headless --path "$P" --import >"$WORK/import.log" 2>&1
	GODOT_AI_ALLOW_HEADLESS=1 "$GODOT" --headless --editor --path "$P" >"$WORK/editor.log" 2>&1 &
	EDITOR_PID=$!
}
PROBE=(python3 -I "$PLUGIN/tests/mcp_probe.py" editor_state 300 -- bash "$PLUGIN/scripts/godot-ai-mcp.sh")

echo "== order: $ORDER"
if [ "$ORDER" = editor-first ]; then
	start_editor
	wait_record || { echo "FAIL: editor-owned backend never published its record"; tail -30 "$WORK/editor.log"; exit 1; }
	echo "editor backend up on 18000; attaching"
	"${PROBE[@]}" && { echo "RESULT: PASS"; exit 0; }
else
	"${PROBE[@]}" >"$WORK/probe.out" &
	PROBE_PID=$!
	wait_record || { echo "FAIL: bridge-spawned backend never came up"; exit 1; }
	echo "bridge backend up on 18000; opening editor"
	start_editor
	wait "$PROBE_PID"; code=$?
	cat "$WORK/probe.out"
	[ "$code" -eq 0 ] && { echo "RESULT: PASS"; exit 0; }
fi
echo "--- editor log tail"; tail -30 "$WORK/editor.log"
echo "--- runtime dir"; ls -la "$GODOT_AI_RUNTIME_DIR"; tail -20 "$GODOT_AI_RUNTIME_DIR"/*.log 2>/dev/null
echo "RESULT: FAIL"
exit 1
