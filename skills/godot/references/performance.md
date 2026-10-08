# Performance

## Method
1. Set a budget in milliseconds per target (16.66 ms @ 60 fps, 33.33 ms @ 30 fps; mobile 30 fps
   ≈ 21–22 ms for thermal headroom). Measure on target hardware, not only in the editor.
2. Baseline before the change; decide CPU- vs GPU-bound (frame time = the slower one; disable
   V-Sync and compare small vs large window for fill-rate).
3. Fix the biggest measured bottleneck; re-profile. Never optimize blind; optimized code is rigid.

## Tools
- Debugger → Profiler (off by default, no C#; Self vs Inclusive), Visual Profiler (CPU/GPU passes;
  not on Compatibility), Monitors, ObjectDB snapshot diff (4.6+) for leaks/orphan nodes.
- `Performance.add_custom_monitor(&"game/enemies", func() -> int: return enemies.size())`.
- Micro-timing: `Time.get_ticks_usec()` averaged over ≥1000 runs. CLI: `--print-fps`,
  `--benchmark`, `--frame-delay` (simulate slow CPU). External: Tracy/Perfetto/Instruments (4.6+).

## CPU (scripts, nodes)
- Every processing node costs per frame: disable idle ones (`set_process(false)`,
  `process_mode = PROCESS_MODE_DISABLED`, VisibleOnScreenEnabler2D/3D); detach rarely used
  subtrees with `remove_child` (keep the reference) instead of hiding.
- Prefer signals/timers over polling; cache node refs (`@onready`, `%Unique`); no `get_node`/
  `find_child`/`load()` in hot paths; StringName literals for hot comparisons.
- Static typing speeds up GDScript; Packed*Array for large homogeneous data.
- Thousands of identical objects: MultiMesh, or servers (RenderingServer/PhysicsServer) with RIDs
  (keep a script reference to resources passed as RIDs; avoid server getters every frame).
- Pooling: not by default in GDScript (no GC); only for profiled spawn spikes; reset fully.
- Heavy work: WorkerThreadPool / threads (see `data-io.md`); spread procedural generation across
  frames (e.g. one chunk per frame).

## GPU (rendering)
- Fewer unique materials, then fewer unique shaders (StandardMaterial3Ds with identical feature
  toggles share a shader). Reuse materials; don't duplicate per instance (use instance uniforms).
- Avoid large/overlapping transparent surfaces; isolate small transparent parts on their own
  surface. Shadows off on small/distant lights; bake static lighting.
- LOD, visibility ranges (HLOD), occlusion culling; automatic instancing is Forward+ only for
  opaque/alpha-scissor materials.
- 2D: texture atlases, avoid huge transparent sprites (MeshInstance2D), fewer lights.
- Mobile: avoid dense vertices in small screen areas; no VRAM compression on pixel art.

## Stutter
- Shader/pipeline compilation (Forward+/Mobile 4.4+ ubershaders): load meshes/shaders at load time;
  show a warm-up scene that uses every rendering feature (MSAA, SSAO, GI, shadow modes) and every
  spawnable effect once (hidden instance under the camera); don't toggle those features mid-play;
  enable Shader Baker on export presets (4.5+, not Compatibility/Web).
- Compatibility: pre-warm by drawing each mesh/effect for one frame.
- Loading hitches: `ResourceLoader.load_threaded_request` behind a loading screen; preload at
  checkpoints, never `load()` during combat.
- Jitter vs stutter: jitter = tick/refresh mismatch → physics interpolation; stutter = frame
  spikes → profile.

## Input latency
- Swapchain image count 2 (Forward+/Mobile), higher physics tick rate, `Input.use_accumulated_input
  = false` for raw input, cap FPS slightly below VRR refresh.

## Evidence format
Report: scenario, target, budget, before/after frame ms (avg + worst), what changed, profiler
screenshot or monitor numbers. "Feels faster" is not evidence.
