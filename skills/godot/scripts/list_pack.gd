extends SceneTree
## Lists every file inside the mounted main pack (run by gd.py release with --main-pack).
## Exported scripts appear as `*.gdc` + `*.gd.remap`, scenes as `*.remap`.


func _initialize() -> void:
	_walk("res://")
	quit()


func _walk(dir_path: String) -> void:
	for file: String in DirAccess.get_files_at(dir_path):
		print("PACKFILE ", dir_path.path_join(file))
	for sub: String in DirAccess.get_directories_at(dir_path):
		_walk(dir_path.path_join(sub))
