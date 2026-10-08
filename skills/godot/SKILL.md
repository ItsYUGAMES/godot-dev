---
name: godot
description: Use when working on a Godot 4 game or project - GDScript, .gd/.tscn/.tres files, nodes, scenes, signals, physics, UI, shaders, animation, tilemaps, input, save/load, multiplayer, tests, export, or the godot-ai MCP editor tools - or when the user mentions Godot or a project.godot exists.
---

# Godot 4.7 router

Read this file, then only the reference rows your task needs (one level deep; never bulk-load).
`GD` below means `python3 "<base directory of this skill>/scripts/gd.py"` (the base directory is
shown when the skill loads; if python3 is missing use `uv run --no-project python`). It is the
verification gate: run it, don't read it.

## 0. Ground truth before code
- Version: read `config/features` in `project.godot` and `godot --version`. These rules target
  4.7; say so when the project differs. Models drift to Godot 3 / 4.0-era APIs.
- Unsure an engine name exists? `GD api Class Class.member` (installed-engine ClassDB; MISSING
  lines suggest real names). Never ship a Godot 3 name: KinematicBody*, Spatial, `yield`,
  `setget`, `instance()`, `connect("sig", obj, "m")`, `export var`, `onready var`, `tool`.
- Look at the existing scene/script before editing; follow the project's own conventions.

## 1. Workflow
One-line tuning or obvious fix → edit → gate (step 4). Anything touching scenes, input map,
autoloads, or more than one system → full loop in `references/workflow.md`:
1. Feature card: behavior in input actions, tunables with ranges, out-of-scope, agent-verifiable
   vs human-open (feel) checks.
2. Plan the smallest slice; `git commit` (or confirm clean tree) before editor/MCP mutations.
3. Test first where logic is testable (prototype phase: throwaway probe only); bug fix = red →
   green → revert fix (red) → restore (green); implement one system at a time.
4. Gate: `GD hygiene` and `GD check` (+ `--smoke` for runtime changes) → `RESULT: PASS`, plus
   project tests; `GD release --preset …` before handing over release-relevant work.
5. Report evidence (commands + verdicts), temporary artifacts created and deleted, what was kept
   and why; list feel items as open for the human.

## 2. Hard rules
1. Static typing everywhere: vars, params, `-> void`, `Array[T]`, `Dictionary[K, V]`. `:=` only
   when the right side names the type; `$Node`/`dict["k"]` need an explicit `: Type`.
2. Physics movement in `_physics_process`; `move_and_slide()` takes velocity in units/s (never
   `* delta`); gravity `velocity += get_gravity() * delta`; read `is_on_floor()` after the call.
3. Call down, signal up: children emit past-tense signals, owners act; `sig.connect(callable)`,
   `sig.emit()`; dependencies injected via typed `@export`, not deep paths or `get_parent()`.
4. Loaded Resources are shared: `duplicate()`/`resource_local_to_scene` before per-instance edits.
5. `res://` is read-only at runtime; saves/settings go to `user://`; never load Objects from
   untrusted data.
6. Defer tree and physics-state changes made inside physics callbacks or threads
   (`set_deferred`, `call_deferred`); `queue_free()`; `is_instance_valid()` for maybe-freed refs.
7. Scenes: when the editor has a scene open, change it through godot-ai, not the file. Hand-edit
   `.tscn` only per `references/scene-files.md`; never touch `.godot/`, `.import`, `.uid`
   contents or encoded blocks; move/rename assets in the editor.
8. TileMapLayer (not TileMap), Parallax2D, `create_tween()`, `change_scene_to_file()`,
   InputMap actions (no raw keycodes in gameplay, no `ui_*` actions outside UI).
9. Autoloads only for broad systems that own their data; helpers are `class_name` + `static func`.
10. No optimization, pooling, or threading without profiler evidence (budget in ms).
11. Godot exits 0 even after script errors: only `RESULT: PASS` counts; a check that could not
    run is `NOT ASSESSED`, never a pass. Feel is verified by a human, not claimed.
12. Finish clean: only `assert()` is stripped in release — remove investigation prints, keep debug
    tools behind `OS.is_debug_build()`; scratch files live outside `res://` and are deleted; no
    commented-out code; `@warning_ignore` needs a reason; never delete, skip or loosen a test to
    get green.

## 3. Route: Task → Read → Verify
| Task | Read | Verify |
|---|---|---|
| Plan a feature, milestone, feature card, review | `references/workflow.md` | card + gate evidence |
| Any GDScript (style, typing, signals, await, exports, 3→4 traps) | `references/gdscript.md` | `GD check` |
| Scene composition, communication, autoloads, patterns, state machines | `references/architecture.md` | review vs rules |
| New project, settings, folders, VCS, renderer, stretch, language choice | `references/project-setup.md` | `GD check` |
| Physics bodies, character controllers, collisions, raycasts, Jolt | `references/physics.md` | `GD check --smoke` |
| 2D: tilemaps, parallax, canvas layers, lights, particles, `_draw`, pixel art | `references/2d.md` | `--smoke` + screenshot |
| 3D: transforms, cameras, materials, lights/GI, LOD, model import | `references/3d.md` | `--smoke` + screenshot |
| AnimationPlayer/Tree, state machines, tweens, sprite animation | `references/animation.md` | `--smoke` |
| UI: containers, themes, focus/gamepad nav, fonts, RichText, i18n | `references/ui.md` | screenshot at 2 sizes |
| Input actions, rebinding, mouse capture, controllers, touch | `references/input.md` | runtime input test |
| Save/load, file paths, resource loading, threads, background loading | `references/data-io.md` | round-trip test |
| Audio buses, players, music sync | `references/audio.md` | `--smoke` |
| Navigation agents, navmesh, avoidance | `references/navigation.md` | `--smoke` |
| Multiplayer, RPC, spawner/synchronizer, HTTP, WebSocket | `references/multiplayer.md` | 2-instance run |
| Shaders, post-processing, VFX, compute | `references/shaders.md` | screenshot |
| Performance, profiling, stutter, MultiMesh | `references/performance.md` | ms vs budget |
| Hand-editing `.tscn`/`.tres` text | `references/scene-files.md` | `GD check` |
| Tests (GUT/GdUnit4), CI, headless runs, export, web/mobile | `references/testing-export.md` | test exit codes |
| Finishing a task, cleanup, debug code, keep/strip/delete, release builds | `references/hygiene.md` | `GD hygiene`, `GD release` |
| godot-ai MCP editor tools (`mcp__*godot-ai*`) | `references/godot-ai.md` | tool diagnostics |
| Editor plugins, `@tool` scripts | `references/editor-plugins.md` | reload plugin |

Skip the router for read-only questions and single-line edits; don't re-route every turn.
