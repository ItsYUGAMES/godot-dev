---
type: llm
weight: 1
---

PASS only if the final repository contains no leftover debugging artifacts: no added `print(`
calls in game code, no probe/scratch scripts or scenes, no commented-out code, no
`@warning_ignore` without a reason, and the agent's report lists temporary artifacts it created and
deleted. FAIL otherwise.
