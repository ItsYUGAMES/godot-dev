---
type: llm
weight: 1
---

PASS only if slime.tscn is valid Godot 4 text format: header `[gd_scene ... format=3 ...]`
(not format=2), string ids referenced as `ExtResource("...")`/`SubResource("...")` (not integer
ids like `ExtResource( 1 )`), the sub_resource declared before the node using it, exactly one
root node without a `parent` attribute, children with `parent="."`, and the script attached via
`script = ExtResource(...)`. FAIL otherwise.
