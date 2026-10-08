# Editor plugins and @tool scripts

## @tool
- `@tool` must be the first line; scripts it uses must be `@tool` too (non-tool scripts act empty
  in the editor; subclasses must repeat `@tool`).
- Guard game logic: `if Engine.is_editor_hint(): return` (or the inverse for editor-only code).
  `OS.has_feature("editor")` = editor build, not "running in editor".
- Write and test code first, then add `@tool`. Breakpoints are ignored in tool scripts — print.
- No tree surgery / `queue_free()` on user nodes from tool code without undo: use
  `EditorUndoRedoManager` (`create_action` → `add_do_method/add_undo_method` (+
  `add_do_reference` for created nodes) → `commit_action`).
- Nodes added from tool code need `owner = get_tree().edited_scene_root` (EditorScript:
  `EditorInterface.get_edited_scene_root()`) to be saved, then mark the scene unsaved.
- Export setters run in the editor only with `@tool`; call `notify_property_list_changed()` after
  changing exported structure; `update_configuration_warnings()` + `_get_configuration_warnings()`
  to self-document required children/exports.
- `@export_tool_button("Label", "Icon") var action := do_thing` for inspector buttons (tool only).
- Don't access editor singletons from game code (they don't exist in exports); if unavoidable,
  `Engine.get_singleton(&"EditorInterface")` guarded by `Engine.is_editor_hint()`.

## EditorPlugin
- Layout: `addons/<name>/plugin.cfg` (`name`, `description`, `author`, `version`, `script`) +
  `@tool extends EditorPlugin` script.
- Every registration in `_enter_tree` has a matching removal + free in `_exit_tree`:
  custom types, import/inspector/gizmo plugins, docks, tool menu items.
- Docks (4.7): `var dock := EditorDock.new()`, add your Control, `add_dock(dock)` /
  `remove_dock(dock)` + `queue_free()`. `add_control_to_dock`, `add_control_to_bottom_panel`,
  `get_editor_interface()` are deprecated → `EditorDock`, `EditorInterface` singleton.
- Autoloads and sub-plugins: register in `_enable_plugin`/`_disable_plugin`
  (`add_autoload_singleton`/`remove_autoload_singleton`), not in tree callbacks.
- Main screen: `_has_main_screen() -> true`, add the panel to
  `EditorInterface.get_editor_main_screen()`, `_make_visible(false)` initially,
  `_get_plugin_name()`, `_get_plugin_icon()`. Scale UI with `EditorInterface.get_editor_scale()`.
- Import plugin: `_get_importer_name`, `_get_recognized_extensions`, `_get_save_extension`,
  `_get_resource_type`, `_get_import_options` (always return an Array), `_get_preset_count`,
  `_import(...)` → `ResourceSaver.save(res, "%s.%s" % [save_path, _get_save_extension()])`;
  validate input files (never trust them).
- Inspector plugin: `_can_handle`, `_parse_property` returning true replaces the default editor;
  custom EditorProperty uses `_update_property` + `emit_changed`.
- Custom node types: `class_name` + `@icon("res://…svg")` (preferred over `add_custom_type`).
- Reload after changes: disable/enable in Project Settings → Plugins, or godot-ai
  `editor_reload_plugin` (drops the MCP session briefly).
