---
type: llm
weight: 1
---

PASS only if slime.gd is statically typed Godot 4 GDScript that moves the body in
`_physics_process` with `velocity` + `move_and_slide()` (no arguments, velocity not multiplied by
delta), turns around using `is_on_wall()` or a raycast checked after movement, and exposes speed
as an `@export` value. FAIL otherwise.
