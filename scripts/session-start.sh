#!/usr/bin/env bash
# SessionStart hook: silent outside Godot projects; inside one, installs/enables the
# pinned godot-ai add-on when absent and prints <=3 lines of context, shaped for the host
# named in $1 (see set_host in lib.sh).
set -u
DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$DIR/lib.sh"
set_host "${1:-}"

find_godot_root >/dev/null || exit 0
if ! pick_python; then
	emit_context "Godot project detected (godot-dev plugin). Load the \`godot\` skill before any Godot work." \
		"godot-ai: skipped — needs Python 3.9+ or uv (https://docs.astral.sh/uv/)."
	exit 0
fi
"${PY[@]}" "$DIR/godot_dev.py" session-start
exit 0
