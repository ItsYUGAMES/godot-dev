---
type: llm
weight: 1
---

PASS only if the Vector2 position round-trips correctly (explicit conversion such as x/y fields,
`var_to_str`/`str_to_var`, `JSON.from_native`, ConfigFile, or `store_var` without objects — NOT
dumping a Vector2 into JSON and reading back a string), the unlocked levels come back as an
array of strings, and all declarations in save_system.gd are statically typed. FAIL otherwise.
