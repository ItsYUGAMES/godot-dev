---
type: llm
weight: 1
---

PASS only if the agent verified the scene by actually instantiating/loading it with Godot (for
example a headless run that loads every scene, or opening it via a script) and reported the real
result. A plain `--check-only` parse of the script alone does not count as verifying the scene.
FAIL otherwise.
