# Game programmer workflow (agent edition)

Studios ship through gates; agents fail by stopping when code "looks done". Every step below ends
in an artifact or a command result, never an assertion. Postmortems blame scope and process more
than code, so the gates and scope control matter more than any pattern.

## Per-feature loop (one feature/system per session)
| # | Step | Action | Exit evidence |
|---|---|---|---|
| 0 | Orient (once per project) | Engine version, renderer, physics engine, test framework + test root, formatter config, warning levels, VCS/LFS state, `.uid` policy, project phase (prototype / production / live); build the verification harness if absent | `GD check` PASS on the current tree |
| 1 | Classify | One-sentence diff → go to 7. Touches scenes, input map, autoloads, project settings or >1 system → continue | Classification stated |
| 2 | Feature card | Fill the template below | Card in the plan / PR text |
| 3 | Tech note | Scenes, scripts, resources, signals touched; risks; perf impact; test plan | ≤1 page; each risk has a spike or mitigation |
| 4 | Spike / greybox | Answer the riskiest unknown in a throwaway scene (placeholder shapes OK); delete it after | Go / no-go recorded |
| 5 | Checkpoint | `git commit` or confirm clean tree before editor/MCP writes (checkpoints miss them) | Clean tree hash |
| 6 | Test first | Production/live: failing unit/scenario test, or a reproduction for bugs (red → green → revert-red → green). Prototype: throwaway probe, no permanent suite. Poll conditions, no fixed sleeps | Test fails for the right reason |
| 7 | Smallest slice | One system; typed GDScript; scenes via editor/MCP or rules in `scene-files.md`; feel values as `@export_range` | Diff limited to planned files |
| 8 | Gate | `GD check` after edits; `--smoke` for runtime paths; project tests; `GD hygiene` before handing back | Commands + `RESULT:` lines pasted |
| 9 | Runtime/visual | Drive the running game (godot-ai `game_manage`, scenario script); screenshot only for visual questions | State/log lines, image path |
| 10 | Perf (hot loops, rendering) | Profiler / `--print-fps` vs stored baseline in ms | Numbers vs budget |
| 11 | Review + integrate | Fresh-context review of diff *and data* against the card (correctness, scope); delete scaffolding (`hygiene.md`); small commit, cleanup of untouched code in its own commit | Commit hash; kept/deleted artifacts and open human items listed |
| 12 | Milestone gate | Run the project's exit criteria; milestone cleanup (`hygiene.md`); `GD release --preset …` | proceed / pivot / kill |

Tuning requests ("jump feels floaty"): change exported values, not architecture.

## Feature card template
```text
Feature: <name> | Engine: Godot 4.7 | System: <one system>
Behavior (input actions, never physical keys):
  Given <state>, when <action>, then <observable result>.
Tunables (@export_range default (min-max)): <name> <d> (<a>-<b>)
Agent-verifiable: <test path / scenario / state assertion / log line>
Visual: none | screenshot of <view> compared to <reference>
Allowed changes: <files>; scenes via editor/MCP
Out of scope: <list>
Done when: GD check PASS; tests pass; evidence pasted
Human-open: <feel/art/level-design judgement>
```

## Verification ladder (climb only as far as the change needs)
1. **Parse/load gate** — `GD check`: `--import` (rebuilds `class_name` cache), loads every script
   with autoloads registered, instantiates every scene. `--check-only` is NOT used: it fails valid
   autoload references.
2. **Logic tests** — GUT/GdUnit4 on RefCounted/Resource rule classes (damage, cooldowns, FSM,
   save round-trip). See `testing-export.md`.
3. **Scenario sim** — headless scene script with `--fixed-fps 60 --quit-after N`, seeded RNG,
   injected `InputEventAction` via `Input.parse_input_event()`, state printed as lines. Godot
   physics is not deterministic: assert with tolerances.
4. **Live runtime** — godot-ai: `project_run` → `game_manage` input/state reads → `logs_read`.
5. **Visual** — godot-ai `editor_screenshot` or a windowed run (headless has no renderer output).
6. **Feel** — human only; deliver a short playtest checklist and the tunables.

## Milestone gates (write project-specific exit criteria; don't assume definitions)
- Prototype: each throwaway answers one question (fun vs technical spike kept separate).
- Vertical slice: production-quality core loop on target hardware within budget.
- Alpha = feature freeze; Beta = content complete, no placeholders, zero known crashes;
  Release candidate = reproducible from a tag, export verified, no debug output.
- After alpha, new scope must displace existing scope.

## Guardrails (failure → rule)
- Godot 3/4 mix-ups → version from `project.godot`; `GD api` lookups; gate after each edit.
- Scene corruption / lost nodes → editor/MCP edits, `owner` set, re-instantiate to verify.
- "Compiles but plays wrong" → scenario or runtime check with state evidence, not a read-through.
- Sprawl / duplicated code → one system per session, out-of-scope list, small diffs.
- Self-certified feel → human-open checklist; never claim "feels good".
- Exit code 0 trusted → only parsed verdicts; `NOT ASSESSED` when a check could not run.

## Finish checklist
- [ ] `GD check` PASS (with `--smoke` if runtime code changed)
- [ ] Project tests run and pass (count > 0), or stated as absent
- [ ] Visual change? screenshot inspected; UI checked at two window sizes
- [ ] No Godot 3 APIs, no untyped declarations, no edits to `.godot/`/`.import`/`.uid`
- [ ] `GD hygiene` PASS: no investigation prints, scratch files, commented-out code or unexplained `@warning_ignore`; no test deleted/skipped/loosened to get green
- [ ] Release-relevant change: `GD release --preset …` PASS (tests don't ship, pack boots)
- [ ] Evidence pasted; temporary artifacts listed as deleted; kept artifacts justified; human-open items listed; nothing claimed that was not run
