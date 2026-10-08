extends SceneTree
## Headless project check run by godot_check.py: loads every script and
## instantiates every scene under res:// (addons/ skipped unless asked).
## Prints one `GODOT_CHECK <kind> <OK|FAIL> <path>` line per file.

var _include_addons := false
var _failures := 0


func _initialize() -> void:
	_include_addons = OS.get_cmdline_user_args().has("--include-addons")
	_walk("res://")
	print("GODOT_CHECK done failures=%d" % _failures)
	quit(1 if _failures > 0 else 0)


func _walk(dir_path: String) -> void:
	for sub: String in DirAccess.get_directories_at(dir_path):
		if sub.begins_with("."):
			continue
		if dir_path == "res://" and sub == "addons" and not _include_addons:
			continue
		_walk(dir_path.path_join(sub))
	for file: String in DirAccess.get_files_at(dir_path):
		var path := dir_path.path_join(file)
		match file.get_extension():
			"gd":
				_check_script(path)
			"tscn", "scn":
				_check_scene(path)


func _check_script(path: String) -> void:
	var script := ResourceLoader.load(path, "", ResourceLoader.CACHE_MODE_IGNORE) as GDScript
	var ok := script != null and (script.can_instantiate() or script.is_abstract())
	_report("script", ok, path)


func _check_scene(path: String) -> void:
	var packed := ResourceLoader.load(path) as PackedScene
	var ok := packed != null and packed.can_instantiate()
	if ok:
		var node := packed.instantiate()
		ok = node != null
		if node:
			node.free()
	_report("scene", ok, path)


func _report(kind: String, ok: bool, path: String) -> void:
	if not ok:
		_failures += 1
	print("GODOT_CHECK %s %s %s" % [kind, "OK" if ok else "FAIL", path])
