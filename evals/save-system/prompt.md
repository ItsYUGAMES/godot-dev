---
max_turns: 30
allowed_tools: [Read, Write, Edit, Glob, Grep, Skill, Bash]
---

In the current directory, create a minimal Godot 4.7 project (`project.godot`) and add a save
system: `systems/save_system.gd`, registered as an autoload named `SaveSystem`, that saves and
loads the player's position (Vector2), health (int) and unlocked level ids (array of strings),
and survives a corrupted or missing save file. Godot is installed at
/Applications/Godot.app/Contents/MacOS/Godot if you want to verify. Don't ask questions.
Finish by printing the full final contents of every file you wrote and saying how you verified it.
