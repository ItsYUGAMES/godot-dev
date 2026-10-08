#!/usr/bin/env bash
# Tests for gd.py hygiene and gd.py release against a throwaway git repo + Godot 4.7.
# Usage: bash tests/gd_tests.sh [GODOT_BIN]
set -u
PLUGIN=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
GD=(python3 -I "$PLUGIN/skills/godot/scripts/gd.py")
[ -n "${1:-}" ] && GD+=(--godot "$1")
WORK=$(mktemp -d "${TMPDIR:-/tmp}/gd-tests.XXXXXX")
trap 'rm -rf "$WORK"' EXIT
PASS=0 FAIL=0
ok() { PASS=$((PASS + 1)); printf 'ok   %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); printf 'FAIL %s\n' "$1"; [ -n "${2:-}" ] && printf '%s\n' "$2" | sed 's/^/     /'; }
check() { if eval "$2"; then ok "$1"; else bad "$1" "${3:-}"; fi; }

P="$WORK/game"
mkdir -p "$P/game" "$P/tests"
cd "$P" || exit 1
git init -q . && git config user.email t@t && git config user.name t
printf '.godot/\n' > .gitignore
printf 'config_version=5\n\n[application]\n\nconfig/name="G"\nconfig/features=PackedStringArray("4.7")\nrun/main_scene="res://game/main.tscn"\n' > project.godot
printf 'extends Node\n\nvar items: Array[int] = [1, 2]\n\n\nfunc _ready() -> void:\n\tpass\n' > game/main.gd
printf '[gd_scene format=3]\n\n[ext_resource type="Script" path="res://game/main.gd" id="1"]\n\n[node name="Main" type="Node"]\nscript = ExtResource("1")\n' > game/main.tscn
printf 'extends Node\n' > game/old.gd
printf 'uid://btest0000001\n' > game/old.gd.uid
printf 'extends RefCounted\n\n\nfunc test_items() -> void:\n\tassert(2 == 2, "two")\n\tassert(1 == 1)\n' > tests/test_items.gd
cat > export_presets.cfg <<'EOF'
[preset.0]

name="Leaky"
platform="macOS"
runnable=true
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path=""

[preset.0.options]

custom_template/debug=""

[preset.1]

name="Clean"
platform="macOS"
runnable=false
export_filter="all_resources"
include_filter=""
exclude_filter="tests/*, test/*"
export_path=""

[preset.1.options]

custom_template/debug=""
EOF
git add -A && git commit -qm base

# --- dirty change set
cat >> game/main.gd <<'EOF'
	print("debug value ", items)
	@warning_ignore("unused_variable")
	var unused := 1
	#var old_speed = 3
	# Returns the scaled value (prose, must not be flagged).
	# TODO fix later
	# TODO(yu): owned todo is fine
	assert(items.pop_back() != null)
	assert(is_instance_valid(self), "safe")
EOF
python3 -I - <<'EOF'
import re
p="tests/test_items.gd"; s=open(p).read(); open(p,"w").write(s.replace('\tassert(1 == 1)\n',''))
EOF
rm game/old.gd
printf 'extends SceneTree\n' > game/probe_test.gd
out=$("${GD[@]}" hygiene 2>&1); code=$?
check "dirty: exit 1 and RESULT FAIL" '[ $code -eq 1 ] && printf "%s" "$out" | grep -q "RESULT: FAIL"' "$out"
check "dirty: debug print caught" 'printf "%s" "$out" | grep -q "debug print added.*game/main.gd"' "$out"
check "dirty: warning_ignore without reason caught" 'printf "%s" "$out" | grep -q "@warning_ignore without a reason"' "$out"
check "dirty: commented-out code caught" 'printf "%s" "$out" | grep -q "commented-out code added.*#var old_speed"' "$out"
check "dirty: prose comment not flagged" '! printf "%s" "$out" | grep -q "Returns the scaled"' "$out"
check "dirty: ownerless TODO caught, owned TODO not" \
	'[ "$(printf "%s" "$out" | grep -c "TODO/FIXME without owner")" = 1 ]' "$out"
check "dirty: side-effect assert caught, safe assert not" \
	'printf "%s" "$out" | grep -q "assert() calls pop_back" && ! printf "%s" "$out" | grep -q "calls is_instance_valid"' "$out"
check "dirty: weakened test caught" 'printf "%s" "$out" | grep -q "assertions removed from a test.*tests/test_items.gd"' "$out"
check "dirty: probe file caught" 'printf "%s" "$out" | grep -q "scratch/probe file left behind: game/probe_test.gd"' "$out"
check "dirty: orphan uid caught" 'printf "%s" "$out" | grep -q "orphan .uid.*game/old.gd.uid"' "$out"
check "dirty: leaky export preset warned" 'printf "%s" "$out" | grep -q "export preset \"Leaky\" does not exclude tests/\*"' "$out"

# --- clean change set
git checkout -q -- . && git clean -qfd
printf '\n\nfunc total() -> int:\n\tvar sum: int = 0\n\tfor value: int in items:\n\t\tsum += value\n\treturn sum\n' >> game/main.gd
out=$("${GD[@]}" hygiene 2>&1); code=$?
check "clean: PASS (only the leaky-preset warning)" '[ $code -eq 0 ] && printf "%s" "$out" | grep -q "RESULT: PASS"' "$out"

# --- release
out=$("${GD[@]}" release --preset Missing 2>&1); code=$?
check "release: unknown preset is NOT ASSESSED (exit 2)" '[ $code -eq 2 ] && printf "%s" "$out" | grep -q "NOT ASSESSED"' "$out"
out=$("${GD[@]}" release --preset Leaky --frames 30 2>&1); code=$?
check "release: leaky preset fails on shipped tests" '[ $code -eq 1 ] && printf "%s" "$out" | grep -q "should not ship: tests/"' "$out"
out=$("${GD[@]}" release --preset Clean --frames 30 2>&1); code=$?
check "release: clean preset exports, contents OK, boots" '[ $code -eq 0 ] && printf "%s" "$out" | grep -q "\[boot\] OK"' "$out"
python3 -I - <<'PYEOF'
p="game/main.gd"; s=open(p).read()
open(p,"w").write(s.replace("\tpass\n", "\tvar broken: Array[int] = []\n\tpush_warning(str(broken[5]))\n", 1))
PYEOF
out=$("${GD[@]}" release --preset Clean --frames 30 2>&1); code=$?
check "release: runtime error in exported pack fails boot" '[ $code -eq 1 ] && printf "%s" "$out" | grep -q "\[boot\] FAIL"' "$out"

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
