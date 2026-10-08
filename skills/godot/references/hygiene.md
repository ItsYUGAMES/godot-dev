# Finish hygiene: keep, strip, delete

What lasts in game code is mostly answers, invariants, tunable data, regression tests and
why-comments. Scaffolding that produced them is deleted before handing work back. Godot strips
only `assert()` from release exports — every other keep-or-strip decision is a written rule.

## Keep / strip / delete
| Keep in the repo | Keep in source, inactive in release | Delete before finishing |
|---|---|---|
| Invariant asserts (side-effect free) | Debug overlays, cheats, consoles behind `OS.is_debug_build()` or a custom feature tag | Investigation `print`/`print_debug`/`print_stack` |
| One regression test per fixed bug | `@tool` code behind `Engine.is_editor_hint()` | Scratch/probe scripts and scenes (+ their `.uid`/`.import`) |
| Tunables as `@export_range`/Resource fields | `print_verbose()` trace logging | Commented-out code (git keeps history) |
| Why-comments, `##` docs on public API, `TODO(owner)` | Test roots and test addons (export `exclude_filter`) | Temporary main-scene / input-map / autoload edits |
| Determinism/save-compat checks, smoke tests | Kill switches you mean to keep | Code + tests of features removed in this change; expired release toggles |
| Verdicts of prototypes/spikes (in the plan or PR text) | — | Prototype gameplay code (archive the branch, never merge) |

## Godot mechanics
- Only `assert()` disappears in release; it isn't even evaluated — never put side effects in it
  (do the call, store the result, assert on the variable).
- `print()`, `print_debug()`, `print_rich()` and `push_*()` all ship. An unguarded debug print is a
  release defect.
- Error tiers:
  - programmer invariant → `assert(cond, "msg")`;
  - designer/data/player error → `push_error()`/`push_warning()` + safe-default return;
  - scene misconfiguration → `_get_configuration_warnings()` in a `@tool` script;
  - opt-in trace → `print_verbose()`.
- `OS.is_debug_build()` is true in the editor and debug exports; custom feature tags apply only to
  exported runs (not the editor).
- `@warning_ignore("x")` only with a reason comment on the same line; fix the cause first.
- Keep tests out of releases with the preset's `exclude_filter="test/*, tests/*, addons/gut/*,
  addons/gdUnit4/*"` (recursive into subfolders, verified on 4.7). Not `.gdignore` (it makes
  scripts unloadable). Never exclude an addon that an autoload references (e.g. godot-ai's
  `_mcp_game_helper`) — the release boot breaks.
- Secrets: `.godot/export_credentials.cfg` is never committed; nothing in the client is secret.
- `.uid` sidecars: commit them; move/delete them with their script; re-save referencing scenes.

## Agent rules
- Scratch work lives outside `res://` (session scratchpad). If a probe must load project
  resources, use `res://.scratch/` (dot folders never export, add it to `.gitignore`) and delete
  it with its sidecars before finishing.
- Phase sets test policy:
  - prototype/greybox → verify with `GD check` and a throwaway probe, no permanent suites;
  - production/live → tests ship with every behavior change.
- Bug fix = red → green → revert the fix (test must fail again) → restore (green). Keep the test.
- Never delete, skip or loosen a test to get green. Delete a test only when its subject was
  removed by the requested change, and say so. Flaky test → report it with evidence; quarantine
  or deletion is the team's call.
- Type what you write or change; don't retrofit untouched code; follow the repo's formatter and
  test root (`test/` vs `tests/`) instead of introducing another.
- Changes to warning levels, export presets, autoloads or the input map need user approval.
- Cleanup of code you didn't change goes in a separate commit, never mixed with behavior changes.

## Finish gate
1. `GD hygiene` (git diff vs HEAD + untracked) → `RESULT: PASS`; review every WARN.
2. `GD check` (+ `--smoke` for runtime changes) → `RESULT: PASS`.
3. Release-relevant change and an export preset exists → `GD release --preset "<name>"`
   (exports a pack, fails if tests/test addons ship, boots it headless).
4. Report:
   - changed paths;
   - commands with verdicts;
   - temporary artifacts created and confirmed deleted;
   - artifacts kept and why;
   - what stays unverified (feel, performance, platform exports).

## Milestone cleanup (when the user asks for a release pass)
- **Alpha:** delete cut features and their tests, plus resolved experiment toggles. Do a first
  release-config export to catch debug-only code.
- **Beta:** exclude test levels and debug scenes; remove placeholders; keep perf baselines.
- **Release candidate:** no debug surface reachable in release, `GD release` green, symbols archived.
- **Live:** add a regression test per escaped bug; remove release toggles within one or two
  releases; keep kill switches.
