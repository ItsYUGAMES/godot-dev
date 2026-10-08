---
type: llm
weight: 1
---

PASS only if the final player.gd uses Godot 4 APIs exclusively: `extends CharacterBody2D`,
the built-in `velocity` property with `move_and_slide()` called with no arguments, `@export`
annotations (never `export var`), and no Godot 3 constructs (KinematicBody2D, `yield`, `setget`,
`onready var` without @, `move_and_slide(velocity, ...)`). FAIL otherwise.
