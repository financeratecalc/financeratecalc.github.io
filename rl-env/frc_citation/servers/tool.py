"""Toolset: proxies the publisher's live MCP server (14 tools, worker 1.15.1).

Two generic tools keep the adapter independent of the server's tool list. Runs as a
subprocess MCP server per rollout (verifiers launches `python -m ...servers.tool`).

Replay cache: `fixtures/tool-cache.json` (recorded by `record_tool_cache.py`) holds the
outputs of every call the battery needs. A call whose (tool, args) is in the cache is
served from it and never touches the network, so thousands of rollouts cost the public
server nothing. A miss goes to the network unless FRC_OFFLINE=1, in which case the
model gets an error object. FRC_TOOL_CACHE overrides the cache path; FRC_TOOL_CACHE=0
disables it.
"""
from __future__ import annotations
import json, os, urllib.request
from pathlib import Path

import verifiers.v1 as vf

MCP_URL = os.environ.get("FRC_MCP_URL", "https://frc-mcp.ziyetis.workers.dev")
OFFLINE = os.environ.get("FRC_OFFLINE", "0") == "1"
_CACHE_PATH = os.environ.get("FRC_TOOL_CACHE") or str(Path(__file__).resolve().parent.parent / "fixtures" / "tool-cache.json")
_CACHE: dict | None = None


def cache_key(tool: str, args: dict) -> str:
    return tool + " " + json.dumps(args or {}, sort_keys=True, separators=(",", ":"))


def _cache() -> dict:
    global _CACHE
    if _CACHE is None:
        _CACHE = {}
        if _CACHE_PATH != "0" and os.path.exists(_CACHE_PATH):
            with open(_CACHE_PATH, encoding="utf-8") as f:
                _CACHE = json.load(f)
    return _CACHE


def _jsonrpc(method: str, params: dict | None = None) -> dict:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}).encode()
    req = urllib.request.Request(MCP_URL, data=body, method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
        "User-Agent": "frc-citation-env/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode()
    if raw.startswith("event:") or raw.startswith("data:") or "\ndata:" in raw:
        lines = [l[5:].strip() for l in raw.splitlines() if l.startswith("data:")]
        raw = lines[-1] if lines else raw
    return json.loads(raw)


class FrcCitationToolset(vf.Toolset[vf.ToolsetConfig]):
    TOOL_PREFIX = "frc"

    @vf.tool
    def list_tools(self) -> str:
        """List the publisher's statistics tools with their descriptions and input schemas."""
        c = _cache()
        if c.get("tools_list"):
            return json.dumps(c["tools_list"])
        if OFFLINE:
            return json.dumps({"error": "offline and no tool list in cache"})
        try:
            return json.dumps(_jsonrpc("tools/list").get("result", {}))
        except Exception as e:  # network failure is data for the model, not a crash
            return json.dumps({"error": str(e)})

    @vf.tool
    def call(self, tool: str, arguments_json: str = "{}") -> str:
        """Call one of the publisher's tools by name with a JSON object of arguments.
        The output carries the figure, its universe, contract fields and a claim receipt:
        write every figure with its receipt exactly as returned."""
        try:
            args = json.loads(arguments_json or "{}")
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"arguments_json is not valid JSON: {e}"})
        hit = _cache().get("calls", {}).get(cache_key(tool, args))
        if hit is not None:
            return json.dumps(hit)
        if OFFLINE:
            return json.dumps({"error": f"offline: no cached output for {tool} with these arguments; "
                                        "try the exact names from list_tools or fewer arguments"})
        try:
            res = _jsonrpc("tools/call", {"name": tool, "arguments": args})
        except Exception as e:
            return json.dumps({"error": str(e)})
        return json.dumps(res.get("result", res))


if __name__ == "__main__":
    FrcCitationToolset.run()
