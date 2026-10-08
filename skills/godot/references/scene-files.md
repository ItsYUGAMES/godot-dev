# Hand-editing .tscn / .tres (text format 3/4)

Prefer the editor or godot-ai (`node_create`, `node_set_property`, `batch_execute`,
`scene_save`) — especially when the editor has the scene open: its in-memory copy overwrites
your file on save. Hand-edit only closed scenes, keep edits small, then run `GD check`
(it instantiates every scene; `load()` alone accepts broken hierarchies).

## Structure (order matters)
```
[gd_scene format=3 uid="uid://b7x…"]                 ; format=4 when it holds base64 data (TileMapLayer)

[ext_resource type="Script" uid="uid://c1…" path="res://player/player.gd" id="1_abcde"]
[ext_resource type="PackedScene" path="res://fx/dust.tscn" id="2_fghij"]

[sub_resource type="CircleShape2D" id="CircleShape2D_k3m4n"]
radius = 12.0

[node name="Player" type="CharacterBody2D" unique_id=1823745]
script = ExtResource("1_abcde")
speed = 320.0

[node name="Shape" type="CollisionShape2D" parent="."]
shape = SubResource("CircleShape2D_k3m4n")

[node name="Dust" parent="." instance=ExtResource("2_fghij")]

[node name="Hand" type="Marker2D" parent="Arm"]

[connection signal="body_entered" from="Hitbox" to="." method="_on_hitbox_body_entered"]
```
- Order: header → `ext_resource` → `sub_resource` → `node` → `connection` (→ `editable`).
- `format=2` and `load_steps=` are Godot 3/old: never write `format=2`; omit `load_steps` (4.6+).
- IDs are strings, unique per kind; reference as `ExtResource("id")`/`SubResource("id")`
  (never integers like `ExtResource( 1 )`). Declare a sub_resource before anything uses it.
- Exactly one root node without `parent`. Direct children: `parent="."`; deeper:
  `parent="Arm/Hand"` (path excludes the root's name). Instanced scenes: `instance=ExtResource(…)`
  and no `type`.
- `unique_id` (4.6+) is optional: when adding nodes, omit it or use a new unique integer; never
  duplicate one. `uid=` on ext_resources is optional; never invent or change a `uid://`.
- Node-typed exports store paths with `node_paths=PackedStringArray("target")` on the node line.
- Properties at default values are dropped on save; `;` comments don't survive.
- `.tres`: `[gd_resource type="Theme" format=3 uid=…]` → resources → `[resource]` section.
- AnimationPlayer: `libraries = {&"": SubResource("AnimationLibrary_x")}`.

## Safe vs unsafe
- Safe: property values; new nodes with fresh ids; new sub_resources; groups
  (`groups=["enemies"]`); connections; swapping a script/scene ext_resource path that exists.
- Unsafe (use the editor/godot-ai): base64 / `PackedByteArray` blocks (TileMapLayer
  `tile_map_data`, meshes), imported scenes (`.glb`-generated) and `.escn`, changing `uid`s,
  removing ext_resources still referenced, renaming nodes that other scenes/animations/paths
  reference, files currently open in the editor, `.import` and `.uid` files.

## Code-built scenes (tools, generators)
- After `add_child(node)`, set `node.owner = scene_root` for every node to be saved — but don't
  recurse into instanced child scenes (their internals belong to their own file).
- `PackedScene.pack(root)` then `ResourceSaver.save(packed, path)`; verify by instantiating the
  saved file and comparing node counts.
