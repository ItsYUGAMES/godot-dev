#!/usr/bin/env bash
# SessionStart hook: silent outside Godot projects; inside one, installs/enables the
# pinned godot-ai add-on when absent and prints <=3 lines of context.
set -u
DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$DIR/lib.sh"

find_godot_root >/dev/null || exit 0
if ! pick_python; then
	echo "Godot project detected (godot-dev plugin). Load the \`godot\` skill before any Godot work."
	echo "godot-ai: skipped — needs Python 3.9+ or uv (https://docs.astral.sh/uv/)."
	exit 0
fi
"${PY[@]}" "$DIR/godot_dev.py" session-start
exit 0
