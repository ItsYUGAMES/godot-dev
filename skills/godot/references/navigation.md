# Navigation (NavigationServer / agents; classes marked experimental)

## Setup
- Bake a navmesh for the agent's center: NavigationRegion2D/3D with radius margin; collision and
  visuals aren't used automatically. Runtime bakes: parse collision shapes (not visual meshes),
  bake on a thread, never scale source geometry; rebake after a region's scale changes.
- Regions connect only through shared edges (or within `edge_connection_margin`); overlap alone
  doesn't connect; no nested outlines. NavigationLink needs custom traversal code.
- Different actor sizes → separate navigation maps/navmeshes. Filter with `navigation_layers` on
  queries instead of toggling regions.

## First-frame rule
The map syncs on the physics frame: no path queries or `target_position` in `_ready`. Defer:
```gdscript
func _ready() -> void:
	setup_navigation.call_deferred()

func setup_navigation() -> void:
	await get_tree().physics_frame
	agent.target_position = target.global_position
```
Or skip queries while `NavigationServer2D.map_get_iteration_id(map) == 0`.

## Agent loop (2D; 3D identical with Vector3)
```gdscript
@onready var agent: NavigationAgent2D = $NavigationAgent2D
@export_range(0.0, 1000.0) var speed: float = 200.0


func _physics_process(_delta: float) -> void:
	if agent.is_navigation_finished():
		return
	var next := agent.get_next_path_position()
	var desired := global_position.direction_to(next) * speed
	if agent.avoidance_enabled:
		agent.velocity = desired  # result arrives in velocity_computed
	else:
		velocity = desired
		move_and_slide()


func _on_navigation_agent_2d_velocity_computed(safe_velocity: Vector2) -> void:
	velocity = safe_velocity
	move_and_slide()
```
- Call `get_next_path_position()` once per physics frame; moving the actor is your code.
- Avoidance: `avoidance_enabled = true` (default false), set `agent.velocity`, move in
  `velocity_computed`; avoidance ignores navmesh bounds. Moving obstacles: radius obstacles.
- Don't retarget every frame: only when the target moved past a threshold; stagger many agents.
- Don't call path methods inside agent signal callbacks (defer them).
- Server changes apply after the next sync (4.5+ async region updates); `map_force_update()` is
  gone. Debug draw only in debug builds (Debug → Visible Navigation).
- Grid games: AStarGrid2D is simpler than navmeshes.
