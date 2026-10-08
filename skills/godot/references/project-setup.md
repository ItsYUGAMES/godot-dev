# Project setup and settings

Change settings through the editor or godot-ai `project_manage(settings_set)` while the editor
is open (it rewrites `project.godot` on save). Hand-edit `project.godot` only with the editor
closed; the file omits defaults, so a missing key means "default".

## Day-one decisions
- **Engine**: Godot 4.7 (`config/features=PackedStringArray("4.7", …)`, `config_version=5`).
  Don't change major/minor mid-project without a VCS checkpoint and testing.
- **Language**: GDScript by default. C# needs the .NET editor, can't export to Web, isn't
  covered by the GDScript profiler, and needs rebuilds for new exports/signals. GDExtension only
  for proven hot loops or C/C++ libraries.
- **Renderer** (`rendering/renderer/rendering_method`): Forward+ for desktop 3D (default);
  Mobile for mobile and desktop VR; Compatibility for Web (only option), old hardware, standalone
  XR and most 2D. If targeting Compatibility also set `rendering_method.mobile`. Check feature
  support before using SSR/SDFGI/VoxelGI/volumetric fog/TAA (Forward+ only), decals/trails
  (not Compatibility), compute (not Compatibility).
- **Stretch** (default `disabled`):
  - HD 2D/3D: `display/window/stretch/mode="canvas_items"`, `aspect="expand"`, base
    1920×1080 (or 1280×720); anchor Controls.
  - Pixel art: `mode="viewport"`, `aspect="keep"`, `scale_mode="integer"`, base ~640×360, and
    `rendering/textures/canvas_textures/default_texture_filter=0` (Nearest).
- **Physics**: 3D projects created in 4.6+ write `physics/3d/physics_engine="Jolt Physics"`;
  an absent key means the engine default — set it explicitly for new 3D projects. Action games:
  `physics/common/physics_ticks_per_second=120` + `physics/common/physics_interpolation=true`
  (off by default), then `reset_physics_interpolation()` after teleports.
- **Warnings**: `debug/gdscript/warnings/untyped_declaration=1` (or 2 = error).
- **Input map**: snake_case actions (`move_left`, `jump`, `toggle_pause`), each bound to
  keyboard + gamepad button/axis; `_p1/_p2` suffixes for local multiplayer.
- **Layers**: name `layer_names/2d_physics/layer_N` / `3d_physics` (player, enemies, world,
  pickups) and use them consistently.

## Folders and files
- Feature-first: keep a feature's scene, script, assets together (`player/player.tscn`,
  `player/player.gd`, `player/sprites/`). Third-party code in `addons/<name>/`.
- snake_case file and folder names everywhere (exported PCK is case-sensitive; Windows/macOS
  aren't). C# files: PascalCase matching the class.
- `.gdignore` (empty file) excludes a folder from import; dot-prefixed paths never export.
- Non-resource files you load at runtime (`*.json`, `*.txt`, `*.csv`) must be added to the
  export preset's non-resource include filter.

## Version control
- Generate `.gitignore`/`.gitattributes` from Project → Version Control. Ignore `.godot/` and
  `*.translation`. Line endings LF (`* text=auto eol=lf`).
- Commit: `*.import`, `*.uid` sidecars (4.4+), `project.godot`, `export_presets.cfg`,
  `default_bus_layout.tres`, `*.unwrap_cache`, lightmap `.lmbake`.
- Never commit `.godot/export_credentials.cfg` (passwords, keys).
- Set up Git LFS before the first commit of binary assets (png, wav, ogg, glb, ttf, …).
- Moving a script outside the editor: move its `.uid` too, then re-save scenes that use it.
- 4.6 scene format adds `unique_id` per node and drops `load_steps`; run
  Project → Tools → Upgrade Project Files once after upgrading to avoid noisy diffs.

## Autoloads
- Few, PascalCase names, `*` (enabled) prefix in `project.godot`:
  `[autoload] SaveSystem="*res://systems/save_system.gd"`. See `architecture.md` for policy.

## Addons
- Install into `addons/<name>/` with `plugin.cfg` inside that folder; enable in
  Project Settings → Plugins (`[editor_plugins] enabled=PackedStringArray("res://addons/<name>/plugin.cfg")`).
- Pin addon versions to the engine minor version (GUT 9.7.x ↔ 4.7).

## New project skeleton
```
project.godot   main.tscn/main.gd   player/   enemies/   levels/   ui/   systems/   tests/   addons/
```
Main scene: `application/run/main_scene="res://main.tscn"`. Create `tests/` from day one; run
`GD check` once the skeleton exists.
