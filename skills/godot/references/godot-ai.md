# godot-ai MCP (live editor control)

Tools appear as `mcp__plugin_godot-dev_godot-ai__*` (bundled) or `mcp__godot-ai__*` (your own
entry). Schemas are deferred: load with ToolSearch (`select:` the few you need), not all 47.
They need the project open in a Godot 4.7+ editor with the Godot AI add-on enabled; without it,
editor calls return `PLUGIN_DISCONNECTED`/`no_active_session` — ask the user to open the project,
don't hammer.

## Session start
- `editor_state` once: confirm the session's project path is this project, `readiness`,
  `current_scene`, `game_status`. Several editors open → `session_activate` / pass `session_id`
  (top level, never nested in `params`).
- `git commit` or confirm a clean tree first: editor writes bypass Claude's checkpoints, and
  `script_create/script_patch/write_text`/shader writes are `undoable:false`.

## Reading cheaply
- `scene_get_hierarchy(depth, offset, limit)` small and paged; `node_find(name|type|group,
  limit)` instead of full dumps; `node_get_properties(path, fields=[…])` always with fields;
  `script_manage(find_symbols)` for outlines instead of reading whole files;
  `api_manage(get_class)` (properties only by default; add `sections`).
- Logs: `logs_read(source=editor|game|plugin, count, since_cursor)`; `include_details=true` only
  when errors exist. Prefer `godot://…` resources for reads.

## Writing
- Node/scene/property tools edit the editor's in-memory scene: persist with `scene_save`.
  `project_run` autosaves by default (`autosave=false` for experiments).
- Edit open `.tscn`/`.tres` through tools, not raw file writes (the editor copy wins on save).
- Scripts: `script_patch(old_text, new_text)` with a unique anchor, or
  `script_create(overwrite=true)` for full rewrites; read each response's `diagnostics` and
  `reloaded`. A raw file edit + rescan does not prove the script parsed — run `GD check`.
- Multi-step scene edits: `batch_execute(commands=[{command: "create_node", params: …}, …],
  undo=true)` with plugin command names (`create_node`, `set_property`, `attach_script`,
  `delete_node`); rolls back on first error. Don't batch tests, plugin reloads, input sequences
  or filesystem moves.
- Project config: `input_map_manage(ensure_action/ensure_binding)` (idempotent), `autoload_manage`,
  `project_manage(settings_set)` — these persist to project.godot; confirm with the user first.
- Treat `new_errors_since_last_call` as a doorbell: finish the batch, then read logs.

## Running and verifying
- `project_run(mode, scene)` → poll `editor_state` until running → `game_manage`
  (`get_scene_tree`, `get_node_info`, `get_ui_elements`, `input_action`,
  `input_sequence` for frame-timed input) → `logs_read(source="game", include_details=true)` →
  `project_manage(op="stop")` before editing code again. Games started with F5 are not visible.
- Verify through state/logs/tests before screenshots. `editor_screenshot(source=viewport|
  viewport_2d|cinematic|game, max_resolution≤640)`; `game` only after `project_run` and
  `game_capture_ready`. Screenshots stay in context — take few.
- Tests: `test_run(suite, test_name, verbose=false)` for `res://tests/test_*.gd` extending
  `McpTestSuite` (synchronous `test_*`, each phase <20 s, run <300 s); `test_manage(results_get)`
  instead of re-running. `cache_warning` → restart the editor before trusting a rerun.
- Shaders: `material_manage` `shader_validate` before writing.

## Errors
- `EDITOR_NOT_READY` (importing, playing, testing): back off, retry.
- `DEFERRED_TIMEOUT` on script writes: read the file before retrying.
- `TRANSPORT_OUTCOME_UNKNOWN`: verify state; never blindly replay.
- `editor_reload_plugin` drops the session (~20–30 s): retry once, then `session_manage(list)`.
- Tool returned success but nothing changed? Re-read the state — never trust a success flag alone.
- Tools missing / `PORT_OCCUPIED` / HTTP 401 right after the editor and Claude started at the same
  moment (or on the very first run while uv builds the environment): ask the user to reconnect
  godot-ai in `/mcp`.

## Ask the user first
`filesystem_manage(remove)` (esp. `permanent=true`), `editor_manage(quit)`,
`editor_manage(game_eval)` (runs arbitrary code), `client_manage(configure/remove)` (rewrites MCP
client configs), settings/autoload writes.

## Plugin behavior (godot-dev)
- SessionStart installs the pinned, signature-verified add-on into `addons/godot_ai/` when absent
  and enables it (editor closed). `GODOT_DEV_AUTO_INSTALL=0` disables; `GODOT_DEV_MCP=0` keeps
  the bundled server inactive.
- If you already configured godot-ai (dock "Configure"), the bundled server stays inactive to
  avoid duplicate tools; its pin must equal the add-on version or the editor rejects the backend.
- Bundled launcher pins `godot-ai==<addons/godot_ai/plugin.cfg version>`, reads ports/excluded
  domains from editor settings, and disables telemetry unless opted in.
