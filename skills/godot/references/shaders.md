# Shaders, post-processing, compute

## Language essentials (Godot shading language, not raw GLSL)
- First line `shader_type spatial|canvas_item|particles|sky|fog;` then optional `render_mode`.
  Files `.gdshader`; shared code in `.gdshaderinc` via `#include "res://…"` (can't include a
  `.gdshader`).
- No implicit int→float/uint conversion: write `2.0`, `float(i)`, `1u`. Initialize locals (they
  start as garbage). Define functions above callers. Clamp runtime array indices. Compare floats
  with an epsilon.
- Varyings are assigned only in `vertex()`/`fragment()`. `light()` is skipped under vertex
  shading — accumulate with `DIFFUSE_LIGHT +=`; defining any `light()` in canvas_item replaces
  built-in 2D lighting.
- Uniform hints: `source_color` on color uniforms and albedo/color samplers only;
  `hint_range(0.0, 1.0)`; `hint_normal` for normal maps. `hint_albedo`/`hint_color` are Godot 3.
- Screen/depth access via uniforms (the `SCREEN_TEXTURE`/`DEPTH_TEXTURE` built-ins are gone):
  `uniform sampler2D screen_tex : hint_screen_texture, repeat_disable, filter_nearest;`
  then `textureLod(screen_tex, SCREEN_UV, 0.0)`; same for `hint_depth_texture`,
  `hint_normal_roughness_texture` (Forward+).
- canvas_item `COLOR` in `fragment()` already includes texture × modulate; use
  `texture(TEXTURE, UV)` for the raw texture.
- Writing `ALPHA` moves a spatial material to the transparent pipeline (sorting, no shadows,
  absent from screen/depth textures); `discard` defeats depth prepass. If you write `DEPTH`,
  write it in every branch.
- Per-renderer code: `#if CURRENT_RENDERER == RENDERER_COMPATIBILITY` (NDC z −1..1 there,
  0..1 elsewhere). Reverse-Z since 4.3: full-screen quads use `POSITION = vec4(VERTEX.xy, 1.0, 1.0);`.
- Toggle features with `#define`/`#if` instead of bool uniforms where possible.

## Parameters from code
- `material.set_shader_parameter(&"name", value)` — exact name and type, mismatches fail
  silently. It changes every user of that material: per-instance values use
  `instance uniform` + `set_instance_shader_parameter()` (scalars/vectors, ~16 per shader) or a
  duplicated material.
- `global uniform` must exist in Project Settings → Shader Globals; set with
  `RenderingServer.global_shader_parameter_set`; don't call the getter every frame.
- Materials using a ViewportTexture must be Local to Scene.

## Post-processing
- 2D: CanvasLayer + full-rect ColorRect with a canvas_item shader reading `hint_screen_texture`;
  overlapping screen readers need a BackBufferCopy between them.
- 3D: full-screen QuadMesh (size 2, flip faces) in front of the camera with
  `POSITION = vec4(VERTEX.xy, 1.0, 1.0)` and a large `extra_cull_margin`, or a CompositorEffect
  (Forward+/Mobile; render thread, mutex shared fields, free RIDs on predelete).
- The 3D screen texture is captured after opaques: transparents are missing.

## Compute (Forward+/Mobile only; RenderingDevice is null on Compatibility)
- GLSL file starting `#[compute]` + `#version 450`; `RDShaderFile.get_spirv()` →
  `shader_create_from_spirv` → `compute_pipeline_create`; dispatch groups `(n - 1) / 8 + 1` with
  a bounds check; pad push constants to 16 bytes; `free_rid()` every RID (shader frees
  dependents). Local device: `submit()` then `sync()` a few frames later.

## Style and verification
- Order: shader_type → render_mode → uniforms → consts → varyings → functions → vertex →
  fragment → light; snake_case; tabs; `0.5` not `.5`.
- `load()` accepts shaders with syntax errors and compilation is lazy: validate with godot-ai
  `material_manage(shader_validate)` or by rendering it (screenshot); headless runs don't render.
- Stutter: precompile by showing every material/effect once during loading (see performance.md).
