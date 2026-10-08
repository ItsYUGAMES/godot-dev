# Shared helpers for godot-dev entry scripts (bash 3.2+). Source, don't execute.

# Print the nearest directory containing project.godot, walking up from the project dir.
find_godot_root() {
	local dir
	dir=$(cd "${CLAUDE_PROJECT_DIR:-$PWD}" 2>/dev/null && pwd -P) || return 1
	while :; do
		if [ -f "$dir/project.godot" ]; then
			printf '%s\n' "$dir"
			return 0
		fi
		[ "$dir" = "/" ] && return 1
		dir=$(dirname "$dir")
	done
}

# Fill the PY array with a Python 3.9+ command; prefer an existing interpreter over uv.
pick_python() {
	local cand path uv
	for cand in python3.13 python3.12 python3.11 python3.10 python3; do
		path=$(command -v "$cand" 2>/dev/null) || continue
		# Without Command Line Tools, macOS /usr/bin/python3 only pops an installer dialog.
		if [ "$path" = /usr/bin/python3 ] && [ "$(uname -s)" = Darwin ] && ! xcode-select -p >/dev/null 2>&1; then
			continue
		fi
		if "$path" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
			PY=("$path" -I)
			return 0
		fi
	done
	for uv in "$(command -v uv 2>/dev/null)" "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv; do
		if [ -n "$uv" ] && [ -x "$uv" ]; then
			PY=("$uv" run --no-project --quiet --python ">=3.11" python -I)
			return 0
		fi
	done
	return 1
}

# Zero-tool MCP server: answers initialize/tools/list/ping, sends no instructions.
mcp_stub() {
	local line id method proto
	while IFS= read -r line || [ -n "$line" ]; do
		id="" method="" proto="2025-06-18"
		[[ $line =~ \"id\"[[:space:]]*:[[:space:]]*([0-9]+|\"[^\"]*\") ]] && id="${BASH_REMATCH[1]}"
		[[ $line =~ \"method\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] && method="${BASH_REMATCH[1]}"
		[[ $line =~ \"protocolVersion\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] && proto="${BASH_REMATCH[1]}"
		[ -z "$id" ] && continue
		case "$method" in
		initialize)
			printf '{"jsonrpc":"2.0","id":%s,"result":{"protocolVersion":"%s","capabilities":{},"serverInfo":{"name":"godot-ai-inactive","version":"0"}}}\n' "$id" "$proto" ;;
		tools/list)
			printf '{"jsonrpc":"2.0","id":%s,"result":{"tools":[]}}\n' "$id" ;;
		ping)
			printf '{"jsonrpc":"2.0","id":%s,"result":{}}\n' "$id" ;;
		*)
			printf '{"jsonrpc":"2.0","id":%s,"error":{"code":-32601,"message":"godot-ai bundled server inactive"}}\n' "$id" ;;
		esac
	done
}
