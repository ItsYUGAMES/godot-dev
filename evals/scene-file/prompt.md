---
max_turns: 30
allowed_tools: [Read, Write, Edit, Glob, Grep, Skill, Bash]
---

In the current directory, create a minimal Godot 4.7 project (`project.godot`) and, by writing
the text files directly, an enemy scene `enemies/slime.tscn`: root `Slime` (CharacterBody2D)
with a CollisionShape2D using a CircleShape2D of radius 10, a Sprite2D child, and the script
`enemies/slime.gd` attached to the root, which patrols left and right and turns around at walls.
Godot is installed at /Applications/Godot.app/Contents/MacOS/Godot if you want to verify.
Don't ask questions. Finish by printing the full final contents of every file you wrote and
saying how you verified it.
