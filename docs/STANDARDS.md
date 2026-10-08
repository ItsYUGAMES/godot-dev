# Godot 4.7 development standards — cross-validated

Canonical rule set for the `godot-dev` plugin. The skill's reference files are operational
distillations of this document; this file itself is never loaded into an agent's context.
Date: 2026-10-08. Engine verified: `4.7.stable.official.5b4e0cb0f`.

## 1. Sources and evidence levels

| Tag | Source | Where |
|---|---|---|
| D1–D8 | Official Godot 4.7 docs (manual and class reference) | https://docs.godotengine.org/en/stable/ |
| M1, M2 | Official demo projects (master @ b761b4c, all targeting 4.7) | https://github.com/godotengine/godot-demo-projects |
| P | *Game Programming Patterns* (Nystrom), mapped to Godot | https://gameprogrammingpatterns.com/ |
| S | High-star Godot agent skills, Godot MCP guidance, official skill-authoring guidance | Survey of public GitHub repos and Anthropic docs, 2026-10-08 |
| W | Game-programmer workflow (studio, indie Godot, agent-driven) | Survey of GDC talks, studio engineering blogs, Godot docs |
| A | godot-ai v4.3.0 | https://github.com/hi-godot/godot-ai |
| R | Expert code/test standards and keep-vs-delete lifecycle (Epic, Unity, Godot, Rare, Riot, Factorio, agent guidance) | Survey of published standards, GDC talks and postmortems |
| V | Verified by running the installed Godot 4.7 binary | Section 4 of this file |

The per-source research reports behind the S, W and R surveys were written while building the
plugin and are not part of this repository; each rule below names its source tags.

**Adoption rule.** A rule is adopted when an official source states it and nothing
contradicts it, or when two independent sources agree. **Precedence on conflict:**
V (engine binary) > class reference > manual > official demos > community skills.
GPP supplies design principles only; where Godot already provides the mechanism, the
Godot-native form wins. Community rules that copy each other count as one source.

## 2. Conflicts and resolutions

| # | Conflict | Sources | Resolution |
|---|---|---|---|
| C1 | `:=` inference: banned (some skills) vs preferred when type is obvious (style guide) | S vs D2, M1 | Use `:=` only when the right-hand side names the type on the same line (`Foo.new()`, literal, `as T`); write `: T` otherwise. `$Node` and Variant-returning calls (`dict["k"]`, `JSON.parse_string`) never use bare `:=`. |
| C2 | Member order differs across skills | S vs D2, M1 | Official order (D2-15): annotations → `class_name` → `extends` → `##` doc → signals → enums → consts → static vars → `@export` → vars → `@onready` → virtuals → public → private → inner classes. |
| C3 | `get_node() as T` "more type-safe" vs `var n: T = $N` | D2 conflict | Required nodes: explicit type hint (fails loudly at load). `as` + null check only when a mismatch is expected. Demos' `@onready var x := $X as T` is acceptable for nodes that may legitimately differ. |
| C4 | Object pooling recommended (P) vs usually unnecessary in GDScript (D1-50) | P vs D1 | No default pooling; pool only on profiled spawn spikes, fully reset on reuse. |
| C5 | Singletons rejected (P) vs autoloads allowed (D1-15) | P vs D1 | Autoload only broad, self-contained systems that own their data (save, settings, audio bus routing, quest state). Helpers: `class_name` + `static func`. No "GameManager" that mutates other nodes. |
| C6 | Global EventBus autoload (community idiom) | S vs P | Allowed narrowly: ≤ a handful of truly global, cross-scene events, documented in one file. Feature-local communication uses direct signals ("signal up, call down"). |
| C7 | Hand-writing `.tscn` (forbidden vs taught) | S, A | Prefer editor/godot-ai operations when the editor has the scene open (the editor's in-memory copy wins on save). Hand-edit text only with the format rules (reference `scene-files.md`), never binary/encoded blocks, and verify with `gd.py check` (instantiates every scene). |
| C8 | Signal connections in editor vs code | M1/M2 (editor-heavy) vs S (code) | Both valid. Connections an agent creates go in code (`sig.connect(_on_x)`) unless the scene is edited through the editor/MCP; never string-based `connect("sig", obj, "m")`. |
| C9 | `--check-only` as parse gate | S, W | Rejected: **V-1** shows it fails valid autoload references. Use `gd.py check` (load + instantiate under a SceneTree script after `--import`). |
| C10 | Jolt default | D5 (gdd_0268 vs 0251) | New projects created in 4.6+ write `physics/3d/physics_engine="Jolt Physics"`; an absent key means the engine default (**V-6**). Read the setting before applying Jolt-specific notes. |
| C11 | `move_and_slide` "up to five" collisions | D5 vs class ref | `max_slides` default is **4** (**V-3**). |
| C12 | AnimationTree must be activated | older guides vs D8 | `AnimationTree.active` defaults to `true` in 4.7 (**V-3**). |
| C13 | Force Vertex Shading default on mobile disables `light()` | D6 | Not default in 4.7: `force_vertex_shading=false`, no mobile override (**V-3**). Still: never rely on `light()` running when vertex shading is enabled. |
| C14 | `roughness_layers` 8→7 vs 7→8 | D1 | Default is **8** (**V-3**). |
| C15 | Master-branch-looking APIs (`tween_await`, `add_dock(EditorDock)`, `CONNECT_APPEND_SOURCE_OBJECT`, `Logger`/`OS.add_logger`, `ResourceLoader.list_directory`, `@abstract`/`Script.is_abstract`, `FoldableContainer`, `DrawableTexture2D`, `AreaLight3D`, `InputEvent.DEVICE_ID_MOUSE`, `Control.custom_maximum_size`) | D7, D8, D3 | All present in 4.7 stable (**V-2**). |
| C16 | `SurfaceTool.add_smooth_group` | D3 | Does not exist; `set_smooth_group(index)` (**V-2**). |
| C17 | `add_control_to_dock` deprecated? | D5, D7, M1 | Still exists but deprecated in 4.7 docs; use `add_dock(EditorDock)` (**V-2**, D7). |
| C18 | Headless screenshots for visual checks | W | Impossible: dummy renderer returns no texture (**V-4**). Visual checks need a windowed run or godot-ai `editor_screenshot`. |
| C19 | `--import` rebuilds the `class_name` cache on a fresh clone | S, W | Confirmed (**V-5**): fresh project without `.godot/`, `--import` then a SceneTree script resolves `class_name` + autoload references. |
| C20 | Exit code 0 means success | S, W | False: a smoke run with a runtime script error exits 0 (**V-1**). Gate on parsed error lines and an explicit verdict. |
| C21 | Physics interpolation on by default? | D5, M2 | Off by default (**V-3**); demos (11/11 Jolt 3D demos) enable it with 120 ticks for action games. Recommend enabling for character games; then `reset_physics_interpolation()` after teleports. |
| C22 | C# vs GDScript | S (godogen C#) vs D2, M | GDScript default; C# cannot export to Web, needs the .NET editor, profiler doesn't cover it. |
| C23 | `@export_file` stores UID vs path | D1, D7 | Since 4.4 `@export_file` stores `uid://`; use `@export_file_path` (4.5+) when a raw path is required. |
| C24 | `Resource.duplicate(true)` deep copy | D1, D7 | Since 4.5 it no longer copies external sub-resources; use `duplicate_deep(Resource.DEEP_DUPLICATE_ALL)` (exists, **V-2**). |
| C25 | godot-ai version coupling | A | The editor accepts only an exact-version backend; the plugin launcher pins `godot-ai==<addons/godot_ai/plugin.cfg version>`. |
| C26 | `export_presets.cfg` ignored (demo repo `.gitignore`) vs committed (docs) | M1 vs D4 | Commit it (CI exports need it); secrets live separately in `.godot/export_credentials.cfg`, which is never committed. The demo repo ignores it only because each demo is exported by CI with its own presets. |
| C27 | Godot-spawned vs bridge-spawned godot-ai backend at the same instant | A, **V-8** | Editor-first and bridge-first both work; a simultaneous start can leave a mismatched capability record (HTTP 401 / `PORT_OCCUPIED`) — reconnect the MCP server. |
| C28 | Type everything (Godot) vs don't annotate untouched code (agent guidance) | R | Scope rule: type everything you write or change; don't retrofit code you only pass by. |
| C29 | Rare auto-deletes unfixed flaky tests vs "never remove tests" (agent guidance) | R | Deletion is a team decision made over weeks; an agent never deletes/skips/loosens tests to get green, deletes a test only with its removed subject, and reports flaky tests with evidence. |
| C30 | No automated tests on fun-finding prototypes (Rare) vs "give the agent a runnable check" | R | A check is not a permanent test: prototypes get `GD check` + throwaway probes; permanent tests start when a mechanic enters production. |
| C31 | `test/` (GUT/GdUnit4 default) vs `tests/` (godot-ai runner) | R, A | The repo's existing root wins; never split suites across both. |

## 3. Final standards

Tags after each rule name its sources. "MUST" = gate/blocker, "SHOULD" = default, "AVOID" = needs a reason.

### 3.1 Ground truth and version safety
- S01 MUST read the target version from `project.godot` (`config/features`) and `godot --version` before writing engine code; these rules target 4.7. [S, W, D1]
- S02 MUST look up any engine class/member not certain to exist in 4.x (`gd.py api Class.member`); never emit Godot 3 names (KinematicBody, Spatial, `yield`, `setget`, `instance()`, `connect("sig", obj, "m")`, `export var`, `onready`, `tool`). [S, D1, D2, V-2]
- S03 MUST NOT edit `.godot/`, `*.import`, `*.uid` content, or binary/base64 scene blocks; move/rename assets inside the editor (or move `.uid` with the script and re-save referencing scenes). [D1, D3, M1, W]

### 3.2 GDScript
- S10 MUST type all variables, parameters and returns (`-> void` included); typed collections `Array[T]`, `Dictionary[K, V]`; enable `untyped_declaration` warning. [D2, M1 94–97%, M2 91–96%, S]
- S11 MUST follow the official naming: snake_case files/functions/vars/signals, PascalCase classes/nodes, CONSTANT_CASE constants/enum members, `_private`; past-tense signal names; handlers `_on_<node>_<signal>`. [D2, D1, M1, M2]
- S12 MUST use the official member order (C2) and tabs, `and/or/not`, double quotes, `0.5` not `.5`. [D2, M1]
- S13 SHOULD use `&"name"` for StringName (actions, groups, animations) and `^"path"` for NodePath literals in hot code. [M1, M2, D7]
- S14 MUST use typed math (`clampf`, `absi`, `lerpf`…), `is_equal_approx` for floats, `posmod/fposmod` for true modulo; remember `5 / 2 == 2`. [D2, M1]
- S15 MUST connect with `sig.connect(callable)`, emit with `sig.emit()`, call Callables with `.call()`; bound args follow signal args; declare signal parameter types. [D2, D7, M1]
- S16 MUST `await` coroutines whose result is used; never reassign captured locals in lambdas; avoid storing lambdas in RefCounted members; never `CONNECT_PERSIST` with lambdas. [D2, D7]
- S17 MUST NOT combine `@onready` with `@export`; MUST NOT read exported values in `_init()`; custom Resource `_init` params need defaults. [D2, D7]
- S18 SHOULD export the narrowest type (`@export var target: Node2D`, `@export var stats: EnemyStats`) instead of `NodePath`/`Resource`; `@export_range` for tunables. [D2, M1, W]
- S19 MUST report with `push_error`/`push_warning`; `assert()` only for side-effect-free checks (stripped in release). [D2, D7]
- S20 MUST call `super()` in overridden lifecycle methods when the parent logic must run; 4.7 typed-return overrides need an explicit `return`. [D1]

### 3.3 Scene tree, lifecycle, processing
- S30 MUST rely on lifecycle order: `_init` → (exports) → `_enter_tree` (parent first) → `@onready` → `_ready` (children first); `_ready` runs once unless `request_ready()`. [D2, D7]
- S31 MUST move bodies and do collision logic in `_physics_process`; visuals in `_process`; scale rates by `delta`; frame-rate-independent smoothing `lerp(a, b, 1.0 - exp(-k * delta))`. [D2, D5, M2, D4]
- S32 MUST instance with `preload/load(...).instantiate()` + `add_child()`; `queue_free()` not `free()`; `is_instance_valid()` for possibly-freed refs. [D2, D7]
- S33 MUST defer tree/physics mutations made from physics callbacks or threads (`set_deferred`, `call_deferred`); never call a method deferred from itself; delay a frame with `await get_tree().process_frame`. [D1, D7, M1]
- S34 MUST change scenes with `change_scene_to_file/packed` (deferred; `await get_tree().scene_changed` to reach the new one) or a manual deferred swap. [D7, M1]
- S35 SHOULD use `%UniqueName` for in-scene references that may move; AVOID `..` and deep hard-coded paths; AVOID `find_child` in hot paths. [D2, D7, M1]
- S36 MUST set `owner` on nodes created by tool/editor code (and every node packed with `PackedScene.pack()`), without recursing into instanced scenes. [D1, D7, S]
- S37 SHOULD pause via `get_tree().paused` and `process_mode` (pause UI = `PROCESS_MODE_ALWAYS`); `create_timer` ignores pause unless told otherwise. [D2, D7, M1]

### 3.4 Architecture and patterns
- S40 MUST keep scenes self-contained; parents inject dependencies (signal, Callable, typed export); siblings don't reference each other. [D1]
- S41 SHOULD "call down, signal up": children emit, owners act (spawning included). [D1, D2, S]
- S42 MUST NOT mutate a shared Resource for one instance: `duplicate()` / `resource_local_to_scene` / `duplicate_deep`. [D1, D7, P, S]
- S43 SHOULD model kinds as `class_name X extends Resource` with `@export` fields saved as `.tres` (Type Object/Flyweight). [P, D2]
- S44 SHOULD compose behavior from child nodes/scenes; keep inheritance shallow (≤2–3 levels). [P, S, D1]
- S45 SHOULD replace ≥2 exclusive bools with `enum` + `match`; graduate to state nodes/objects (enter/exit) when states own data; pushdown stack for "return to previous". [P, M1]
- S46 AVOID speculative abstraction, custom ECS, home-made scripting languages/VMs. [P, S]
- S47 AVOID autoload managers; follow C5/C6. [D1, P]

### 3.5 Domains (details live in skill references)
- Physics: never scale bodies/shapes; shapes are direct children; `move_and_slide()` with velocity in units/s (no `* delta`), gravity via `get_gravity() * delta`; read floor state after the call; RigidBody via forces/`_integrate_forces`; raycasts in `_physics_process`; name layers. [D5, D8, M1, M2]
- 2D: TileMapLayer only (TileMap deprecated); Parallax2D; CanvasLayer for HUD; `queue_redraw()` for `_draw`. [D3, D8, V-2]
- 3D: −Z forward (imported assets face +Z), 1 unit = 1 m, add Camera3D/WorldEnvironment/lights yourself; check renderer feature support. [D3]
- Animation: address `"library/anim"`; drive AnimationTree via `set("parameters/...")`; looping animations never emit `animation_finished`; physics-moved animations use physics callback mode. [D3, D8]
- UI: Containers + size flags; theme constants via `add_theme_*_override`; initial `grab_focus()`; no `ui_*` actions in gameplay; decorative Controls `mouse_filter = IGNORE`. [D6, D8, M1]
- Input: InputMap actions (snake_case, keyboard + pad each); gameplay in `_unhandled_input`; held state polled in `_physics_process`; `Input.get_vector()`. [D4, D7, M1, M2]
- Data: saves in `user://` only; ConfigFile/JSON/`store_var` without objects for untrusted data; check `FileAccess.open()`/`JSON.parse()` errors; background loading via `load_threaded_*`. [D4, D7, M1]
- Navigation: no queries in `_ready`; await a physics frame / iteration id; `get_next_path_position()` once per physics frame. [D4, D8, M2]
- Multiplayer: server authority; validate `any_peer` RPCs with `get_remote_sender_id()` (captured before `await`); identical `@rpc` sets on all peers; spawner/synchronizer split input vs state. [D4, D8, M2]
- Shaders: explicit literals/casts, `source_color`, screen reads via `hint_screen_texture` uniforms, `.gdshaderinc` for shared code; shaders compile lazily — verify visually. [D6, S]
- Threads: no scene-tree access from threads; Mutex shared data; `wait_to_finish()` every Thread; one loader thread. [D5, D7, M1, M2]

### 3.6 Performance
- S60 MUST profile before optimizing; decide CPU- vs GPU-bound; state budgets in ms (16.66 ms @60 fps). [D5, W, P]
- S61 SHOULD disable idle/offscreen processing, prefer signals/timers to polling, use MultiMesh/servers/packed arrays only for thousands of identical items. [D5, P]
- S62 SHOULD prevent shader-compilation stutter with load-time warm-up; avoid `load()` in `_process`. [D5, S]

### 3.7 Verification and workflow
- S70 MUST end every code change with `gd.py check` = PASS (import + autoload-aware load + instantiate) and, for runtime changes, `gd.py check --smoke`; paste the verdict. [S, W, V-1]
- S71 MUST treat Godot exit code 0 as non-evidence; parse error lines; report `NOT ASSESSED` when a check could not run. [S, V-1]
- S72 MUST run every Godot CLI call under a timeout. [S]
- S73 SHOULD verify behavior through state/logs/tests before screenshots; screenshots only for visual questions. [A, S, W]
- S74 MUST commit (or confirm a clean tree) before editor/MCP mutations — checkpoints don't capture them. [W]
- S75 MUST split acceptance into agent-verifiable items and human-open "feel" items; expose feel values as `@export_range`. [W]
- S76 SHOULD work one system/feature per session with an out-of-scope list; one-line tuning skips planning. [W]

### 3.8 Hygiene: keep, strip, delete
- S80 MUST remove investigation `print`/`print_debug`/`print_stack` before finishing: only `assert()` is stripped from release exports; prints ship. [R, D2]
- S81 MUST keep `assert()` free of side effects (not evaluated in release); data/designer errors use `push_error()` + safe default; scene setup errors use `_get_configuration_warnings()`. [R, D2, D7]
- S82 MUST keep debug tools (overlays, cheats, consoles) behind `OS.is_debug_build()` or a custom feature tag; editor code behind `Engine.is_editor_hint()`. [R, D5]
- S83 MUST put scratch/probe files outside `res://` (or `res://.scratch/`, gitignored) and delete them with their `.uid`/`.import`; revert temporary main-scene/input/autoload edits. [R]
- S84 MUST NOT delete, skip or loosen tests to get green; bug fixes follow red → green → revert-red → green and keep the test. [R]
- S85 SHOULD delete commented-out code and ownerless TODOs; keep why-comments and `TODO(owner)`. [R]
- S86 MUST exclude test roots and test addons from release presets via `exclude_filter` (recursive, **V-9**), never via `.gdignore`; never exclude addons referenced by autoloads. [R, D4, V-9]
- S87 SHOULD treat prototypes as answers: keep verdict, tunables and feature list; archive the code, don't merge it. [R, P]
- S88 MUST end with `gd.py hygiene` PASS and, for release-relevant work, `gd.py release --preset …` PASS (**V-10**). [R, V-10]

## 4. Empirical verification log (Godot 4.7.stable.official.5b4e0cb0f, macOS)

- **V-1** Fresh test project with an autoload `Game`, a `class_name Health` resource, and a main scene using both. `--headless --check-only --script main.gd` → `Compile Error: Identifier not found: Game` (false failure). `gd.py check` → PASS. Broken variant (parse error, scene referencing a missing script, out-of-bounds index at runtime) → `gd.py check --smoke` FAIL with all three errors listed; the smoke run itself exited 0.
- **V-2** `gd.py api` against ClassDB: FOUND `Tween.tween_await`, `AwaitTweener`, `EditorPlugin.add_dock(dock: EditorDock)`, `Object.CONNECT_APPEND_SOURCE_OBJECT`, `Script.is_abstract`, `Logger`, `OS.add_logger`, `ResourceLoader.list_directory`, `AreaLight3D`, `SurfaceTool.set_smooth_group`, `TileMap`, `TileMapLayer`, `InputEvent.DEVICE_ID_MOUSE`, `FoldableContainer`, `DrawableTexture2D`, `Control.custom_maximum_size`, `AnimationMixer.active`, `Resource.duplicate_deep`, `EditorPlugin.add_control_to_dock`, `Parallax2D`; MISSING `SurfaceTool.add_smooth_group`, `KinematicBody2D` (with correct suggestions).
- **V-3** Defaults: `CharacterBody2D.max_slides=4`, `floor_max_angle=45°`, `AnimationTree.active=true`, `Camera2D.process_callback=IDLE`, `physics_interpolation=false`, `physics_ticks_per_second=60`, `force_vertex_shading=false` (no `.mobile` override), `roughness_layers=8`, `stretch/mode=disabled`, `rendering_method=forward_plus`, `untyped_declaration=0` (off), `GPUParticles3D.draw_pass_1=null`.
- **V-4** `--headless` viewport texture: `texture_2d_get` error on the dummy renderer, image null.
- **V-5** Fresh clone (no `.godot/`) + `--import` → global class cache populated; subsequent SceneTree script resolves `class_name` and autoloads.
- **V-6** `physics/3d/physics_engine` absent → `DEFAULT`.
- **V-7** godot-ai v4.3.0 release triple downloaded from GitHub: SHA-256 equals the GitHub digests; vendored `release_verify.py` (sha256 `1b8c60c0…`) verifies signature, identity, archive hash and 313-file inventory with both uv Python 3.12 and macOS Python 3.9 (openssl fallback).
- **V-8** End-to-end (`tests/integration_godot_ai.sh`, isolated HOME, ports 18000/19500): hook
  installs + enables the add-on in a fresh 4.7 project; a headless editor (`GODOT_AI_ALLOW_HEADLESS=1`)
  loads it and spawns backend 4.3.0; the plugin's MCP launcher attaches, lists 47 tools and
  `editor_state` returns the project — PASS for editor-first and bridge-first orders. A test HOME
  under `/tmp` fails because godot-ai rejects capability dirs with world-writable ancestors.
- **V-9** Export `exclude_filter="test/*"` (`--export-pack`) omitted both `test/test_top.gd` and `test/unit/deep/test_deep.gd`; a control export without the filter contained both — the glob matches subfolders.
- **V-10** `--main-pack out.pck --script list_pack.gd` lists the pack's files (scripts appear as `*.gdc` + `*.gd.remap`); `--main-pack out.pck --quit-after N` boots the exported pack headless. `tests/gd_tests.sh` (16 checks) covers `gd.py hygiene` (catches prints, unexplained suppressions, commented-out code, ownerless TODOs, side-effect asserts, weakened tests, probe files, orphan `.uid`, leaky presets) and `gd.py release` (leaky preset fails, clean preset passes, runtime error in the pack fails boot).
