# Animation, tweens

## Choosing a tool
- AnimatedTexture: logic-free loops (also as TileSet tiles).
- AnimatedSprite2D + SpriteFrames: frame-based 2D only.
- AnimationPlayer: property/method/audio tracks, cut-out and skeletal animation.
- AnimationTree: blending, blend spaces, state machines — drives an AnimationPlayer, stores none.
- Tween: one-off procedural motion from code.

## AnimationPlayer
- Animations live in AnimationLibrary resources; address them as `"library/anim"` (`""` library
  = plain `"anim"`). Use `autoplay`, not `current_animation`, for start-up animation.
- Keep a `RESET` animation (keys at t=0): default pose and blend fallback.
- Don't put Node2D/Node3D under AnimationPlayer expecting transform inheritance (it's a plain
  Node). Animate a child pivot, not the node code also moves (tracks overwrite every frame).
- Looping animations never emit `animation_finished`; `queue()` after a loop never plays;
  `seek()` to the end doesn't emit. `play()` applies next frame → `advance(0)` for immediate pose.
- Animating physics bodies: `callback_mode_process = ANIMATION_CALLBACK_MODE_PROCESS_PHYSICS`
  (default IDLE); moving platforms use AnimatableBody with `sync_to_physics`.
- 3D: Position/Rotation/Scale 3D tracks; Bezier and property tracks can't blend together;
  method-track keys are `{"method": …, "args": […]}` and don't preview in the editor.
- Deprecated: `set_process_callback`/`ANIMATION_PROCESS_*` → `callback_mode_process`;
  `method_call_mode` → `callback_mode_method`; SpriteFrames `animation_loop` → `loop_mode`.

## AnimationTree
- Wrap the imported model in your own scene with the AnimationTree there. `active` defaults to
  true in 4.7.
- Control only through the tree once it drives a player
  (also valid: `tree[&"parameters/run/blend_amount"] = x`):

```gdscript
@onready var tree: AnimationTree = $AnimationTree
@onready var playback: AnimationNodeStateMachinePlayback = tree.get(&"parameters/playback")


func _physics_process(_delta: float) -> void:
	tree.set(&"parameters/locomotion/blend_position", velocity.length() / max_speed)
	if is_on_floor():
		playback.travel(&"run")
```
- A state machine must be started (autostart or `playback.start()`) before `travel()`.
  Advance Condition only checks for `true`; Advance Expression needs
  `advance_expression_base_node` and is case-sensitive.
- Never mutate AnimationNode resources at runtime (shared by every instance) — set parameters.
- BlendSpace: Discrete mode for 2D sprite frames; sync for locomotion (4.7: `sync_mode` enum).
- Root motion: feed `get_root_motion_position()` into velocity before `move_and_slide()`.
- Gameplay rules stay in code; AnimationTree reflects state, it doesn't own it.

## Tweens
- `var t := create_tween()` (bound to the node; dies with it). `Tween.new()` is invalid; tweens
  aren't reusable — `kill()` and recreate. Kill the previous tween before starting a new one on
  the same property.

```gdscript
func fade_out() -> void:
	var tween := create_tween().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tween.tween_property(self, ^"modulate:a", 0.0, 0.3)
	tween.parallel().tween_property(self, ^"scale", Vector2.ONE * 1.2, 0.3)
	tween.tween_callback(queue_free)
	await tween.finished
```
- Infinite `set_loops()` needs non-zero duration. `SceneTree.create_tween()` tweens aren't bound
  and outlive nodes. Tweening physics bodies with interpolation on: `set_process_mode(
  Tween.TWEEN_PROCESS_PHYSICS)`.

## Skeletons and cut-out
- 2D: Skeleton2D + Polygon2D weights; re-run Overwrite Rest Pose after editing bones; IK chains
  are editor-only — animate bones, not polygons.
- 3D retargeting: BoneMap + SkeletonProfileHumanoid; import humanoids in T-pose.
