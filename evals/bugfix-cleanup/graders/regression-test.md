---
type: llm
weight: 1
---

PASS only if the agent added a permanent regression test for the overspend case, showed it failing
before the fix (or failing again when the fix was reverted) and passing after, with real command
output. FAIL if no test was kept or its red/green evidence is missing.
