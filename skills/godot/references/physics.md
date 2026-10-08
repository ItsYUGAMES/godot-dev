# Physics and character controllers

## Body choice
| Need | Node |
|---|---|
| Player/NPC you steer | CharacterBody2D/3D + `move_and_slide()` |
| Simulated object (crates, ragdoll, projectiles with bounce) | RigidBody2D/3D (forces/impulses) |
| Moving platform / door driven by animation or code | AnimatableBody2D/3D |
| Level geometry | StaticBody2D/3D (trimesh/concave only here) |
| Triggers, hitboxes, gravity zones | Area2D/3D (signals) |

## Rules
- Movement and collision logic in `_physics_process` (60 Hz default). Never set `position` of a
  body to move it; never scale bodies or CollisionShapes (resize the shape; make it unique first).
- CollisionShape/CollisionPolygon must be direct children of the body. Prefer primitives;
  concave shapes only on StaticBody; few non-transformed shapes per body.
- `collision_layer` = layers I'm on; `collision_mask` = layers I detect; A detects B only if B's
  layer is in A's mask. `set_collision_mask_value(n, true)` is 1-based. Name the layers.
- Toggling shapes/monitoring inside physics callbacks: `set_deferred(&"disabled", true)`.
- RigidBody: forces/impulses or `_integrate_forces(state)`; don't set its transform or
  `look_at()` every frame; contact signals need `contact_monitor = true` and
  `max_contacts_reported > 0`; sleeping bodies skip `_integrate_forces`.
- Area: `body_entered` for bodies, `area_entered` for areas; `get_overlapping_*` updates once
  per physics step — use ShapeCast + `force_shapecast_update()` for same-frame checks;
  trimesh shapes under Area3D are hollow.
- Raycasts: RayCast2D/3D results are one physics frame old (`force_raycast_update()` for now);
  check `is_colliding()` first; collider may be TileMapLayer/GridMap/CSG, not only bodies.
  Space queries only inside `_physics_process`; set an explicit mask (query default = all 32
  layers); `{}` result = miss.
- Tunneling: CCD on fast RigidBodies, thicker static colliders, or tick rate 120/180/240.
- Physics is non-deterministic: no lockstep sims on it; tests use tolerances.

## CharacterBody loop (2D; 3D is identical with Vector3 and camera-relative input)
```gdscript
extends CharacterBody2D

@export_range(0.0, 1000.0) var speed: float = 300.0
@export_range(0.0, 2000.0) var jump_velocity: float = 600.0
@export_range(0.0, 30.0) var acceleration: float = 12.0


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity += get_gravity() * delta
	if Input.is_action_just_pressed(&"jump") and is_on_floor():
		velocity.y = -jump_velocity
	var direction := Input.get_axis(&"move_left", &"move_right")
	velocity.x = lerpf(velocity.x, direction * speed, 1.0 - exp(-acceleration * delta))
	move_and_slide()
```
- `velocity` is units/second; never multiply it by `delta` before `move_and_slide()` (but do
  scale gravity/acceleration by `delta`). `move_and_collide(velocity * delta)` does need delta.
- Read `is_on_floor()/is_on_wall()` and `get_slide_collision(i)` after `move_and_slide()`.
- Top-down: `motion_mode = MOTION_MODE_FLOATING`. Defaults: `floor_max_angle` 45°,
  `max_slides` 4, `up_direction` up.
- `get_gravity()` respects Area gravity overrides; don't read the project gravity setting.
- 3D input: `Input.get_vector(&"move_left", &"move_right", &"move_forward", &"move_back")`,
  rotate by the camera's yaw (remove pitch) before applying.

## Physics interpolation (smooth motion at any refresh rate)
- Enable `physics/common/physics_interpolation` (off by default); move interpolated objects only
  in physics ticks (including tweens/animations on them).
- After spawning/teleporting: set the transform, then call `reset_physics_interpolation()`.
- 3D cameras: `top_level`, `physics_interpolation_mode = OFF`, update in `_process` from
  `target.get_global_transform_interpolated()` (Node3D only); mouse look applied per frame.
- Camera2D `process_callback` defaults to IDLE; without interpolation, use PHYSICS when it
  follows a physics body. GPU particles aren't interpolated in 2D (use CPUParticles2D or disable).
- Test interpolation temporarily at 10 ticks/s to expose jitter sources.

## Jolt (3D)
- Check `physics/3d/physics_engine` first. Jolt specifics: ray `face_index` is -1 unless enabled;
  joint soft limits unsupported; Area3D always detects static bodies; 4.7 flips
  WorldBoundaryShape3D `plane.d` sign. Remove a body from the tree before mass shape rebuilds.

## Troubleshooting
| Symptom | Fix |
|---|---|
| Jitter | Physics interpolation or camera in matching callback; don't move bodies in `_process` |
| Sliding down slopes / sticking to walls | `floor_stop_on_slope`, `floor_max_angle`, `wall_min_slide_angle`, `motion_mode` |
| No collision | layer/mask pair, shape is direct child, shape not disabled, body not scaled |
| Pass-through at speed | CCD, thicker colliders, higher tick rate |
| Tile bumps | TileMapLayer composite colliders (Physics Quadrant Size, 4.5+) |
| Spiral of death | fewer complex bodies, lower tick rate or `max_physics_steps_per_frame` |
