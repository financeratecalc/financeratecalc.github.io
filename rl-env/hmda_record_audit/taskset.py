"""verifiers v1 taskset: hmda-record-audit (FinanceRateCalc).

Single-turn, no tools. The prompt carries one public HMDA LAR record (2025, FHA) and either
asks for regulatory arithmetic (task A) or for the consistency rules that fire (task B).
Ground truth is computed from the record and the published rules; rewards are model-free.
"""
from __future__ import annotations

import json
import os

import verifiers.v1 as vf

from hmda_record_audit.rewards import arithmetic_reward, audit_reward
from hmda_record_audit.rules import rulebook_text

HERE = os.path.dirname(os.path.abspath(__file__))

SYSTEM_PROMPT = (
    "You audit one public HMDA loan/application record at a time. Work only from the record and the "
    "rulebook given; do not look anything up. Answer with a single JSON object and nothing after it. "
    "Never predict whether any application will be approved or denied; this environment grades record "
    "consistency and regulatory arithmetic, not outcomes."
)

ARITH_INSTRUCTIONS = (
    "Task A. The record is an originated FHA forward loan. Compute, as a JSON object with exactly these keys:\n"
    '  {"ltv": loan_amount / property_value as a decimal (4 dp),\n'
    '   "mip_upfront": 1.75% of loan_amount in dollars (2 dp),\n'
    '   "mip_annual_rate": the FHA annual MIP rate as a decimal under HUD Mortgagee Letter 2023-05 '
    "(base loan amount threshold $726,200; term from loan_term in months; use the ltv you computed),\n"
    '   "mip_monthly": loan_amount x mip_annual_rate / 12 in dollars (2 dp; first-year approximation)}\n'
)

AUDIT_INSTRUCTIONS = (
    "Task B. Using ONLY the rulebook below, list the ids of every rule that fires on this record "
    '(validity violated or quality check tripped). Answer as {"rules_fired": [ids]}; use [] if none. '
    "Do not invent ids that are not in the rulebook.\n\nRULEBOOK\n" + rulebook_text() + "\n"
)


class AuditData(vf.TaskData):
    tid: str
    task_type: str  # "arith" | "audit"
    record: dict
    truth: dict


class AuditTaskConfig(vf.TaskConfig):
    tools: vf.ToolsetConfig = vf.ToolsetConfig()  # no toolsets; kept so the shared smoke workflow flags apply


def _final_text(trace) -> str:
    for m in reversed(list(trace.messages)):
        role = getattr(m, "role", None) if not isinstance(m, dict) else m.get("role")
        if role == "assistant":
            content = getattr(m, "content", None) if not isinstance(m, dict) else m.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "\n".join((p.get("text", "") if isinstance(p, dict) else getattr(p, "text", "")) for p in content)
    return ""


class AuditTask(vf.Task[AuditData, vf.State, AuditTaskConfig]):
    @property
    def key(self) -> str:
        return f"hmda-record-audit:{self.data.tid}"

    def _score(self, trace) -> dict:
        text = _final_text(trace)
        if self.data.task_type == "arith":
            return arithmetic_reward(text, self.data.truth)
        return audit_reward(text, self.data.truth["rules_fired"])

    @vf.reward(weight=1.0)
    async def reward(self, trace: vf.Trace) -> float:
        return self._score(trace)["reward"]

    @vf.metric
    async def signals(self, trace: vf.Trace) -> dict:
        s = self._score(trace)
        return {k: float(v) for k, v in s.items() if isinstance(v, (int, float, bool))}


class AuditTasksetConfig(vf.TasksetConfig):
    task: AuditTaskConfig = AuditTaskConfig()
    fixtures: str = os.environ.get("HMDA_AUDIT_FIXTURES", os.path.join(HERE, "fixtures", "tasks.json"))


def build_prompt(task_type: str, record: dict) -> str:
    head = ARITH_INSTRUCTIONS if task_type == "arith" else AUDIT_INSTRUCTIONS
    return head + "\nRECORD\n" + json.dumps(record, indent=1, ensure_ascii=False)


class HmdaRecordAuditTaskset(vf.Taskset[AuditTask, AuditTasksetConfig]):
    def load(self) -> list[AuditTask]:
        with open(self.config.fixtures, encoding="utf-8") as f:
            raw = json.load(f)["tasks"]
        # interleave A and B so that any prefix (--num-tasks N) is balanced across task types
        a = [t for t in raw if t["type"] == "arith"]
        b = [t for t in raw if t["type"] != "arith"]
        tasks = []
        for i in range(max(len(a), len(b))):
            if i < len(a):
                tasks.append(a[i])
            if i < len(b):
                tasks.append(b[i])
        return [AuditTask(AuditData(idx=i, name=t["id"], prompt=build_prompt(t["type"], t["record"]),
                                    system_prompt=SYSTEM_PROMPT, tid=t["id"], task_type=t["type"],
                                    record=t["record"], truth=t["truth"]), self.config.task)
                for i, t in enumerate(tasks)]
