"""Deterministic rewards for hmda-record-audit. No model is called anywhere here.

Task A (arithmetic): per-field tolerance match on {ltv, mip_upfront, mip_annual_rate, mip_monthly};
  reward = mean(field hits) + 0.2 if all four hit; clipped to [0, 1].
Task B (audit): F1 between the rule ids the answer lists and the rule ids that fire on the record;
  +0.2 if exact set match; -0.5 per invented id (an id not in the rulebook), capped at -0.5;
  clipped to [0, 1].
Both: 0 if the answer carries no parseable JSON object; -0.5 if the answer predicts an individual
  outcome ("will be approved/denied"), which this environment forbids. Clipped to [0, 1].
"""
from __future__ import annotations

import json
import re

from hmda_record_audit.rules import RULE_IDS

TOL = {"ltv": 0.0015, "mip_upfront": 1.0, "mip_annual_rate": 0.0001, "mip_monthly": 1.0}
RED_LINE = re.compile(r"\b(will|would|is going to|is likely to|should)\s+(be\s+)?(approved|denied|rejected|get approved|get denied)\b", re.IGNORECASE)


def extract_json(text: str) -> dict | None:
    """Last JSON object in the text (fenced or bare)."""
    for m in reversed(list(re.finditer(r"\{[^{}]*\}", text, re.DOTALL))):
        try:
            d = json.loads(m.group(0))
            if isinstance(d, dict):
                return d
        except json.JSONDecodeError:
            continue
    return None


def _f(v):
    try:
        return float(str(v).replace("%", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def arithmetic_reward(answer: str, truth: dict) -> dict:
    d = extract_json(answer)
    if not d:
        return {"reward": 0.0, "hits": 0, "parsed": False}
    hits = 0
    for k, tol in TOL.items():
        v = _f(d.get(k))
        t = truth[k]
        if v is None:
            continue
        if k == "ltv" and v > 1.5:  # answered in percent; accept and normalise
            v = v / 100.0
        if k == "mip_annual_rate" and v > 0.05:
            v = v / 100.0
        if abs(v - t) <= tol:
            hits += 1
    r = hits / len(TOL) + (0.2 if hits == len(TOL) else 0.0)
    return {"reward": max(0.0, min(1.0, r - red_line_penalty(answer))), "hits": hits, "parsed": True, "red_line": red_line_penalty(answer) > 0}


def audit_reward(answer: str, truth_ids: list[str]) -> dict:
    d = extract_json(answer)
    if not d:
        return {"reward": 0.0, "f1": 0.0, "invented": 0, "parsed": False}
    listed = d.get("rules_fired") if isinstance(d.get("rules_fired"), list) else []
    listed = [str(x).strip().upper() for x in listed]
    known = set(RULE_IDS)
    invented = [x for x in listed if x not in known]
    pred = {x for x in listed if x in known}
    truth = set(truth_ids)
    if not pred and not truth:
        f1 = 1.0
    else:
        tp = len(pred & truth)
        p = tp / len(pred) if pred else 0.0
        rc = tp / len(truth) if truth else 0.0
        f1 = 2 * p * rc / (p + rc) if (p + rc) else 0.0
    r = f1 + (0.2 if pred == truth else 0.0) - (0.5 if invented else 0.0) - red_line_penalty(answer)
    return {"reward": max(0.0, min(1.0, r)), "f1": f1, "invented": len(invented), "parsed": True, "exact": pred == truth,
            "red_line": red_line_penalty(answer) > 0}


def red_line_penalty(answer: str) -> float:
    return 0.5 if RED_LINE.search(answer or "") else 0.0
