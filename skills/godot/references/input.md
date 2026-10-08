# Input

## Actions, not keys
- Define InputMap actions (snake_case verb_noun: `move_left`, `jump`, `interact`, `toggle_pause`),
  each with keyboard + gamepad button/axis; `_p1/_p2` suffixes for local multiplayer.
  Add via editor or godot-ai `input_map_manage(ensure_action/ensure_binding)` (idempotent).
- Query with StringNames: `Input.is_action_pressed(&"jump")`.
- Movement: `Input.get_vector(&"move_left", &"move_right", &"move_up", &"move_down")`
  (circular deadzone) or `Input.get_axis(&"move_left", &"move_right")`; triggers:
  `get_action_strength`.
- `ui_*` actions belong to UI focus navigation — not gameplay.

## Where to handle what
- Dispatch order: `_input` → `_gui_input` (Controls) → `_shortcut_input` → `_unhandled_key_input`
  → `_unhandled_input` → physics picking `_input_event`. Non-GUI callbacks run deepest node first.
- One-shot gameplay events (jump, interact, pause): `_unhandled_input(event)` with
  `event.is_action_pressed(&"jump")`; consume with `get_viewport().set_input_as_handled()`.
- Held state (movement, aim): poll `Input.*` in `_physics_process`. `Input` ignores
  `set_input_as_handled()`.
- `_input` only to intercept before GUI (debug keys, global capture).
- Type-check before reading subtype fields: `if event is InputEventMouseButton and event.pressed:`.
- Keys: `physical_keycode` for WASD-style layout-independent bindings, `keycode` for shortcuts,
  `key_label` for on-screen prompts. 4.7: mouse/keyboard `device` is
  `InputEvent.DEVICE_ID_MOUSE`/`DEVICE_ID_KEYBOARD`, not 0.

## Mouse
- Captured mouse (`Input.mouse_mode = Input.MOUSE_MODE_CAPTURED`): use `event.screen_relative`
  for look (position stays centered); apply look per frame, not in physics ticks.
- Custom cursor: `Input.set_custom_mouse_cursor()` (≤256 px; ≤128 on Web) beats a sprite cursor.
- Web: capture mouse / fullscreen only inside an input callback (user gesture).

## Controllers and touch
- Controllers don't send echo events; desktop uses SDL3 (4.5+). Guard LEDs/motion sensors with
  `has_joy_light()`/`has_joy_motion_sensors()`.
- Touch: track `InputEventScreenTouch/Drag` by `index`; emulate mouse from touch only if needed.

## Rebinding
- Toggle a capture state, read the next event in `_unhandled_input`, then
  `InputMap.action_erase_events(action)` + `InputMap.action_add_event(action, event)`.
- Remaps are not saved automatically: persist to `user://` (ConfigFile or `store_var` without
  objects) and re-apply at startup only for actions that still exist.

## Quit and focus
- Confirm-on-quit: `get_tree().set_auto_accept_quit(false)` and handle
  `NOTIFICATION_WM_CLOSE_REQUEST`; `get_tree().quit()` doesn't send it.
- Mobile: save on `NOTIFICATION_APPLICATION_PAUSED` (iOS gives ~5 s).

## Testing input
- Simulate actions in tests/scenarios: `Input.parse_input_event(ev)` with an `InputEventAction`
  (`ev.action = &"jump"; ev.pressed = true`) reaches `_input`; `Input.action_press()` only sets
  polled state — `is_action_pressed` is true at once but `is_action_just_pressed` only on the next
  physics tick, so step a frame before asserting. Release after a frame. godot-ai:
  `game_manage(input_sequence)` for timed input.
