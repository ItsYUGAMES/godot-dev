---
type: llm
weight: 1
---

PASS only if project.godot registers the autoload correctly in Godot 4 syntax:
`[autoload]` section with `SaveSystem="*res://systems/save_system.gd"`, the file declares
`config_version=5`, and the agent ran a Godot verification command and reported its real
result. FAIL otherwise.
