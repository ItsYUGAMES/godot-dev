#!/usr/bin/env bash
# Offline tests for the SessionStart hook, add-on installer and MCP launcher.
# Usage: bash tests/run_tests.sh RELEASE_DIR
#   RELEASE_DIR holds the three pinned godot-ai v4.3.0 release assets (downloaded once), so the
#   tests never hit the network; the pinned SHA-256 values are still enforced.
set -u
PLUGIN=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
RELEASE=${1:?usage: run_tests.sh RELEASE_DIR}
WORK=$(mktemp -d "${TMPDIR:-/tmp}/godot-dev-tests.XXXXXX")
trap 'rm -rf "$WORK"' EXIT
PASS=0 FAIL=0

ok() { PASS=$((PASS + 1)); printf 'ok   %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); printf 'FAIL %s\n' "$1"; [ -n "${2:-}" ] && printf '     %s\n' "$2"; }
check() { if eval "$2"; then ok "$1"; else bad "$1" "${3:-}"; fi; }

# Isolated environment: no real Claude config, plugin data in WORK, prewarm marked done.
export CLAUDE_CONFIG_DIR="$WORK/claude" CLAUDE_PLUGIN_DATA="$WORK/data" CODEX_HOME="$WORK/codex"
mkdir -p "$CLAUDE_CONFIG_DIR" "$CLAUDE_PLUGIN_DATA" "$CODEX_HOME"
touch "$CLAUDE_PLUGIN_DATA/prewarmed-4.3.0" "$CLAUDE_PLUGIN_DATA/prewarmed-4.2.3"
export GODOT_DEV_RELEASE_BASE_URL="file://$RELEASE"
unset GODOT_DEV_AUTO_INSTALL GODOT_DEV_MCP GODOT_DEV_MCP_FORCE GODOT_DEV_TELEMETRY GODOT_DEV_MCP_PORT

new_project() { # dir config_version features
	mkdir -p "$1"
	printf '; Engine configuration file.\nconfig_version=%s\n\n[application]\n\nconfig/name="T"\nconfig/features=PackedStringArray(%s)\n' "$2" "$3" > "$1/project.godot"
}
# Context text of a SessionStart hook's stdout, whatever host shape it uses (plain or JSON).
ctx() { python3 -I -c '
import json, sys
raw = sys.stdin.read()
try:
    d = json.loads(raw)
except ValueError:
    sys.stdout.write(raw); sys.exit()
print(d.get("additional_context") or d.get("additionalContext") or d["hookSpecificOutput"]["additionalContext"])'; }
hook() { (cd "$1" && CLAUDE_PROJECT_DIR="$1" bash "$PLUGIN/scripts/session-start.sh") | ctx; }
plan() { (cd "$1" && CLAUDE_PROJECT_DIR="$1" GODOT_DEV_MCP_DRY_RUN=1 bash "$PLUGIN/scripts/godot-ai-mcp.sh"); }
field() { python3 -I -c "import json,sys; d=json.loads(sys.argv[1]); print(eval(sys.argv[2]))" "$1" "$2"; }

# 1. Non-Godot directory: hook silent, MCP is a zero-tool stub.
mkdir -p "$WORK/plain"
out=$(hook "$WORK/plain")
check "non-Godot: hook prints nothing" '[ -z "$out" ]' "$out"
stub=$(cd "$WORK/plain" && printf '%s\n' \
	'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}' \
	'{"jsonrpc":"2.0","method":"notifications/initialized"}' \
	'{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
	'{"jsonrpc":"2.0","id":"x3","method":"ping"}' | CLAUDE_PROJECT_DIR="$WORK/plain" bash "$PLUGIN/scripts/godot-ai-mcp.sh")
check "non-Godot: stub answers 3 requests with valid JSON" \
	'[ "$(printf "%s\n" "$stub" | python3 -I -c "import json,sys; print(sum(1 for l in sys.stdin if \"result\" in json.loads(l)))")" = 3 ]' "$stub"
check "non-Godot: stub sends no instructions and no tools" \
	'! printf "%s" "$stub" | grep -q instructions && printf "%s" "$stub" | grep -q "\"tools\":\[\]"'

# 2. Fresh Godot 4.7 project: install + enable, then idempotent.
P="$WORK/game"; new_project "$P" 5 '"4.7", "Forward Plus"'
printf '\n[editor_plugins]\n\nenabled=PackedStringArray("res://addons/other/plugin.cfg")\n' >> "$P/project.godot"
out=$(hook "$P")
check "fresh: hook reports verified install" 'printf "%s" "$out" | grep -q "installed v4.3.0 (signature + hashes verified)"' "$out"
check "fresh: add-on files present" '[ -f "$P/addons/godot_ai/plugin.cfg" ] && grep -q "version=\"4.3.0\"" "$P/addons/godot_ai/plugin.cfg"'
check "fresh: plugin enabled, existing plugin kept" \
	'grep -q "enabled=PackedStringArray(\"res://addons/other/plugin.cfg\", \"res://addons/godot_ai/plugin.cfg\")" "$P/project.godot"' "$(grep enabled "$P/project.godot")"
check "fresh: no staging leftovers" '[ -z "$(ls -A "$P/addons" | grep staging)" ]'
check "fresh: hook output is at most 3 lines" '[ "$(printf "%s\n" "$out" | wc -l | tr -d " ")" -le 3 ]' "$out"
sum1=$(shasum "$P/project.godot")
out2=$(hook "$P")
check "rerun: add-on left untouched" 'printf "%s" "$out2" | grep -q "v4.3.0 present (left untouched)"' "$out2"
check "rerun: project.godot unchanged" '[ "$sum1" = "$(shasum "$P/project.godot")" ]'

# 3. Bridge plan: active with pinned version, ports, telemetry off.
pl=$(plan "$P")
check "plan: active" '[ "$(field "$pl" "d[\"active\"]")" = True ]' "$pl"
check "plan: pins add-on version, ports, disables telemetry" \
	'printf "%s" "$pl" | grep -q "godot-ai==4.3.0" && printf "%s" "$pl" | grep -q "\"--ws-port\"" && printf "%s" "$pl" | grep -q "\"--disable-telemetry\""' "$pl"
pl=$(cd "$P" && CLAUDE_PROJECT_DIR="$P" GODOT_DEV_MCP_DRY_RUN=1 GODOT_DEV_MCP_PORT=18000 GODOT_DEV_TELEMETRY=1 bash "$PLUGIN/scripts/godot-ai-mcp.sh")
check "plan: env overrides port and telemetry" \
	'printf "%s" "$pl" | grep -q "\"18000\"" && ! printf "%s" "$pl" | grep -q disable-telemetry' "$pl"
pl=$(cd "$P" && CLAUDE_PROJECT_DIR="$P" GODOT_DEV_MCP_DRY_RUN=1 GODOT_DEV_MCP=0 bash "$PLUGIN/scripts/godot-ai-mcp.sh")
check "plan: GODOT_DEV_MCP=0 keeps it inactive" '[ "$(field "$pl" "d[\"active\"]")" = False ]' "$pl"

# 4. Existing user-scope godot-ai entry: dedupe + pin mismatch warning; FORCE overrides.
printf '{"mcpServers":{"godot-ai":{"type":"stdio","command":"uvx","args":["--from","godot-ai==4.2.3","godot-ai","attach"]}}}' > "$CLAUDE_CONFIG_DIR/.claude.json"
pl=$(plan "$P")
check "dedupe: bundled server inactive when user entry exists" \
	'[ "$(field "$pl" "d[\"active\"]")" = False ] && printf "%s" "$pl" | grep -q "user scope"' "$pl"
out=$(hook "$P")
check "dedupe: hook warns about pin mismatch" 'printf "%s" "$out" | grep -q "godot-ai==4.2.3 differs from add-on v4.3.0"' "$out"
pl=$(cd "$P" && CLAUDE_PROJECT_DIR="$P" GODOT_DEV_MCP_DRY_RUN=1 GODOT_DEV_MCP_FORCE=1 bash "$PLUGIN/scripts/godot-ai-mcp.sh")
check "dedupe: GODOT_DEV_MCP_FORCE=1 activates anyway" '[ "$(field "$pl" "d[\"active\"]")" = True ]' "$pl"
rm "$CLAUDE_CONFIG_DIR/.claude.json"
printf '{"mcpServers":{"godot-ai":{"command":"x"}}}' > "$P/.mcp.json"
pl=$(plan "$P")
check "dedupe: project .mcp.json entry detected" 'printf "%s" "$pl" | grep -q "project scope"' "$pl"
rm "$P/.mcp.json"

# 4b. Codex host: dedupe reads Codex config.toml instead of ~/.claude.json.
codex_plan() { (cd "$1" && GODOT_DEV_MCP_DRY_RUN=1 bash "$PLUGIN/scripts/godot-ai-mcp.sh" codex); }
pl=$(codex_plan "$P")
check "codex: active without a Codex godot-ai entry" '[ "$(field "$pl" "d[\"active\"]")" = True ]' "$pl"
printf '[mcp_servers.godot-ai]\ncommand = "uvx"\nargs = ["-c", "run(sys.argv[1:])", \047C:/Users/u/uvx.exe\047, "--from", "godot-ai==4.2.3", "godot-ai", "attach"]\n\n[mcp_servers.godot-ai.env]\nX = "1"\n' > "$CODEX_HOME/config.toml"
pl=$(codex_plan "$P")
check "codex: inactive when config.toml has godot-ai" \
	'[ "$(field "$pl" "d[\"active\"]")" = False ] && printf "%s" "$pl" | grep -q "user scope"' "$pl"
check "codex: reads the pin from config.toml" '[ "$(field "$pl" "d[\"other_pin\"]")" = 4.2.3 ]' "$pl"
pl=$(plan "$P")
check "claude: ignores Codex config.toml" '[ "$(field "$pl" "d[\"active\"]")" = True ]' "$pl"
out=$(cd "$P" && bash "$PLUGIN/scripts/session-start.sh" codex)
check "codex: hook warns about pin mismatch" 'printf "%s" "$out" | grep -q "godot-ai==4.2.3 differs from add-on v4.3.0"' "$out"
# The .codex-mcp.json command as Codex runs it: no ${} expansion, cwd = session dir.
mkdir -p "$CODEX_HOME/plugins/cache/m/godot-dev/0.0.0"; cp -R "$PLUGIN/scripts" "$CODEX_HOME/plugins/cache/m/godot-dev/0.0.0/"
cmd=$(python3 -I -c "import json,sys; print(json.load(open(sys.argv[1]))['mcpServers']['godot-ai']['args'][1])" "$PLUGIN/.codex-mcp.json")
pl=$(cd "$P" && GODOT_DEV_MCP_DRY_RUN=1 bash -c "$cmd")
check "codex: .codex-mcp.json finds the launcher and passes the host" \
	'[ "$(field "$pl" "d[\"active\"]")" = False ] && printf "%s" "$pl" | grep -q "user scope"' "$pl"
rm "$CODEX_HOME/config.toml"
mkdir -p "$P/.codex"; printf '[mcp_servers."godot-ai"]\ncommand = "x"\n' > "$P/.codex/config.toml"
pl=$(codex_plan "$P")
check "codex: project .codex/config.toml entry detected" 'printf "%s" "$pl" | grep -q "project scope"' "$pl"
rm -r "$P/.codex"

# 4c. Hook output shape per host.
shape() { (cd "$1" && bash "$PLUGIN/scripts/session-start.sh" ${2:+"$2"}); }
o=$(shape "$P" cursor)
check "shape: cursor additional_context" 'field "$o" "d[\"additional_context\"]" | grep -q "Godot 4.7 project detected"' "$o"
o=$(shape "$P" copilot)
check "shape: copilot additionalContext" 'field "$o" "d[\"additionalContext\"]" | grep -q "Godot 4.7 project detected"' "$o"
for h in gemini "" bogus; do
	o=$(shape "$P" "$h")
	check "shape: ${h:-claude} hookSpecificOutput" \
		'[ "$(field "$o" "d[\"hookSpecificOutput\"][\"hookEventName\"]")" = SessionStart ] && field "$o" "d[\"hookSpecificOutput\"][\"additionalContext\"]" | grep -q "Godot 4.7 project detected"' "$o"
done
o=$(shape "$P" codex)
check "shape: codex plain text" '[ "${o%%(*}" = "Godot 4.7 project detected " ]' "$o"
printf '{"mcpServers":{"godot-ai":{"command":"x","args":["godot-ai==4.2.3"]}}}' > "$CLAUDE_CONFIG_DIR/.claude.json"
o=$(cd "$P" && CLAUDE_PLUGIN_ROOT="$PLUGIN" bash "$PLUGIN/scripts/session-start.sh" gemini | ctx)
check "shape: gemini arg under Claude reads Claude config" 'printf "%s" "$o" | grep -q "existing godot-ai entry (user scope)"' "$o"
rm "$CLAUDE_CONFIG_DIR/.claude.json"
for h in claude codex cursor copilot gemini; do
	o=$(shape "$WORK/plain" "$h")
	check "shape: $h silent outside Godot" '[ -z "$o" ]' "$o"
done
if [ -e /opt/homebrew/bin/uv ] || [ -e /usr/local/bin/uv ]; then
	printf 'skip shape: no-Python JSON (uv in a fixed system path)\n'
else
	mkdir -p "$WORK/empty"
	o=$(cd "$P" && dirname() { local d="${1%/*}"; [ "$d" = "$1" ] && d=.; printf '%s\n' "${d:-/}"; } \
		&& export -f dirname && PATH="$WORK/empty" HOME="$WORK/empty" "$BASH" "$PLUGIN/scripts/session-start.sh" cursor)
	check "shape: no-Python message is cursor JSON" 'field "$o" "d[\"additional_context\"]" | grep -q "needs Python 3.9+ or uv"' "$o"
fi

# 5. Opt-out, Godot 3 and 4.6 projects are not touched.
Q="$WORK/optout"; new_project "$Q" 5 '"4.7"'
out=$(cd "$Q" && CLAUDE_PROJECT_DIR="$Q" GODOT_DEV_AUTO_INSTALL=0 bash "$PLUGIN/scripts/session-start.sh" | ctx)
check "opt-out: nothing installed" '[ ! -e "$Q/addons/godot_ai" ] && printf "%s" "$out" | grep -q "auto-install disabled"' "$out"
G3="$WORK/godot3"; new_project "$G3" 4 '"3.5"'
out=$(hook "$G3")
check "Godot 3 project: detected, untouched" '[ ! -e "$G3/addons" ] && printf "%s" "$out" | grep -q "Godot 3 project"' "$out"
G46="$WORK/godot46"; new_project "$G46" 5 '"4.6"'
out=$(hook "$G46")
check "Godot 4.6 project: skipped (needs 4.7+)" '[ ! -e "$G46/addons/godot_ai" ] && printf "%s" "$out" | grep -q "needs Godot 4.7+"' "$out"

# 6. Tampered download is rejected and leaves nothing behind.
BADREL="$WORK/badrel"; mkdir -p "$BADREL"; cp "$RELEASE"/* "$BADREL/"
printf 'x' >> "$BADREL/godot-ai-v4-plugin.zip"
T="$WORK/tampered"; new_project "$T" 5 '"4.7"'
out=$(cd "$T" && CLAUDE_PROJECT_DIR="$T" GODOT_DEV_RELEASE_BASE_URL="file://$BADREL" bash "$PLUGIN/scripts/session-start.sh" | ctx)
check "tampered: install refused" 'printf "%s" "$out" | grep -q "install failed" && [ ! -e "$T/addons/godot_ai" ]' "$out"
check "tampered: project.godot not modified" '! grep -q godot_ai "$T/project.godot"'
check "tampered: no staging leftovers" '[ -z "$(ls -A "$T/addons" 2>/dev/null | grep staging)" ]'

# 7. Existing add-on of another version is left alone and pinned.
O="$WORK/older"; new_project "$O" 5 '"4.7"'
mkdir -p "$O/addons/godot_ai"; printf '[plugin]\n\nname="Godot AI"\nversion="4.2.3"\nscript="plugin.gd"\n' > "$O/addons/godot_ai/plugin.cfg"
out=$(hook "$O")
check "older add-on: untouched" 'grep -q "4.2.3" "$O/addons/godot_ai/plugin.cfg" && printf "%s" "$out" | grep -q "v4.2.3 present"' "$out"
pl=$(plan "$O")
check "older add-on: launcher pins godot-ai==4.2.3" 'printf "%s" "$pl" | grep -q "godot-ai==4.2.3"' "$pl"

# 8. Subdirectory of a Godot project resolves the root.
mkdir -p "$P/scripts/deep"
out=$(hook "$P/scripts/deep")
check "subdirectory: root found from nested dir" 'printf "%s" "$out" | grep -q "Godot 4.7 project detected"' "$out"

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
