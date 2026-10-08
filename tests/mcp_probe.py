#!/usr/bin/env python3
"""Minimal MCP stdio client: initialize, list tools, call one tool until it succeeds.

Usage: mcp_probe.py TOOL_NAME TIMEOUT_S -- COMMAND [ARGS...]
Prints one JSON summary line; exit 0 when the tool call returned a non-error result.
"""

from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import time


def main() -> int:
    sep = sys.argv.index("--")
    tool, timeout = sys.argv[1], float(sys.argv[2])
    cmd = sys.argv[sep + 1:]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    lines: queue.Queue[str] = queue.Queue()
    threading.Thread(target=lambda: [lines.put(l) for l in proc.stdout], daemon=True).start()
    deadline = time.time() + timeout
    next_id = 0

    def request(method: str, params: dict | None = None) -> dict:
        nonlocal next_id
        next_id += 1
        msg = {"jsonrpc": "2.0", "id": next_id, "method": method}
        if params is not None:
            msg["params"] = params
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()
        while time.time() < deadline:
            try:
                reply = json.loads(lines.get(timeout=1))
            except queue.Empty:
                if proc.poll() is not None:
                    raise RuntimeError(f"server exited {proc.returncode}")
                continue
            except ValueError:
                continue
            if reply.get("id") == next_id:
                return reply
        raise TimeoutError(method)

    summary: dict = {}
    try:
        init = request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                      "clientInfo": {"name": "godot-dev-probe", "version": "1"}})
        summary["server"] = init.get("result", {}).get("serverInfo")
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        proc.stdin.flush()
        tools = request("tools/list").get("result", {}).get("tools", [])
        summary["tool_count"] = len(tools)
        summary["has_tool"] = any(t.get("name") == tool for t in tools)
        result: dict = {}
        while time.time() < deadline:
            result = request("tools/call", {"name": tool, "arguments": {}}).get("result", {})
            if not result.get("isError"):
                break
            time.sleep(3)
        text = " ".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
        summary["call_ok"] = bool(result) and not result.get("isError")
        summary["call_excerpt"] = text[:600]
    except Exception as exc:  # report, then fail
        summary["error"] = repr(exc)
    finally:
        proc.terminate()
    print(json.dumps(summary))
    return 0 if summary.get("call_ok") else 1


if __name__ == "__main__":
    sys.exit(main())
