#!/usr/bin/env python3
"""godot-dev helper (stdlib only, Python 3.9+).

Subcommands:
  session-start   Godot project? -> install/enable the pinned godot-ai add-on if
                  absent, then print <=3 short context lines. Silent elsewhere.
  mcp             Replace this process with the godot-ai stdio bridge, or serve an
                  inactive (zero-tool) MCP stub when the bridge must not run.
  status          Print diagnostics as JSON (for humans and tests).

Environment knobs (all optional):
  GODOT_DEV_AUTO_INSTALL=0   never install or enable the add-on
  GODOT_DEV_MCP=0            keep the bundled MCP server inactive
  GODOT_DEV_MCP_FORCE=1      run the bundled server even if another godot-ai entry exists
  GODOT_DEV_TELEMETRY=1      do not pass --disable-telemetry
  GODOT_DEV_MCP_PORT / GODOT_DEV_MCP_WS_PORT / GODOT_DEV_EXCLUDE_DOMAINS
                             override what is read from the Godot editor settings
  GODOT_DEV_MCP_DRY_RUN=1    print the bridge argv as JSON instead of exec (tests)
  GODOT_DEV_RELEASE_BASE_URL alternate download location (hashes stay pinned)
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Pinned godot-ai release. Bump all fields together (see README "Updating godot-ai").
PIN_VERSION = "4.3.0"
PIN_TAG = "v4.3.0"
PIN_COMMIT = "b82b5c519b1b17228f70d8effce1626f391bd1dd"
PIN_ASSETS = {
    "godot-ai-v4-plugin.zip": "dbc3d16e1aa7a5f3ae8038a150bf4191162112f4329c79611aa6f656e3ca4e58",
    "godot-ai-v4-plugin.manifest.json": "fdb5e89a8df0b4677256e380efb7be6b696b86ca056911ff793dee04611a0f0c",
    "godot-ai-v4-plugin.manifest.sig": "cdd969ca0806888cc2126f82c413ae7b0714bd98faba00f1c7b75be16954288a",
}
VERIFIER_SHA256 = "1b8c60c01f907c90092752b596caedc92022b3fba235620ae8fe510fc487a09d"
MIN_GODOT = (4, 7)
PLUGIN_CFG_RES = "res://addons/godot_ai/plugin.cfg"

# Same resolver policy the godot-ai dock writes for uvx clients.
UVX_POLICY = [
    "--isolated", "--no-config", "--no-env-file", "--no-sources", "--no-build",
    "--index-strategy", "first-index", "--keyring-provider", "disabled",
    "--index", "https://pypi.org/simple", "--default-index", "https://pypi.org/simple",
    "--find-links", "https://pypi.org/simple/godot-ai/", "--link-mode", "copy",
]
EXCLUDABLE = set(
    "editor scene node project script resource api filesystem client signal autoload "
    "input_map game testing batch ui theme animation material particle camera audio "
    "tilemap tileset gridmap navigation csg custom".split()
)


def env_flag(name: str, default: str = "") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def env_off(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("0", "false", "no", "off")


def host() -> str:
    """Agent host, set by set_host in lib.sh from the host's hook/MCP config."""
    return os.environ.get("GODOT_DEV_HOST") or "claude"


def emit_context(text: str) -> None:
    """Print SessionStart context in the shape the host's hook runner reads."""
    if host() == "codex":
        print(text)
        return
    if host() == "cursor":
        out: dict = {"additional_context": text}
    elif host() == "copilot":
        out = {"additionalContext": text}
    else:  # Claude and Gemini
        out = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}
    print(json.dumps(out))


def data_dir() -> Path:
    base = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.join(
        os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "godot-dev"
    )
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------- project facts

def find_root(start: str | None = None) -> Path | None:
    here = Path(start or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "project.godot").is_file():
            return candidate
    return None


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def project_info(root: Path) -> dict:
    text = read_text(root / "project.godot")
    cfg = re.search(r"^config_version\s*=\s*(\d+)", text, re.M)
    feats = re.search(r'^config/features\s*=\s*PackedStringArray\(([^)]*)\)', text, re.M)
    version = None
    if feats:
        for item in re.findall(r'"([^"]*)"', feats.group(1)):
            if re.fullmatch(r"\d+\.\d+", item):
                version = item
                break
    return {
        "config_version": int(cfg.group(1)) if cfg else None,
        "godot": version,
        "addon_enabled": PLUGIN_CFG_RES in _editor_plugins_line(text),
    }


def version_tuple(value: str | None) -> tuple[int, ...]:
    if not value:
        return ()
    return tuple(int(x) for x in re.findall(r"\d+", value)[:3])


def addon_version(root: Path) -> str | None:
    cfg = root / "addons" / "godot_ai" / "plugin.cfg"
    if not (root / "addons" / "godot_ai").exists():
        return None
    match = re.search(r'^version\s*=\s*"([^"]+)"', read_text(cfg), re.M)
    return match.group(1).split("+")[0] if match else "unknown"


def _editor_plugins_line(text: str) -> str:
    section = re.search(r"^\[editor_plugins\]\s*$(.*?)(?=^\[|\Z)", text, re.M | re.S)
    if not section:
        return ""
    line = re.search(r"^enabled\s*=\s*PackedStringArray\((.*)\)\s*$", section.group(1), re.M)
    return line.group(1) if line else ""


def editor_running(root: Path) -> bool:
    """Conservative: any Godot editor process counts unless it names another path."""
    try:
        out = subprocess.run(["ps", "-axo", "command="], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return True
    for line in out.splitlines():
        exe = line.strip().split(" ")[0]
        name = os.path.basename(exe).lower()
        if not name.startswith("godot") or "godot-ai" in line or "godot_ai" in line or "godot-mcp" in line:
            continue
        path = re.search(r"--path\s+(\S+)", line)
        if path and Path(path.group(1)).resolve() != root:
            continue
        return True
    return False


# ---------------------------------------------------------------- install

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_verifier():
    path = HERE / "vendor" / "release_verify.py"
    if _sha256(path) != VERIFIER_SHA256:
        raise RuntimeError("vendored release_verify.py hash mismatch")
    spec = importlib.util.spec_from_file_location("godot_dev_release_verify", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def install_addon(root: Path) -> str:
    base = os.environ.get(
        "GODOT_DEV_RELEASE_BASE_URL",
        f"https://github.com/hi-godot/godot-ai/releases/download/{PIN_TAG}",
    ).rstrip("/")
    verifier = _load_verifier()
    addons = root / "addons"
    addons.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="godot-dev-") as tmp:
        files = {}
        for name, expected in PIN_ASSETS.items():
            target = Path(tmp) / name
            with urllib.request.urlopen(f"{base}/{name}", timeout=60) as response, target.open("wb") as out:
                shutil.copyfileobj(response, out)
            if _sha256(target) != expected:
                raise RuntimeError(f"{name}: SHA-256 differs from the pinned value")
            files[name] = target
        staging = addons / f".godot_dev_staging-{os.getpid()}"
        try:
            plugin, _digest, _manifest = verifier.stage_verified_release(
                files["godot-ai-v4-plugin.zip"],
                files["godot-ai-v4-plugin.manifest.json"],
                files["godot-ai-v4-plugin.manifest.sig"],
                ("hi-godot/godot-ai", "stable", PIN_TAG, PIN_VERSION, PIN_COMMIT),
                staging,
            )
            final = addons / "godot_ai"
            if final.exists():
                raise RuntimeError("addons/godot_ai appeared during install; left untouched")
            os.rename(plugin, final)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    return PIN_VERSION


def enable_addon(root: Path) -> None:
    path = root / "project.godot"
    text = read_text(path)
    if PLUGIN_CFG_RES in _editor_plugins_line(text):
        return
    entry = f'"{PLUGIN_CFG_RES}"'
    section = re.search(r"^\[editor_plugins\]\s*$", text, re.M)
    if section is None:
        text = text.rstrip("\n") + f"\n\n[editor_plugins]\n\nenabled=PackedStringArray({entry})\n"
    else:
        body_start = section.end()
        nxt = re.search(r"^\[", text[body_start:], re.M)
        body_end = body_start + nxt.start() if nxt else len(text)
        body = text[body_start:body_end]
        line = re.search(r"^enabled\s*=\s*PackedStringArray\((.*)\)\s*$", body, re.M)
        if line:
            inner = line.group(1).strip()
            new_inner = f"{inner}, {entry}" if inner else entry
            body = body[: line.start()] + f"enabled=PackedStringArray({new_inner})" + body[line.end():]
        else:
            body = f"\n\nenabled=PackedStringArray({entry})" + body
        text = text[:body_start] + body + text[body_end:]
    tmp = path.with_name(".project.godot.godot-dev.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


# ---------------------------------------------------------------- MCP config

def claude_config_path() -> Path:
    base = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(base) / ".claude.json" if base else Path.home() / ".claude.json"


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def codex_entry(path: Path) -> dict | None:
    """The [mcp_servers.godot-ai] table of a Codex config.toml, as {"args": [...]}."""
    # ponytail: regex instead of tomllib (3.11+); reads only the header and quoted args.
    match = re.search(r"""^\[mcp_servers\.(?:godot-ai|"godot-ai"|'godot-ai')\]\s*$(.*?)(?=^\[|\Z)""",
                      read_text(path), re.M | re.S)
    if not match:
        return None
    args = re.search(r"^args\s*=\s*\[(.*?)\]\s*$", match.group(1), re.M | re.S)  # args may hold "argv[1:]"
    return {"args": re.findall(r"""["']([^"']*)["']""", args.group(1)) if args else []}


# MCP config files of the JSON-configured hosts, as (scope, path relative to home or project root).
# Cursor: cursor.com/docs/context/mcp; Gemini: geminicli.com/docs/get-started/configuration;
# Copilot CLI: docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers
HOST_MCP_CONFIGS = {
    "cursor": [("user", ".cursor/mcp.json"), ("project", ".cursor/mcp.json")],
    "gemini": [("user", ".gemini/settings.json"), ("project", ".gemini/settings.json")],
    "copilot": [("user", ".copilot/mcp-config.json"), ("project", ".mcp.json"), ("project", ".github/mcp.json")],
}


def existing_entry(root: Path) -> tuple[str, dict] | None:
    """Another godot-ai MCP entry the user configured (dock Configure / claude mcp add)."""
    if host() in HOST_MCP_CONFIGS:
        for scope, rel in HOST_MCP_CONFIGS[host()]:
            data = _load_json((Path.home() if scope == "user" else root) / rel)
            servers = data.get("mcpServers", data)  # Copilot project files may omit the wrapper
            if isinstance(servers, dict) and isinstance(servers.get("godot-ai"), dict):
                return scope, servers["godot-ai"]
        return None
    if host() == "codex":
        home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
        for scope, path in (("user", home / "config.toml"), ("project", root / ".codex" / "config.toml")):
            entry = codex_entry(path)
            if entry is not None:
                return scope, entry
        return None
    config = _load_json(claude_config_path())
    servers = config.get("mcpServers") or {}
    if isinstance(servers, dict) and "godot-ai" in servers:
        return "user", servers["godot-ai"]
    dirs = {str(root)}
    if os.environ.get("CLAUDE_PROJECT_DIR"):
        dirs.add(str(Path(os.environ["CLAUDE_PROJECT_DIR"]).resolve()))
    for proj_dir, proj in (config.get("projects") or {}).items():
        if proj_dir in dirs and isinstance(proj, dict) and "godot-ai" in (proj.get("mcpServers") or {}):
            return "local", proj["mcpServers"]["godot-ai"]
    for d in dirs:
        servers = _load_json(Path(d) / ".mcp.json").get("mcpServers") or {}
        if isinstance(servers, dict) and "godot-ai" in servers:
            return "project", servers["godot-ai"]
    return None


def entry_pin(entry: dict) -> str | None:
    for arg in entry.get("args") or []:
        match = re.fullmatch(r"godot-ai==([\w.+-]+)", str(arg))
        if match:
            return match.group(1)
    return None


def editor_settings(godot: str | None) -> dict:
    home = Path.home()
    dirs = [
        home / "Library" / "Application Support" / "Godot",
        Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "godot",
    ]
    files = [f for d in dirs if d.is_dir() for f in d.glob("editor_settings-4*.tres")]
    if not files:
        return {}
    preferred = [f for f in files if godot and f.name == f"editor_settings-{godot}.tres"]
    chosen = preferred[0] if preferred else max(files, key=lambda f: f.stat().st_mtime)
    values = {}
    for key, raw in re.findall(r"^godot_ai/(\w+)\s*=\s*(.+)$", read_text(chosen), re.M):
        values[key] = raw.strip().strip('"')
    return values


def find_uvx() -> str | None:
    found = shutil.which("uvx")
    candidates = [found] if found else []
    candidates += [os.path.expanduser(p) for p in (
        "~/.local/bin/uvx", "~/.cargo/bin/uvx", "/opt/homebrew/bin/uvx", "/usr/local/bin/uvx")]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return os.path.abspath(candidate)
    return None


def bridge_plan(root: Path) -> dict:
    """Decide whether the bundled server runs, and with which argv."""
    info = project_info(root)
    if env_off("GODOT_DEV_MCP"):
        return {"active": False, "reason": "disabled by GODOT_DEV_MCP=0"}
    other = existing_entry(root)
    if other and not env_flag("GODOT_DEV_MCP_FORCE"):
        return {"active": False, "reason": f"using existing godot-ai entry ({other[0]} scope)",
                "other_scope": other[0], "other_pin": entry_pin(other[1])}
    uvx = find_uvx()
    if not uvx:
        return {"active": False, "reason": "uv/uvx not found (install uv: https://docs.astral.sh/uv/)"}
    settings = editor_settings(info["godot"])
    installed = addon_version(root)
    version = installed if installed and installed != "unknown" else PIN_VERSION
    port = os.environ.get("GODOT_DEV_MCP_PORT") or settings.get("http_port") or "8000"
    ws_port = os.environ.get("GODOT_DEV_MCP_WS_PORT") or settings.get("ws_port") or "9500"
    excluded = os.environ.get("GODOT_DEV_EXCLUDE_DOMAINS", settings.get("excluded_domains", ""))
    domains = sorted({d.strip() for d in excluded.split(",") if d.strip() in EXCLUDABLE})
    argv = [uvx, *UVX_POLICY, "--from", f"godot-ai=={version}", "godot-ai",
            "attach", "--port", str(port), "--ws-port", str(ws_port)]
    if domains:
        argv += ["--exclude-domains", ",".join(domains)]
    telemetry_opt_in = env_flag("GODOT_DEV_TELEMETRY") or settings.get("telemetry_enabled") == "true"
    if not telemetry_opt_in:
        argv.append("--disable-telemetry")
    return {"active": True, "argv": argv, "version": version, "port": port, "ws_port": ws_port}


def clean_env() -> dict:
    """Drop ambient uv resolution controls, as godot-ai does for its own spawns."""
    return {k: v for k, v in os.environ.items() if not k.startswith("UV_")}


def serve_stub() -> None:
    """Minimal MCP server with no tools and no instructions (zero context cost)."""
    for line in sys.stdin:
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if not isinstance(msg, dict) or "id" not in msg:
            continue
        method = msg.get("method")
        if method == "initialize":
            params = msg.get("params") or {}
            result = {"protocolVersion": params.get("protocolVersion", "2025-06-18"),
                      "capabilities": {}, "serverInfo": {"name": "godot-ai-inactive", "version": "0"}}
            reply = {"jsonrpc": "2.0", "id": msg["id"], "result": result}
        elif method == "tools/list":
            reply = {"jsonrpc": "2.0", "id": msg["id"], "result": {"tools": []}}
        elif method == "ping":
            reply = {"jsonrpc": "2.0", "id": msg["id"], "result": {}}
        else:
            reply = {"jsonrpc": "2.0", "id": msg["id"],
                     "error": {"code": -32601, "message": "godot-ai bundled server inactive"}}
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()


def prewarm(plan: dict) -> str:
    """Build the pinned uv environment in the background once per version."""
    marker = data_dir() / f"prewarmed-{plan['version']}"
    if marker.exists():
        return ""
    argv = [plan["argv"][0], *UVX_POLICY, "--from", f"godot-ai=={plan['version']}", "godot-ai", "--version"]
    log = (data_dir() / "prewarm.log").open("ab")
    script = 'if "$@"; then touch "$GODOT_DEV_MARKER"; fi'
    env = clean_env() | {"GODOT_DEV_MARKER": str(marker)}
    subprocess.Popen(["/bin/sh", "-c", script, "sh", *argv], stdout=log, stderr=log,
                     stdin=subprocess.DEVNULL, env=env, start_new_session=True)
    retry = "start a new Codex session" if host() == "codex" else "reconnect godot-ai in /mcp"
    return f" First run: building the godot-ai environment in the background; if its tools are missing, {retry} in ~1 min."


# ---------------------------------------------------------------- commands

def cmd_session_start() -> int:
    root = find_root()
    if root is None:
        return 0
    info = project_info(root)
    godot = info["godot"]
    lines = [f"Godot {godot or '?'} project detected (godot-dev plugin). "
             "Load the `godot` skill before any Godot work: GDScript, scenes, shaders, UI, tests, export, godot-ai MCP."]
    if (info["config_version"] or 0) < 5:
        lines.append("This looks like a Godot 3 project (config_version < 5): godot-ai and the Godot 4.7 rules do not apply as-is.")
        emit_context("\n".join(lines))
        return 0
    installed = addon_version(root)
    addon_line = ""
    if installed is None:
        if env_off("GODOT_DEV_AUTO_INSTALL"):
            addon_line = "godot-ai add-on: not installed (auto-install disabled by GODOT_DEV_AUTO_INSTALL=0)."
        elif version_tuple(godot) and version_tuple(godot) < MIN_GODOT:
            addon_line = f"godot-ai add-on: not installed (needs Godot {MIN_GODOT[0]}.{MIN_GODOT[1]}+, project targets {godot})."
        else:
            try:
                installed = install_addon(root)
                addon_line = f"godot-ai add-on: installed v{installed} (signature + hashes verified)."
            except Exception as exc:  # report, never break the session
                addon_line = f"godot-ai add-on: install failed ({exc}); retried next session."
    else:
        addon_line = f"godot-ai add-on: v{installed} present (left untouched)."
    if installed and not info["addon_enabled"] and not env_off("GODOT_DEV_AUTO_INSTALL"):
        if editor_running(root):
            addon_line += " Not enabled yet: a Godot editor is open; enable Project > Project Settings > Plugins > Godot AI."
        else:
            try:
                enable_addon(root)
                addon_line += " Enabled in project.godot."
            except OSError as exc:
                addon_line += f" Could not enable in project.godot ({exc})."
    lines.append(addon_line)
    plan = bridge_plan(root)
    if plan["active"]:
        mcp_line = f"godot-ai MCP: bundled server active (godot-ai=={plan['version']}, ports {plan['port']}/{plan['ws_port']}); open this project in the Godot editor to use it."
        mcp_line += prewarm(plan)
    else:
        mcp_line = f"godot-ai MCP: bundled server inactive, {plan['reason']}."
        pin = plan.get("other_pin")
        if pin and installed and installed != "unknown" and pin != installed:
            mcp_line += f" Its pin godot-ai=={pin} differs from add-on v{installed}; the editor rejects mismatched backends — update that entry (dock Configure) or set GODOT_DEV_MCP_FORCE=1."
    lines.append(mcp_line)
    emit_context("\n".join(lines))
    return 0


def cmd_mcp() -> int:
    root = find_root()
    plan = bridge_plan(root) if root else {"active": False, "reason": "not a Godot project"}
    if env_flag("GODOT_DEV_MCP_DRY_RUN"):
        print(json.dumps(plan))
        return 0
    if not plan["active"]:
        serve_stub()
        return 0
    os.chdir(root)
    os.execve(plan["argv"][0], plan["argv"], clean_env())
    return 1  # unreachable


def cmd_status() -> int:
    root = find_root()
    out: dict = {"root": str(root) if root else None, "pinned": PIN_VERSION}
    if root:
        out.update(project_info(root))
        out["addon"] = addon_version(root)
        out["editor_running"] = editor_running(root)
        out["bridge"] = bridge_plan(root)
    print(json.dumps(out, indent=2))
    return 0


def main(argv: list[str]) -> int:
    commands = {"session-start": cmd_session_start, "mcp": cmd_mcp, "status": cmd_status}
    if len(argv) != 2 or argv[1] not in commands:
        print(f"usage: {Path(argv[0]).name} {{{'|'.join(commands)}}}", file=sys.stderr)
        return 2
    return commands[argv[1]]()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
