# GDScript 4.7 rules

## Layout and naming (official style guide; demos follow it)
- Order: `@tool`/`@icon`/`@abstract` → `class_name` → `extends` → `##` doc → signals → enums →
  consts → static vars → `@export` vars → vars → `@onready` vars → `_static_init` → static funcs →
  virtuals (`_init`, `_enter_tree`, `_ready`, `_process`, `_physics_process`, …) → public → private
  → inner classes. Public before private inside each group.
- Comments say why, not what; `##` docs on public members; `TODO(owner)`/`TODO #123` only;
  commented-out code is deleted (git has history).
- snake_case files/funcs/vars/signals/groups; PascalCase classes/nodes/enum names; CONSTANT_CASE
  consts and enum members (one per line, trailing comma); `_private` members and helpers.
- Signals past tense (`health_changed`, `died`); handlers `_on_<node_snake>_<signal>`.
- Tabs, LF, UTF-8 no BOM, final newline; ≤100 chars; two blank lines between functions;
  `and/or/not` (never `&&/||/!`); double quotes; `0.5` not `.5`; never `== true`.
- `class_name` only for types other scripts reference; else `const X = preload("res://x.gd")`.

## Static typing
- Type every var, param, return: `func hit(amount: int) -> void:`; `-> void` on virtuals too.
- `:=` only when the right side names the type: `var t := Timer.new()`, `var n := 3`,
  `var s := $Sprite as Sprite2D`. Otherwise explicit: `@onready var bar: ProgressBar = %LifeBar`.
  `var x := $Node` types as `Node`; `var hp := data["hp"]` / `JSON.parse_string()` won't compile.
- Typed collections: `Array[Enemy]`, `Dictionary[StringName, int]` (4.4+); nested typed arrays are
  unsupported; copy across element types with `typed.assign(other)`; `for e: Enemy in list`.
- Narrow with `is` then assign to a typed var before calling subclass members (avoids UNSAFE_*).
- Typed math: `absf/absi`, `clampf/clampi`, `lerpf`, `minf/maxi`, `roundi`, `snappedf`;
  `is_equal_approx` for floats; `5 / 2 == 2`; `%` is int-only → `fmod`, `posmod`, `fposmod`.
- `&"name"` StringName for actions/groups/animations; `^"path"` NodePath literals.
- Project settings: the typed-code warnings (`untyped_declaration`, `unsafe_*`,
  `return_value_discarded`) are Ignore by default and `res://addons` is excluded; strict projects
  set `untyped_declaration=2` and `unsafe_*=1` (changing levels needs user approval). Silence
  locally with `@warning_ignore("x")  # reason` — never without a reason.
- Scope: type what you write or change; don't retrofit untouched code in the same change.

## Exports and annotations
- Exports need a type or constant initializer; narrowest type (`@export var target: Node2D`,
  `@export var stats: EnemyStats`) instead of `NodePath`/`Resource`.
- Tunables: `@export_range(0.0, 20.0, 0.1, "suffix:m/s") var speed: float = 8.0`; groups with
  `@export_group`. Gameplay numbers live here or in Resources, not as literals in logic (tests
  read them too). Named enum export stores an int.
- Never `@onready` + `@export` on one var (error). `_init()` sees defaults, not inspector values.
- `@export_file` stores `uid://` (4.4+); `@export_file_path` for raw paths. Large scenes loaded
  on demand: `@export_file("*.tscn")` instead of `@export var s: PackedScene` (eager load).
- Setters run in the editor only in `@tool` scripts; custom Resource `_init` params need defaults.

## Signals, callables, await
- `signal health_changed(old: int, new: int)`; `health_changed.emit(a, b)`;
  `button.pressed.connect(_on_button_pressed)`; bound args come after signal args:
  `sig.connect(_on_hit.bind(id))`. Guard duplicates with `is_connected()`.
- Callables: `f.call(x)`, never `f(x)`; check `is_valid()`. `Callable.create(dict, "clear")` for
  Dictionary methods.
- `await sig` → value (1 arg), Array (2+), null (0). `await` any coroutine whose result you use.
- Lambdas capture by value: don't reassign captured locals; don't keep lambdas in RefCounted
  members (leak); no `CONNECT_PERSIST` with lambdas.
- Delay a frame: `await get_tree().process_frame`; one-shot timer:
  `await get_tree().create_timer(0.5, false).timeout` (second arg `false` = respect pause).

## Lifecycle and objects
- Init order: defaults → initializers → `_init` → exported values → `@onready` → `_ready`.
  `_enter_tree` parent-first; `_ready` children-first, once (re-add needs `request_ready()`).
- `super()` explicitly in overrides when parent logic must run; 4.7: an override of a
  typed-return method needs an explicit `return`.
- Plain `Object` → `free()` manually; RefCounted/Resource free themselves; Nodes → `queue_free()`.
  Freed refs are not null: `is_instance_valid(x)`. Break RefCounted cycles with `weakref()`.
- Error tiers: `assert(cond, "msg")` for programmer invariants only — stripped (not even
  evaluated) in release, so no side effects; `push_error()`/`push_warning()` + safe-default return
  for data/designer/player errors; `_get_configuration_warnings()` for scene setup mistakes.
  `print()` ships in release: no investigation prints left behind (`print_verbose()` for traces).
- Arrays/Dictionaries are references: `duplicate()` to copy; don't erase while iterating.

## Godot 3 → 4 traps (never emit the left side)
| Godot 3 | Godot 4.7 |
|---|---|
| `yield(obj, "sig")` | `await obj.sig` |
| `setget a, b` | `var x: int: set = _set_x, get = _get_x` or inline `set(v):` |
| `export(int, 0, 10) var x` / `onready var` / `tool` | `@export_range(0, 10) var x: int` / `@onready` / `@tool` |
| `connect("sig", self, "_m")`, `emit_signal("sig")` | `sig.connect(_m)`, `sig.emit()` |
| `.method()` parent call | `super.method()` / `super()` |
| `scene.instance()`, `change_scene()` | `instantiate()`, `change_scene_to_file()` |
| `KinematicBody2D`, `Spatial`, `Sprite`, `Position2D` | `CharacterBody2D`, `Node3D`, `Sprite2D`, `Marker2D` |
| `move_and_slide(velocity, up)` | set `velocity`, call `move_and_slide()` |
| `Tween` node, `YSort`, `Navigation2D` | `create_tween()`, `y_sort_enabled`, NavigationServer/agents |
| `File`, `Directory`, `OS.get_ticks_msec` | `FileAccess`, `DirAccess`, `Time.get_ticks_msec` |
| `update()`, `pause_mode`, `BUTTON_LEFT`, `PoolStringArray` | `queue_redraw()`, `process_mode`, `MOUSE_BUTTON_LEFT`, `PackedStringArray` |
| `rpc("f")`, `remote`/`master`/`puppet` | `f.rpc()`, `@rpc("any_peer")` etc. |
| `rect_size`, `margin_*`, `extents` | `size`, `offset_*`, `size` (full size) |
| `JSON.parse(text).result` | `JSON.parse_string(text)` or `JSON.new().parse()` + `.data` |
| `TileMap` layers | one `TileMapLayer` node per layer |

## Deprecated in 4.x (use the replacement)
`Color8()` → `Color.from_rgba8()`; `convert()` → `type_convert()`; `inst_to_dict()` →
`JSON.from_native()`; `NOTIFICATION_MOVED_IN_PARENT` → `NOTIFICATION_CHILD_ORDER_CHANGED`;
`EditorPlugin.get_editor_interface()` → `EditorInterface`; `add_control_to_dock()` →
`add_dock(EditorDock)`; `Resource.duplicate(true)` for external sub-resources →
`duplicate_deep(Resource.DEEP_DUPLICATE_ALL)`; `AudioEffectLimiter` → `AudioEffectHardLimiter`.
