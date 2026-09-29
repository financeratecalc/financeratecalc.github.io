"""Toolset: proxies the publisher's live MCP server (14 tools, worker 1.14.1).

Two generic tools keep the adapter independent of the server's tool list. Runs as a
subprocess MCP server per rollout (verifiers launches `python -m ...servers.tool`).
"""
from __future__ import annotations
import json, os, urllib.request

import verifiers.v1 as vf

MCP_URL = os.environ.get("FRC_MCP_URL", "https://frc-mcp.ziyetis.workers.dev")


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
        try:
            res = _jsonrpc("tools/call", {"name": tool, "arguments": args})
        except Exception as e:
            return json.dumps({"error": str(e)})
        return json.dumps(res.get("result", res))


if __name__ == "__main__":
    FrcCitationToolset.run()
