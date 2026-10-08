---
type: llm
weight: 1
---

PASS only if the agent actually executed a Godot-based verification command (for example a
headless Godot run or a project check script) against the files it wrote, reported the real
result, and did not claim success beyond what the command showed. FAIL if it only read its own
code or claimed it works without running anything.
