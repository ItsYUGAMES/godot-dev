---
type: llm
weight: 1
---

PASS only if every member variable, function parameter and function return type in player.gd is
statically typed (including `-> void` on `_physics_process` and other functions), and `:=` is
used only where the right-hand side makes the type obvious. FAIL if any declaration is untyped.
