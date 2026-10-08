# Save/load, files, resources, threads

## Paths
- `res://` = project (read-only in exports); `user://` = writable per-user data; `/` separator
  only; `path_join()`; `ProjectSettings.globalize_path()` for OS APIs. Set
  `application/config/use_custom_user_dir` for shipped games.
- Load project assets with `load()`/`preload()`/ResourceLoader — never FileAccess on `res://`
  source files (exports ship only imported data). `load()` takes absolute `res://`/`uid://` paths.
- `preload()` needs a constant path (PascalCase `const`); `load()` for dynamic/late assets.
  Never `load()` inside `_process` or mid-combat.

## Choosing a save format
| Data | Format |
|---|---|
| Settings, key remaps | ConfigFile (`user://settings.cfg`) — native Variant types, `save()` to persist |
| Game state from your own game | JSON (`JSON.stringify` / `JSON.new().parse()`), or `FileAccess.store_var(value)` without objects |
| Designer data in the project | Resource `.tres` with `class_name` + `@export` |
| Untrusted input (downloads, mods, shared saves) | JSON/ConfigFile values only — never `get_var(true)`, `bytes_to_var_with_objects`, `allow_object_decoding`, or `ResourceLoader.load()` on user files (can execute code) |

## Save/load rules
- Check every `FileAccess.open()` for null (`FileAccess.get_open_error()`); `WRITE` truncates;
  create parent dirs (`DirAccess.make_dir_recursive_absolute`). `store_*` returns bool (4.4+).
- JSON: check `parse()` returns OK before `.data` (`get_error_message()`, `get_error_line()`);
  numbers come back as float; convert Vector2/Color manually or use `var_to_str`/`str_to_var`
  or `JSON.from_native()/to_native()` (no objects). GDScript doesn't narrow on `is`: after
  `if v is float:` assign `var f: float = v` before `int(f)` (keeps UNSAFE_* warnings quiet).
- Don't loop on `eof_reached()`; loop while `get_position() < get_length()`.
- Write atomically for important saves: write `save.tmp`, then `DirAccess.rename_absolute`.
- Version your save schema (`{"version": 2, …}`) and migrate on load.
- Loading a world: clear existing persistent nodes first; instantiate parents before children.
  Enumerate savables with a group: `get_tree().get_nodes_in_group(&"persist")`.
- Web `user://` is IndexedDB (may not persist); mobile: save on `NOTIFICATION_APPLICATION_PAUSED`.

```gdscript
const SAVE_PATH := "user://save.json"

func save_game(state: Dictionary) -> Error:
	var file := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if file == null:
		return FileAccess.get_open_error()
	file.store_string(JSON.stringify(state))
	return OK

func load_game() -> Dictionary:
	if not FileAccess.file_exists(SAVE_PATH):
		return {}
	var json := JSON.new()
	if json.parse(FileAccess.get_file_as_string(SAVE_PATH)) != OK or json.data is not Dictionary:
		push_error("Bad save: %s" % json.get_error_message())
		return {}
	return json.data
```

## Resources at runtime
- Cached and shared: `duplicate()`/`resource_local_to_scene` before per-instance changes; 4.5+
  external sub-resources need `duplicate_deep(Resource.DEEP_DUPLICATE_ALL)`.
- `ResourceSaver.save(resource, path)` at runtime doesn't persist generated UIDs.
- Patches/DLC: `ProjectSettings.load_resource_pack()` from an autoload `_init()` before any
  preload; packs are code-execution vectors — only load trusted/signed ones.

## Background loading
```gdscript
ResourceLoader.load_threaded_request(path)
# each frame:
var progress: Array = []
var status := ResourceLoader.load_threaded_get_status(path, progress)
if status == ResourceLoader.THREAD_LOAD_LOADED:
	var scene := ResourceLoader.load_threaded_get(path) as PackedScene
```
`load_threaded_get()` blocks if not finished; poll first. Show progress from `progress[0]`.

## Threads
- Check the Thread-safe APIs page before using a class off the main thread. Never touch the
  active scene tree from a thread: build detached nodes, hand results back with
  `add_child.call_deferred(node)`/`call_deferred`.
- Every `Thread.start()` needs `wait_to_finish()` (also in `_exit_tree`). Mutex around shared
  data (resizing Arrays/Dictionaries needs a lock); Semaphore for worker wake-ups.
- `WorkerThreadPool.add_task()` for parallel chunks; wait on every task id; not for cheap work.
- One loader thread; never load/modify the same Resource from several threads; no GPU calls
  (texture creation, image reads) on workers.
- Signals emitted from a thread run handlers on that thread — defer UI/tree work.
