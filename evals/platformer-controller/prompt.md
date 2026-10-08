---
max_turns: 30
allowed_tools: [Read, Write, Edit, Glob, Grep, Skill, Bash]
---

Create a minimal Godot 4.7 project in the current directory (a `project.godot` with input
actions `move_left`, `move_right`, `jump`) and write `player/player.gd`: a 2D platformer player
for a CharacterBody2D with left/right movement, jump, coyote time and jump buffering, with the
feel values tunable from the inspector. Godot is installed at
/Applications/Godot.app/Contents/MacOS/Godot if you want to verify. Don't ask questions.
Finish by printing the full final contents of every file you wrote and saying how you verified it.
