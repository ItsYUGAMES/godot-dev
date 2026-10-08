# Tests, headless CI, export

## The gate (`GD` = `python3 "<godot skill base directory>/scripts/gd.py"`)
- `GD check` — `--import`, then loads every `.gd` and instantiates every `.tscn` under `res://`
  (addons skipped; `--include-addons` to include) with autoloads registered.
- `GD check --smoke [--scene res://levels/level_1.tscn] [--frames 300]` — also runs the scene
  headless and fails on any `SCRIPT ERROR`/`ERROR` line (Godot exits 0 even then). Without a
  main scene and no `--scene`, smoke is `NOT ASSESSED` (exit 2) — never report that as a pass.
- `GD api Class Class.member …` — names in the installed engine; MISSING → use the suggestions.
- `GD hygiene [--base REV]` — scans your change set (git diff + untracked) for debug prints,
  unexplained `@warning_ignore`, commented-out code, ownerless TODOs, side-effect asserts,
  weakened/deleted tests, scratch files, orphan `.uid`, tracked `.godot/`; FAIL blocks, WARN needs
  a reason in the report. Not a git repo → `NOT ASSESSED`.
- `GD release --preset "<name>"` — exports a pack, fails if test roots/test addons ship, boots
  it headless (editor binary, debug runtime; release-template-only behavior isn't covered).
- Every call has a timeout; only `RESULT: PASS` is a pass. Headless has no renderer output:
  visual checks need godot-ai `editor_screenshot` or a windowed run.

## Unit and scenario tests
- No built-in game test runner (the engine's doctest suite is for engine C++). Pick one:
  - **GUT 9.7.x** (Godot 4.7): `godot --headless -d -s --path . addons/gut/gut_cmdln.gd
    -gdir=res://tests -ginclude_subdirs -gexit` → exit 0 pass / 1 fail; `-gjunit_xml_file=`.
    Options use `=`; omit `-gexit` and it never quits.
  - **GdUnit4 v6**: `GODOT_BIN=… ./addons/gdUnit4/runtest.sh -a res://tests -c` → 0 pass,
    100 failures, 101 warnings (decide policy); HTML/JUnit reports.
  - **godot-ai** `test_run`: `res://tests/test_*.gd` extending `McpTestSuite` (see `godot-ai.md`).
- Use the framework and test root the repo already has (`test/` is the GUT/GdUnit4 default;
  godot-ai's runner needs `tests/`); never split suites across both; don't install a framework
  without approval.
- Cost pyramid: many fast logic tests on RefCounted/Resource rule classes (≤0.1 s each), few
  golden-path scene tests on minimal purpose-built scenes, plus a boot/smoke check. Data checks
  (assets, Resources) are the cheapest first tests.
- Test shape: `test_<given>_<when>_<then>`, arrange-act-assert, one behavior per test; see it
  fail before trusting it; test behavior through public API, not internals; don't expose
  internals just for tests; assert invariants and contracts, not tuning constants (read tunables
  from exports instead of hard-coding them).
- Bugs: reproduce at the lowest tier that can express it → red → fix → green → revert the fix
  (must fail) → restore. The test stays as the regression test.
- Not automated: feel, balance, visual/audio quality, exploratory play — human checklist.
- Never weaken tests to get green (no deleting, skipping, loosening asserts, hard-coding); a
  flaky test is reported with evidence, not deleted. Delete a test only with its removed subject.
- Scenario tests: a SceneTree script or test scene run with `--fixed-fps 60 --quit-after N`;
  seed RNG (`seed(1)` / per-system RandomNumberGenerator); inject `InputEventAction` via
  `Input.parse_input_event()`; print state lines; count failures and `quit(1)` — a failed
  `assert()` in `_initialize()` hangs instead of failing.
- Poll for conditions with a frame budget; never fixed sleeps: GUT `wait_until(cond, max_wait)`
  (needs a literal `true`) / `wait_for_signal`, GdUnit4 awaits; drive frames at a fixed delta
  with GUT `simulate()` (timers don't fire inside it) or GdUnit4 `simulate_frames`. Free every
  node you create. Physics: assert with tolerances.

## Headless CLI facts
- Unknown CLI flags are silently ignored — double-check spelling.
- Fresh clone (no `.godot/`): run `--import` first or `class_name` types won't resolve.
- `--check-only` fails valid code that references autoloads; don't use it as the gate.
- Wrap every call in a timeout (macOS fatal-error dialogs hang headless runs); treat 124 as fail.
  `gd.py` does this itself; for raw calls macOS has no `timeout` — use `gtimeout` (coreutils) or
  `perl -e 'alarm shift; exec @ARGV' 120 godot …`.

## CI pipeline (GitHub Actions or similar)
1. `git lfs pull` 2. pin the exact engine + export templates (e.g. chickensoft-games/setup-godot
   with `4.7.x`) 3. optional lint: `gdformat --check . && gdlint .` (gdtoolkit 4.x; run gdformat
   only under VCS) 4. `godot --headless --path . --import` 5. gate/smoke 6. tests with JUnit output
7. export 8. verify the artifact exists and is non-empty 9. publish on tags only.

## Export
- Commit `export_presets.cfg`; never commit `.godot/export_credentials.cfg`; pass keystore/
  encryption secrets via env vars (`GODOT_ANDROID_KEYSTORE_RELEASE_*`, `GODOT_SCRIPT_ENCRYPTION_KEY`).
- `godot --headless --path . --export-release "Preset Name" build/game.x86_64` — needs an editor
  binary plus matching templates; preset names are exact; the output path is relative to the
  project and its directory must exist (`mkdir -p`). Also `--export-debug`, `--export-pack`.
- Add runtime-read non-resource files (`*.json, *.csv`) to the include filter; dot-prefixed files
  never export; case mismatches break PCK paths.
- Keep tests out of release presets: `exclude_filter="test/*, tests/*, addons/gut/*,
  addons/gdUnit4/*"` (matches subfolders; verified on 4.7) — not `.gdignore`. Don't exclude
  addons that autoloads reference. Check with `GD release --preset …`.
- Feature tags: `OS.has_feature("web")`, custom tags (e.g. `demo`) only apply in exported runs;
  `ProjectSettings.get_setting_with_override()` for overrides.
- Dedicated server: "Export as dedicated server" (strip visuals), run with `--headless`; detect
  via `OS.has_feature("dedicated_server")`.

## Platforms
- **Web**: Compatibility renderer only; C# can't export; single-threaded default — threaded
  builds need COOP/COEP headers; audio Sample mode (no bus effects); fullscreen/mouse capture
  only from input callbacks; `user://` is IndexedDB.
- **Android**: AAB for Play, release keystore, INTERNET permission for networking; v2 plugins;
  request permissions with `OS.request_permission`.
- **iOS/macOS**: sign and notarize; macOS app paths are randomized (don't rely on app-relative
  writes).
- **Mobile UI**: portrait 720×1280 / landscape 1280×720 base, safe areas, touch input.
- **XR**: Mobile renderer for desktop VR, Compatibility for standalone headsets; OpenXR enabled
  in settings; `get_viewport().use_xr = true`; V-Sync off; match physics ticks to refresh rate.
