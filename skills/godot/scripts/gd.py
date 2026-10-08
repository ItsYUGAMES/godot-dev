#!/usr/bin/env python3
"""Godot 4 verification gates for agents (stdlib only, Python 3.9+).

  gd.py check [--smoke [--scene res://x.tscn] [--frames 300]] [--no-import] [--include-addons]
      1. import  godot --headless --import   (rebuilds the class_name cache and .import files)
      2. check   load every .gd and instantiate every .tscn/.scn under res:// (autoload-aware;
                 `--check-only` is not used because it fails on valid autoload references)
      3. smoke   optional: run the main scene (or --scene) for N frames and fail on any error line
  gd.py api Class [Class.member ...]
      Look names up in the installed engine's ClassDB; MISSING lines suggest the closest names.
  gd.py hygiene [--base REV]
      Scan the change set (git diff vs REV, default HEAD, plus untracked files) for leftovers:
      debug prints, unexplained @warning_ignore, commented-out code, ownerless TODOs, side-effect
      asserts, weakened/deleted tests, scratch files, orphan .uid, tracked .godot/credentials.
  gd.py release --preset NAME [--frames 300] [--forbid PREFIX ...]
      Export a pack with the named preset, list its files (fail on test roots / test addons),
      then boot it headless with --main-pack and fail on error lines.

Every Godot call runs under a timeout (a fatal error can hang Godot on macOS). The verdict is
`RESULT: PASS|FAIL|NOT ASSESSED`; exit 0 only on PASS (Godot itself often exits 0 after errors).
Common options: --project DIR, --godot BIN (else $GODOT, PATH, /Applications/Godot*.app), --timeout S.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ERROR_RE = re.compile(r"^(SCRIPT ERROR|ERROR|Parse Error|USER ERROR)\b")
# Engine noise seen on valid projects with 4.7 headless runs.
NOISE = (
    'Parameter "singleton" is null. at: is_cmdline_mode',
    'Condition "!EditorSettings',
)


def find_project(start: str | None) -> Path:
    here = Path(start or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "project.godot").is_file():
            return candidate
    sys.exit("gd.py: no project.godot found (pass --project)")


def find_godot(explicit: str | None) -> str:
    for candidate in (explicit, os.environ.get("GODOT"), os.environ.get("GODOT4"),
                      shutil.which("godot"), shutil.which("godot4")):
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    apps = sorted(glob.glob("/Applications/Godot*.app/Contents/MacOS/Godot")
                  + glob.glob(os.path.expanduser("~/Applications/Godot*.app/Contents/MacOS/Godot")))
    if apps:
        return apps[-1]
    sys.exit("gd.py: Godot binary not found (set GODOT=/path/to/godot or pass --godot)")


def run(cmd: list[str], timeout: int) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL)
        return proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or b"") + (exc.stderr or b"")
        text = out.decode("utf-8", "replace") if isinstance(out, bytes) else out
        return 124, text + f"\nTIMEOUT after {timeout}s"


def error_lines(output: str, limit: int = 25) -> list[str]:
    seen: list[str] = []
    lines = output.splitlines()
    for i, line in enumerate(lines):
        if not ERROR_RE.search(line) or any(n in line for n in NOISE):
            continue
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        entry = f"{line.strip()} {nxt}".strip() if nxt.startswith("at:") else line.strip()
        if any(n in entry for n in NOISE) or entry in seen:
            continue
        seen.append(entry)
    return seen[:limit]


def step(name: str, code: int, errs: list[str], extra: str = "", ok: bool = True) -> bool:
    passed = ok and code == 0 and not errs
    print(f"[{name}] {'OK' if passed else 'FAIL'} (exit {code}{'; ' + extra if extra else ''})")
    for line in errs:
        print(f"  {line}")
    return passed


def cmd_check(args: argparse.Namespace) -> int:
    root = find_project(args.project)
    godot = find_godot(args.godot)
    base = [godot, "--headless", "--path", str(root)]
    version = run([godot, "--version"], 30)[1].strip().splitlines()
    print(f"godot {version[-1] if version else '?'} | project {root}")
    passed = True

    if not args.no_import:
        code, out = run(base + ["--import"], args.timeout)
        passed &= step("import", code, error_lines(out))

    cmd = base + ["--script", str(HERE / "check_project.gd")]
    if args.include_addons:
        cmd += ["--", "--include-addons"]
    code, out = run(cmd, args.timeout)
    rows = re.findall(r"^GODOT_CHECK (script|scene) (OK|FAIL) (.+)$", out, re.M)
    bad = [f"FAIL {kind} {path}" for kind, status, path in rows if status == "FAIL"]
    done = "GODOT_CHECK done" in out
    errs = bad + error_lines(out) + ([] if done else ["check did not finish (crash or timeout): NOT ASSESSED"])
    passed &= step("check", code, errs, f"{len(rows)} files, {len(bad)} failed", ok=done)

    not_assessed = False
    if args.smoke:
        project_text = (root / "project.godot").read_text(encoding="utf-8", errors="replace")
        if not args.scene and not re.search(r'^run/main_scene\s*=\s*"[^"]+"', project_text, re.M):
            # Without a main scene Godot waits instead of quitting; don't burn the timeout.
            print("[smoke] NOT ASSESSED (no run/main_scene; pass --scene res://…)")
            not_assessed = True
        else:
            cmd = base + ["--quit-after", str(args.frames)] + ([args.scene] if args.scene else [])
            code, out = run(cmd, args.timeout)
            target = args.scene or "main scene"
            passed &= step("smoke", code, error_lines(out), f"{args.frames} frames of {target}")

    if not passed:
        print("RESULT: FAIL")
        return 1
    if not_assessed:
        print("RESULT: NOT ASSESSED (requested checks did not all run; not a pass)")
        return 2
    print("RESULT: PASS")
    return 0


def cmd_api(args: argparse.Namespace) -> int:
    godot = find_godot(args.godot)
    with tempfile.TemporaryDirectory(prefix="gd-api-") as tmp:
        Path(tmp, "project.godot").write_text("config_version=5\n", encoding="utf-8")
        cmd = [godot, "--headless", "--path", tmp, "--script", str(HERE / "api_lookup.gd"), "--", *args.names]
        code, out = run(cmd, args.timeout)
    rows = [l for l in out.splitlines() if l.startswith(("FOUND ", "MISSING "))]
    print("\n".join(rows) if rows else out.strip()[-2000:])
    missing = sum(1 for l in rows if l.startswith("MISSING"))
    ok = code == 0 and missing == 0 and len(rows) == len(args.names)
    print("RESULT: PASS" if ok else "RESULT: FAIL")
    return 0 if ok else 1


TEST_ROOTS = ("test/", "tests/")
TEST_ADDONS = ("addons/gut/", "addons/gdUnit4/")
PRINT_RE = re.compile(r"\b(print|prints|printt|printraw|print_rich|print_debug|print_stack|print_tree|print_tree_pretty)\s*\(")
# Style guide: commented-out code is `#code` (no space); prose comments are `# text`.
COMMENTED_CODE_RE = re.compile(
    r"^\s*#(?![#\s])(var |const |func |if |elif |else:|for |while |return\b|extends |signal |await |"
    r"match |[A-Za-z_][\w.]*\s*(\(|=[^=]|\+=|-=)|\$\w)")
TODO_RE = re.compile(r"#.*\b(TODO|FIXME|HACK|XXX)\b(?!\s*[\(#\[])")
ASSERT_RE = re.compile(r"\bassert\s*\((.*)\)")
SAFE_CALL_RE = re.compile(
    r"\b(is_\w+|has_\w+|can_\w+|get_\w+|size|is_empty|len|typeof|abs\w*|min\w*|max\w*|"
    r"is_instance_valid|is_equal_approx|is_zero_approx|str|int|float|bool|find|count|begins_with|"
    r"ends_with|contains|keys|values|length|distance_to|dot|cross|normalized|clamp\w*)\s*\(")
SCRATCH_RE = re.compile(r"(^|/)(\.scratch/|_verify/|tmpclaude|scratch|probe|_probe|tmp_|debug_dump)", re.I)
REMOVED_ASSERT_RE = re.compile(r"\b(assert\w*|expect\w*|verify\w*)\s*\(")
SKIP_RE = re.compile(r"\b(pending|skip|skip_test|pass_test)\s*\(|@ignore|\.skip\(")


def git(root: Path, *args: str) -> tuple[int, str]:
    proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout


def added_lines(root: Path, base: str) -> dict[str, list[tuple[int, str]]]:
    """Map path -> [(line_no, text)] of lines added since base, untracked files included."""
    out: dict[str, list[tuple[int, str]]] = {}
    _code, diff = git(root, "diff", "-U0", "--no-color", base, "--", ".")
    path = None
    line_no = 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else None
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            line_no = int(m.group(1)) if m else 0
        elif raw.startswith("+") and path:
            out.setdefault(path, []).append((line_no, raw[1:]))
            line_no += 1
    _code, untracked = git(root, "ls-files", "--others", "--exclude-standard")
    for rel in untracked.splitlines():
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            out.setdefault(rel, [])
            continue
        out[rel] = list(enumerate(text.splitlines(), 1))
    return out


def removed_lines(root: Path, base: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    _code, diff = git(root, "diff", "-U0", "--no-color", base, "--", ".")
    path = None
    for raw in diff.splitlines():
        if raw.startswith("--- "):
            path = raw[6:] if raw.startswith("--- a/") else None
        elif raw.startswith("-") and not raw.startswith("---") and path:
            out.setdefault(path, []).append(raw[1:])
    return out


def cmd_hygiene(args: argparse.Namespace) -> int:
    root = find_project(args.project)
    code, top = git(root, "rev-parse", "--show-toplevel")
    fails: list[str] = []
    warns: list[str] = []
    if code != 0:
        print("[hygiene] NOT ASSESSED: not a git repository (diff-based checks need a baseline)")
        print("RESULT: NOT ASSESSED")
        return 2
    repo = Path(top.strip())
    prefix = str(root.relative_to(repo)) + "/" if root != repo else ""

    def rel(path: str) -> str:
        return path[len(prefix):] if prefix and path.startswith(prefix) else path

    added = added_lines(repo, args.base)
    for path, lines in sorted(added.items()):
        r = rel(path)
        if SCRATCH_RE.search(r):
            fails.append(f"scratch/probe file left behind: {r}")
        if not r.endswith(".gd"):
            continue
        in_tests = r.startswith(TEST_ROOTS)
        for no, text in lines:
            code_part = text.split("#", 1)[0]
            where = f"{r}:{no}"
            if not in_tests and PRINT_RE.search(code_part) and "hygiene: keep" not in text:
                fails.append(f"debug print added (ships in release): {where}: {text.strip()}")
            if "@warning_ignore" in text and "#" not in text.split("@warning_ignore", 1)[1]:
                fails.append(f"@warning_ignore without a reason comment: {where}")
            if COMMENTED_CODE_RE.match(text):
                warns.append(f"commented-out code added: {where}: {text.strip()}")
            if TODO_RE.search(text):
                warns.append(f"TODO/FIXME without owner or ticket (use TODO(name) / TODO #123): {where}")
            m = ASSERT_RE.search(code_part)
            if m:
                calls = re.findall(r"\b([A-Za-z_]\w*)\s*\(", m.group(1))
                risky = [c for c in calls if not SAFE_CALL_RE.match(c + "(")]
                if risky:
                    warns.append(f"assert() calls {', '.join(risky)} — stripped in release; keep side effects out: {where}")
    for path, lines in sorted(removed_lines(repo, args.base).items()):
        r = rel(path)
        if r.startswith(TEST_ROOTS) and any(REMOVED_ASSERT_RE.search(l) for l in lines):
            warns.append(f"assertions removed from a test (never weaken tests to get green; justify): {r}")
    for path, lines in sorted(added.items()):
        r = rel(path)
        if r.startswith(TEST_ROOTS) and any(SKIP_RE.search(t) for _n, t in lines):
            warns.append(f"test skipped/pending added (justify or remove): {r}")
    _c, deleted = git(repo, "diff", "--name-only", "--diff-filter=D", args.base, "--", ".")
    for path in deleted.splitlines():
        r = rel(path)
        if r.startswith(TEST_ROOTS) and r.endswith(".gd"):
            warns.append(f"test file deleted (only when its subject was removed in this change; say why): {r}")
    # Structural checks over the whole project.
    for uid in root.rglob("*.uid"):
        if ".godot" in uid.parts:
            continue
        if not uid.with_suffix("").exists():
            fails.append(f"orphan .uid (its script was deleted/moved): {uid.relative_to(root)}")
    _c, tracked = git(repo, "ls-files", "--", prefix + ".godot", prefix + "*export_credentials.cfg")
    for path in tracked.splitlines():
        fails.append(f"must not be tracked: {rel(path)}")
    presets = root / "export_presets.cfg"
    has_tests = any((root / t.rstrip("/")).is_dir() for t in TEST_ROOTS)
    if presets.is_file() and has_tests:
        for name, flt in re.findall(r'^name="([^"]*)"(?:.|\n)*?^exclude_filter="([^"]*)"',
                                    presets.read_text(encoding="utf-8"), re.M):
            missing = [t for t in TEST_ROOTS if (root / t.rstrip("/")).is_dir() and t + "*" not in flt]
            if missing:
                warns.append(f'export preset "{name}" does not exclude {", ".join(m + "*" for m in missing)}')
    print(f"[hygiene] base {args.base}: {len(added)} changed/untracked files scanned")
    for line in fails:
        print(f"  FAIL {line}")
    for line in warns:
        print(f"  WARN {line}")
    if fails:
        print("RESULT: FAIL")
        return 1
    print(f"RESULT: PASS ({len(warns)} warning(s) to review)" if warns else "RESULT: PASS")
    return 0


def cmd_release(args: argparse.Namespace) -> int:
    root = find_project(args.project)
    godot = find_godot(args.godot)
    forbid = tuple(args.forbid or (*TEST_ROOTS, *TEST_ADDONS))
    presets = root / "export_presets.cfg"
    if not presets.is_file() or f'name="{args.preset}"' not in presets.read_text(encoding="utf-8"):
        print(f'[release] NOT ASSESSED: no export preset named "{args.preset}" in export_presets.cfg')
        print("RESULT: NOT ASSESSED")
        return 2
    passed = True
    with tempfile.TemporaryDirectory(prefix="gd-release-") as tmp:
        pack = Path(tmp) / "release.pck"
        code, out = run([godot, "--headless", "--path", str(root), "--export-pack", args.preset, str(pack)],
                        args.timeout)
        exported = pack.is_file() and pack.stat().st_size > 0
        passed &= step("export", code, error_lines(out), f'preset "{args.preset}"', ok=exported)
        if not exported:
            print("RESULT: FAIL")
            return 1
        code, out = run([godot, "--headless", "--main-pack", str(pack), "--script", str(HERE / "list_pack.gd")],
                        args.timeout)
        files = re.findall(r"^PACKFILE res://(.+)$", out, re.M)
        leaked = sorted(f for f in files if f.startswith(forbid))
        passed &= step("contents", code, [f"should not ship: {f}" for f in leaked[:20]],
                       f"{len(files)} files", ok=bool(files))
        code, out = run([godot, "--headless", "--main-pack", str(pack), "--quit-after", str(args.frames)],
                        args.timeout)
        passed &= step("boot", code, error_lines(out), f"{args.frames} frames (editor binary, debug runtime)")
    print("RESULT: PASS" if passed else "RESULT: FAIL")
    return 0 if passed else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Godot 4 verification gates (see module docstring).")
    ap.add_argument("--godot")
    ap.add_argument("--timeout", type=int, default=300)
    sub = ap.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="import + load/instantiate everything (+ optional smoke run)")
    check.add_argument("--project")
    check.add_argument("--no-import", action="store_true")
    check.add_argument("--include-addons", action="store_true")
    check.add_argument("--smoke", action="store_true")
    check.add_argument("--scene", default="")
    check.add_argument("--frames", type=int, default=300)
    api = sub.add_parser("api", help="look up engine classes/members in ClassDB")
    api.add_argument("names", nargs="+")
    hyg = sub.add_parser("hygiene", help="scan the change set for debug leftovers and scratch files")
    hyg.add_argument("--project")
    hyg.add_argument("--base", default="HEAD")
    rel = sub.add_parser("release", help="export a pack, check its contents, boot it headless")
    rel.add_argument("--project")
    rel.add_argument("--preset", required=True)
    rel.add_argument("--frames", type=int, default=300)
    rel.add_argument("--forbid", nargs="*", help="path prefixes that must not ship (default: test roots, test addons)")
    args = ap.parse_args()
    commands = {"check": cmd_check, "api": cmd_api, "hygiene": cmd_hygiene, "release": cmd_release}
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
