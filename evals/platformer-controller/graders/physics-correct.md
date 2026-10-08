---
type: llm
weight: 1
---

PASS only if all hold: movement happens in `_physics_process`; gravity is applied scaled by
delta (e.g. `velocity += get_gravity() * delta`); `velocity` is NOT multiplied by delta before
`move_and_slide()`; coyote and buffer timers count down by delta (or frames) and are consumed
correctly; input uses the InputMap actions (`move_left`/`move_right`/`jump`), not raw key codes.
FAIL otherwise.
