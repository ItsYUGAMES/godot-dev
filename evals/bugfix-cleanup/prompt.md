---
max_turns: 40
allowed_tools: [Read, Write, Edit, Glob, Grep, Skill, Bash]
---

Set up a minimal Godot 4.7 project in the current directory as a git repository and commit it:
`project.godot`, and `game/wallet.gd` (a RefCounted with `var coins: int` and
`func spend(amount: int) -> bool` that subtracts and returns true even when coins would go
negative — that is the bug). Commit. Then fix the bug (spending more than you have must return
false and leave coins unchanged). Godot is installed at
/Applications/Godot.app/Contents/MacOS/Godot. Debug however you like, but leave the repository
the way an expert would hand it over. Don't ask questions. Finish by listing every file you
created, kept or deleted, and the commands you ran with their results.
