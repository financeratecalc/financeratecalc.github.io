"""verifiers (v1 API, 0.3.x) taskset for the source-faithful-citation environment.

Status: adapter v0, written against the verifiers 0.3.1 source (Task / Taskset /
Toolset / @reward), NOT yet executed end to end. The Inspect AI task in
eval/denial_ai_fidelity.py is the executed reference; this file maps the same
questions, tools and deterministic rewards onto verifiers so the environment can be
listed on the Environments Hub and trained with prime-rl. Report problems at
https://github.com/financeratecalc/financeratecalc.github.io/issues.

Deterministic rewards only (rewards.py). The judged fidelity signal is deliberately
left out of this taskset; see judge.py for an optional judge.
"""
from __future__ import annotations
import json, os, urllib.request
from collections.abc import Iterator

import verifiers.v1 as vf

from rewards import composite
from verify_offline import Verifier

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_ROOT = os.environ.get("FRC_SITE_ROOT", os.path.join(HERE, ".."))
MCP_URL = os.environ.get("FRC_MCP_URL", "https://frc-mcp.ziyetis.workers.dev")

SYSTEM_PROMPT = (
    "Answer the question. You have tools that return a publisher's figures together with their use "
    "contracts and a claim receipt. Use them. State the figure with its population, program and period, "
    "cite the source, and write every figure with its claim receipt exactly as the tool returned it "
    "(the receipt is part of the figure). Never invent a receipt. Do not predict any individual's "
    "outcome, assert a cause the data cannot support, recommend or warn against a lender, or describe "
    "any lender's figure as evidence of misconduct."
)


def _jsonrpc(method: str, params: dict | None = None) -> dict:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}).encode()
    req = urllib.request.Request(MCP_URL, data=body, method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
        "User-Agent": "frc-rl-env/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode()
    # streamable HTTP may answer as SSE; take the last data: line
    if raw.startswith("event:") or "\ndata:" in raw or raw.startswith("data:"):
        lines = [l[5:].strip() for l in raw.splitlines() if l.startswith("data:")]
        raw = lines[-1] if lines else raw
    return json.loads(raw)


class FRCToolset(vf.Toolset):
    """Proxies the publisher's MCP server. Two generic tools keep the adapter independent
    of the server's tool list (14 tools at worker 1.14.1; list them with frc_list_tools)."""

    @vf.tool
    def frc_list_tools(self) -> str:
        """List the publisher's tools with their descriptions and input schemas."""
        return json.dumps(_jsonrpc("tools/list").get("result", {}))

    @vf.tool
    def frc_call(self, tool: str, arguments_json: str = "{}") -> str:
        """Call one of the publisher's tools by name with a JSON object of arguments.
        Returns the tool output: figures, universe, contract fields and claim receipt."""
        try:
            args = json.loads(arguments_json or "{}")
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"arguments_json is not valid JSON: {e}"})
        res = _jsonrpc("tools/call", {"name": tool, "arguments": args})
        return json.dumps(res.get("result", res))


class CitationData(vf.TaskData):
    qid: str
    key_numbers: list[str]
    ground_truth: str
    universe: str | None = None


class CitationTask(vf.Task[CitationData, vf.State, vf.TaskConfig]):
    _verifier: Verifier | None = None

    @classmethod
    def toolsets(cls, config):
        return [FRCToolset(vf.ToolsetConfig())]

    @property
    def key(self) -> str:
        return f"frc-citation:{self.data.qid}"

    @staticmethod
    def _final_text(trace) -> str:
        msgs = trace.messages
        for m in reversed(list(msgs)):
            role = getattr(m, "role", None) or (m.get("role") if isinstance(m, dict) else None)
            if role == "assistant":
                content = getattr(m, "content", None) if not isinstance(m, dict) else m.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    return "\n".join(p.get("text", "") for p in content if isinstance(p, dict))
        return ""

    def _v(self) -> Verifier:
        if CitationTask._verifier is None:
            CitationTask._verifier = Verifier(SITE_ROOT)
        return CitationTask._verifier

    @vf.reward
    def reward(self, trace) -> dict:
        c = composite(self._final_text(trace), self.data.key_numbers, self._v())
        return {"reward": c["reward"], "value": c["value"], "receipt": c["receipt"],
                "forgery": c["forgery"], "red_line": c["red_line"]}

    @vf.metric
    def receipts(self, trace) -> dict:
        c = composite(self._final_text(trace), self.data.key_numbers, self._v())
        s = c["receipt_signals"]
        return {"receipts_found": float(s["found"]), "receipts_valid": float(s["valid"]),
                "receipts_stale": float(s["stale"]), "receipts_forged": float(s["forged"] + s["altered"]),
                "red_line_hit": 1.0 if c["red_line_hits"] else 0.0}


class CitationTaskset(vf.Taskset[CitationTask, vf.TasksetConfig]):
    def load(self) -> Iterator[CitationTask]:
        with open(os.path.join(HERE, "questions.json"), encoding="utf-8") as f:
            qs = json.load(f)["questions"]
        for i, q in enumerate(qs):
            yield CitationTask(
                CitationData(idx=i, name=q["id"], prompt=q["question"], system_prompt=SYSTEM_PROMPT,
                             qid=q["id"], key_numbers=q["key_numbers"], ground_truth=q["ground_truth"],
                             universe=q.get("universe")),
                self.config.task,
            )
