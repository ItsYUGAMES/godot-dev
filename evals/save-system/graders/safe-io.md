---
type: llm
weight: 1
---

PASS only if all hold: saves go to a `user://` path (never `res://`); `FileAccess.open()` results
are null-checked or errors handled; parse failures of a corrupted file are handled without
crashing (e.g. checking `JSON.parse()` returns OK or validating the loaded type); no object
deserialization from the file (`get_var(true)`, `bytes_to_var_with_objects`, `allow_objects`, or
`ResourceLoader.load` on the save). FAIL otherwise.
