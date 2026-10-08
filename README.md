# godot-dev

A Claude Code plugin for building games in Godot 4.7.

It adds three things. There is one skill that Claude loads when you work on a Godot project; it
routes each task to a short reference file instead of pulling a whole rulebook into context. There
are a few scripts that check Claude's work against the Godot binary you actually have installed.
And it wires up the [godot-ai](https://github.com/hi-godot/godot-ai) MCP server, installing its
editor add-on into a project the first time you open a Claude session there.

Agents writing Godot code tend to repeat the same mistakes: Godot 3 syntax, untyped GDScript,
scenes that load but break when instantiated, and "it works" claims with no run behind them.
Most of what the plugin does is make those mistakes visible before they reach you.

## Requirements

- Claude Code with plugin support
- Godot 4.7 or newer, found through `godot` on your PATH, the `GODOT` environment variable, or
  `/Applications/Godot*.app` on macOS
- Python 3.9 or newer, or [uv](https://docs.astral.sh/uv/) (the godot-ai server itself needs uv)
- git, for the change-set check

## Install

Add this repository as a plugin marketplace, then install the plugin from it:

```bash
claude plugin marketplace add ItsYUGAMES/godot-dev
```

```bash
claude plugin install godot-dev@godot-dev
```

Inside a Claude Code session the same two steps are `/plugin marketplace add ItsYUGAMES/godot-dev`
and `/plugin install godot-dev@godot-dev`. Start a new session afterwards so the skill, hook and
MCP server load.

To try it without installing, clone the repo and point Claude Code at it for one session:

```bash
git clone https://github.com/ItsYUGAMES/godot-dev.git
```

```bash
claude --plugin-dir ./godot-dev
```

Update with `claude plugin update godot-dev@godot-dev`. Remove it with
`claude plugin uninstall godot-dev@godot-dev`.

## What happens in a Godot project

When a session starts, the hook looks for `project.godot` in the working directory or any parent.
Outside a Godot project it prints nothing and the bundled MCP server answers with zero tools, so
the plugin costs you nothing in other repositories.

Inside a project that targets Godot 4.7 or newer, and where `addons/godot_ai/` doesn't exist yet,
the hook downloads the godot-ai v4.3.0 release. Before anything touches your project it checks the
three release files against SHA-256 values pinned in this repo, then runs godot-ai's own verifier
over the RSA signature and the full file inventory. The add-on is extracted into a staging folder
and moved into place in one step. If no Godot editor is running, the hook also enables the add-on
in `project.godot`; if an editor is open, it leaves that file alone and tells you to enable the
plugin from Project Settings, because the editor would overwrite the change anyway.

The hook never overwrites or downgrades an add-on that is already there. It then prints at most
three lines: the engine version, what happened to the add-on, and the MCP status.

The MCP server runs `godot-ai attach` through uvx, pinned to the exact version in
`addons/godot_ai/plugin.cfg`. That matters because the editor refuses a backend whose version
differs from its add-on. Ports and excluded tool domains are read from your Godot editor
settings, and telemetry is off unless you opt in. If you already registered godot-ai yourself
(through the dock's Configure button, `claude mcp add`, or a project `.mcp.json`), the bundled
server stays inactive so you don't get 47 duplicate tools. It warns you if that existing entry
is pinned to a different version than the add-on.

Open the project in the Godot editor and the godot-ai tools can read and change the live editor.

## Using it

You don't call the skill directly. Ask for Godot work as you normally would ("add coyote time to
the player", "why does this scene crash when I instance it", "set up a save system") and Claude
loads the `godot` skill, reads the reference files the task needs, and runs the checks before it
reports back.

The checks live in `skills/godot/scripts/gd.py` and you can run them yourself from a clone:

```bash
python3 skills/godot/scripts/gd.py check --project /path/to/game --smoke
```

`check` runs `--import`, loads every script, instantiates every scene and, with `--smoke`, plays
the main scene headless for a few hundred frames. It doesn't use `--check-only`, which reports
false errors for code that references autoloads.

```bash
python3 skills/godot/scripts/gd.py api CharacterBody2D.move_and_slide Vector3.MODEL_FRONT
```

`api` looks names up in the engine you have installed and suggests the nearest real names when one
doesn't exist. `KinematicBody2D`, for example, comes back as missing with `StaticBody2D` and
`AnimatableBody2D` suggested.

```bash
python3 skills/godot/scripts/gd.py hygiene --project /path/to/game
```

`hygiene` reads your git diff plus untracked files and flags what usually gets left behind after
debugging: `print()` calls (they ship in release builds; only `assert()` is stripped),
`@warning_ignore` without a reason, commented-out code, TODOs with no owner, asserts with side
effects, tests that lost assertions or were deleted, probe scripts, and orphaned `.uid` files.

```bash
python3 skills/godot/scripts/gd.py release --project /path/to/game --preset "macOS"
```

`release` exports a pack with one of your presets, fails if test folders or test add-ons ended up
inside it, and boots the pack headless to catch runtime errors.

All four print a final `RESULT: PASS`, `RESULT: FAIL` or `RESULT: NOT ASSESSED` line. Only PASS
counts, because Godot itself often exits with code 0 after a script error.

## Context cost

Measured with `claude plugin details`:

| When | Cost |
|---|---|
| Every session | about 76 tokens (the skill description) |
| The skill is invoked | about 1.6k tokens for the router, plus whichever reference files the task needs (22 to 94 lines each) |
| Session start in a Godot project | about 120 tokens of hook output |
| godot-ai tools | deferred; schemas load only when Claude searches for them |

## Settings

Set these as environment variables before starting Claude Code:

| Variable | Effect |
|---|---|
| `GODOT_DEV_AUTO_INSTALL=0` | Never install or enable the add-on |
| `GODOT_DEV_MCP=0` | Keep the bundled MCP server inactive |
| `GODOT_DEV_MCP_FORCE=1` | Run the bundled server even if you have your own godot-ai entry |
| `GODOT_DEV_TELEMETRY=1` | Allow godot-ai telemetry |
| `GODOT_DEV_MCP_PORT`, `GODOT_DEV_MCP_WS_PORT`, `GODOT_DEV_EXCLUDE_DOMAINS` | Override the values read from editor settings |

Running `python3 scripts/godot_dev.py status` inside a project prints what the plugin detects.

## What's in the repository

```
.claude-plugin/        plugin and marketplace manifests
skills/godot/          SKILL.md (the router), 21 reference files, gd.py and its GDScript helpers
hooks/, scripts/       SessionStart hook, add-on installer, MCP launcher
scripts/vendor/        godot-ai's release verifier (MIT, pinned by hash)
docs/STANDARDS.md      the full rule set with sources and the engine checks behind it
tests/                 installer, launcher and gd.py tests, plus an end-to-end MCP test
evals/                 cases for `claude plugin eval`
```

The reference files cover the workflow, GDScript, cleanup before handover, architecture and
patterns, project setup, physics, 2D, 3D, animation, UI, input, saving and threads, audio,
navigation, multiplayer, shaders, performance, hand-editing `.tscn` files, testing and export,
godot-ai, and editor plugins.

## Where the rules come from

The rules were distilled from the Godot 4.7 documentation, the official demo projects, *Game
Programming Patterns*, a survey of the most-starred Godot agent skills and MCP servers, and
published studio practice on workflow, testing and code cleanup. Where sources disagreed, the
Godot binary decided: a disputed default or API was settled by running 4.7.stable and checking. As
one example, the docs say `move_and_slide` collides up to five times by default; the engine says
`max_slides` is 4. `docs/STANDARDS.md` lists each conflict and how it was resolved.

The skill was also tested by giving the same tasks to agents with and without it, on a strong
model. Without it, the model already avoided the obvious Godot 3 mistakes. With it, the code passed a strict typing
check more often, and the runs looked up engine APIs, wrote tests before fixing bugs, proved the
tests fail when the fix is reverted, and left clean repositories. It also cost roughly 25 percent
more tokens. Smaller models haven't been measured yet; the eval suite in `evals/` is there for that.

## Tests

```bash
bash tests/gd_tests.sh
```

```bash
bash tests/run_tests.sh /path/to/godot-ai-v4.3.0-release-files
```

```bash
bash tests/integration_godot_ai.sh /path/to/godot-ai-v4.3.0-release-files
```

The second and third scripts expect a folder holding the three godot-ai v4.3.0 release assets
(`godot-ai-v4-plugin.zip`, `.manifest.json`, `.manifest.sig`), so they don't hit the network on
every run. The end-to-end test starts a headless Godot editor with an isolated home directory and
separate ports, so it won't disturb a godot-ai backend you already have running.

```bash
claude plugin eval . --allow-tools Bash Write Edit --no-publish
```

## Troubleshooting

If the godot-ai tools are missing on the very first run, uv was probably still building the
server environment. The hook starts that build in the background; reconnect godot-ai from `/mcp`
a minute later.

If you see `PORT_OCCUPIED` or an HTTP 401 right after opening the editor, Claude and the editor
most likely started godot-ai at the same moment. Reconnecting from `/mcp` fixes it.

If the add-on was installed but isn't active, an editor was open during installation. Enable it
under Project, Project Settings, Plugins, Godot AI.

## Updating the pinned godot-ai version

Change `PIN_VERSION`, `PIN_TAG`, `PIN_COMMIT` and the three `PIN_ASSETS` digests in
`scripts/godot_dev.py`, hashing the downloaded release files yourself rather than trusting the
release page. Copy `release_verify.py` from the same tag into `scripts/vendor/`, update
`VERIFIER_SHA256`, and run the test scripts.

## License

MIT, see `LICENSE`. `scripts/vendor/release_verify.py` comes from
[godot-ai](https://github.com/hi-godot/godot-ai) and keeps its own MIT license in
`scripts/vendor/LICENSE-godot-ai`.
