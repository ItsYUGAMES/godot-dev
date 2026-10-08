# Architecture, communication, patterns

Judge a design by how cheaply it absorbs change; every abstraction is a bet on future change, and
a wrong bet is pure cost. Godot already owns the game loop, composition (node tree), observers
(signals), prototypes (PackedScene) and flyweights (shared Resources) — use those, don't rebuild.

## Scene composition
- A game concept = a scene with a scripted root; script-only `class_name` types are for reusable
  tools. Build big hierarchies as PackedScenes, not in code.
- Scenes are self-contained: the parent injects what a child needs (connect its signal, set a
  typed `@export`/property, pass a Callable). Siblings never reference each other; the common
  ancestor wires them.
- Parent-child means "lifetime and transform belong together". Follow nodes elsewhere with
  RemoteTransform2D/3D or `top_level = true`.
- Typical root: `Main` (script) → `World` (Node2D/3D, swap level children) + `HUD`
  (CanvasLayer/Control). Keep the player outside swappable level branches in larger games.
- State shared by a scene's parts lives on its root; tight pairs reference each other via typed
  exports/`%UniqueName`; loose events go through signals.

## Communication: choose by intent
| Need | Use |
|---|---|
| Parent tells child to act | Direct method call on a typed reference |
| Child reports something happened | Past-tense signal, parent connects ("call down, signal up") |
| Child wants a spawn / scene change | Emit a request signal; owner instantiates and parents |
| Unrelated systems (achievements, audio, analytics) | Signal on a narrow autoload, documented list of events |
| Broadcast to many nodes | Groups: `get_tree().call_group(&"enemies", &"alert")` |
| Handle later / break call recursion | `call_deferred`, `CONNECT_DEFERRED` |
| Undo / replay / rebinding | Command objects (RefCounted with `execute/undo`), `UndoRedo`, InputMap |

Avoid: signals inside one feature for simple calls, listeners that depend on connection order,
emitting from inside a handler of the same signal, lapsed listeners (disconnect or free them).

## Global access policy (most to least preferred)
1. Pass it in (`@export`, constructor/setup method). 2. `owner`/scene-root state.
3. `class_name` + `static func`/`static var` for stateless helpers and constants.
4. Autoload — only broad, self-contained systems that own their data (save/settings, audio
   routing, quest/dialogue state, scene transitions). No "GameManager" that edits other nodes.
5. A global event bus: allowed for a handful of truly global events in one documented file.
Never `free()` an autoload; their order in the list is their init order.

## Data
- Kinds as data: `class_name EnemyStats extends Resource` + `@export` fields, saved as `.tres`;
  vary behavior by a referenced Script/PackedScene/enum, not subclasses per kind.
- Shared by default: `load()` returns one cached instance. Per-instance mutation →
  `duplicate()`, `resource_local_to_scene = true`, or `duplicate_deep(DEEP_DUPLICATE_ALL)`.
- Non-node data: RefCounted (auto-freed) or Resource (serializable); Object only with manual
  `free()`. Don't make nodes for pure data.
- Emit `changed` from Resource setters (`emit_changed()`) if editors/UI must react.

## State machines
- ≥2 mutually exclusive bools → `enum State { IDLE, RUN, JUMP }` + `match` in `_physics_process`
  (fine for simple actors).
- States that own data or need enter/exit → state nodes: each child `State` has `enter()`,
  `exit()`, `physics_update(delta)`, `handle_input(event)` and emits `finished(next: StringName)`;
  the machine forwards callbacks, swaps current. Reach the actor through `owner`.
- Need "return to previous" (stagger, pause) → pushdown stack. Many orthogonal modes → parallel
  machines (n+m states, not n×m). Animation blending → AnimationTree state machine; gameplay
  rules stay in code. Complex AI → behavior tree/utility AI, not a giant FSM.

## Pattern cards (Game Programming Patterns → Godot)
- Component: compose child nodes/scenes; no home-made ECS.
- Type Object / Flyweight: exported Resources; immutable when shared.
- Prototype: spawn from cached PackedScene (`preload` const + `instantiate()`), never `clone()`.
- Observer: signals across domains; direct calls within one feature.
- Event Queue: `call_deferred` with data snapshots when "later" is needed; never emit from handler.
- Command: action objects for undo/replay; InputMap actions for rebinding.
- Update Method: `_process/_physics_process`; disable idle nodes (`process_mode`, `set_process`,
  VisibleOnScreenEnabler2D/3D); timers and signals over per-frame polling.
- Game Loop / Double Buffer: engine-owned; never write your own loop or frame buffering.
- Service Locator / Singleton: last resort (see policy); null-object default if used.
- Object Pool: only for profiled spawn spikes; fully reset on reuse.
- Dirty Flag: setter marks dirty, recompute once (deferred or on read).
- Spatial Partition: Area2D/3D and `PhysicsDirectSpaceState` queries; custom grids only for
  profiled non-physics lookups (AStarGrid2D for grid paths).
- Data Locality: thousands of identical items → MultiMesh/servers/Packed*Array, not a node each.
- Bytecode: don't build a VM/DSL; use Resources, GDScript, or `Expression` for formulas.

## Anti-patterns
Manager classes doing work objects could do themselves; deep `extends` chains; bool soups;
speculative interfaces/plugin systems; mutating shared Resources; removing items while iterating;
physics in `_process`; lazy `load()` mid-gameplay (preload or `load_threaded_request` at checkpoints).
