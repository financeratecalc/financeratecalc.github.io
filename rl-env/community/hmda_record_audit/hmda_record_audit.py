"""hmda-record-audit (Hub package): audit one public HMDA 2025 FHA record.

Two task types, graded without a judge model:
  A  regulatory arithmetic: LTV, FHA upfront MIP (1.75%), annual MIP rate under HUD ML 2023-05, monthly MIP
  B  record consistency: which of 18 rules (text quoted from the HMDA FIG edit specifications) fire
Rewards: A per-field tolerance match (+0.2 all four); B F1 vs the rules that fire (+0.2 exact set,
-0.5 for an invented rule id); both 0 without parseable JSON, -0.5 for predicting an individual outcome.
Fixtures: 500 tasks built from the CFPB HMDA 2025 FHA extract (seeded; input SHA-256 in tasks.json);
150 of the 300 audit records carry one documented perturbation.
Publisher: FinanceRateCalc (CC BY 4.0). This environment never asks whether an application will be approved.
Source of truth for the code: financeratecalc.github.io/rl-env/hmda_record_audit (v1 taskset); this file inlines it.
"""
from __future__ import annotations

import json
import os
import re

import verifiers as vf
from datasets import Dataset

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- arithmetic ----

UPFRONT_RATE = 0.0175
THRESHOLD = 726_200.0


def ltv(loan_amount: float, property_value: float) -> float:
    return round(loan_amount / property_value, 4)


def annual_mip_rate(loan_amount: float, ltv_ratio: float, term_months: int) -> float:
    big = loan_amount > THRESHOLD
    if term_months > 180:
        if not big:
            bp = 55 if ltv_ratio > 0.95 else 50
        else:
            bp = 75 if ltv_ratio > 0.95 else 70
    else:
        if not big:
            bp = 40 if ltv_ratio > 0.90 else 15
        else:
            bp = 65 if ltv_ratio > 0.90 else (40 if ltv_ratio > 0.78 else 15)
    return bp / 10_000.0


def arithmetic_answer(loan_amount: float, property_value: float, term_months: int) -> dict:
    r = ltv(loan_amount, property_value)
    rate = annual_mip_rate(loan_amount, r, term_months)
    return {
        "ltv": r,
        "mip_upfront": round(loan_amount * UPFRONT_RATE, 2),
        "mip_annual_rate": rate,
        "mip_monthly": round(loan_amount * rate / 12.0, 2),
    }

# ---- rules ----

NA = {"NA", "na", "N/A", "", None}
EXEMPT = {"Exempt", "exempt"}


def _num(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _is_na_or_exempt(v) -> bool:
    return v in NA or v in EXEMPT


def _action(r) -> int | None:
    n = _num(r.get("action_taken"))
    return int(n) if n is not None else None


RULES = [
    {"id": "FRC-V01", "kind": "validity", "fields": ["action_taken", "denial_reason-1"],
     "text": "If Action Taken equals 3 or 7, then Reason for Denial: 1 must equal 1111, 1, 2, 3, 4, 5, 6, 7, 8, or 9.",
     "check": lambda r: _action(r) in (3, 7) and _num(r.get("denial_reason-1")) not in (1111, 1, 2, 3, 4, 5, 6, 7, 8, 9)},
    {"id": "FRC-V02", "kind": "validity", "fields": ["action_taken", "denial_reason-1"],
     "text": "If Action Taken equals 1, 2, 4, 5, 6, or 8, then Reason for Denial: 1 must equal 10 (not applicable).",
     "check": lambda r: _action(r) in (1, 2, 4, 5, 6, 8) and _num(r.get("denial_reason-1")) not in (10, 1111)},
    {"id": "FRC-V03", "kind": "validity", "fields": ["loan_amount"],
     "text": "Loan Amount must be a number greater than or equal to 0, and cannot be left blank.",
     "check": lambda r: _num(r.get("loan_amount")) is None or _num(r.get("loan_amount")) < 0},
    {"id": "FRC-V04", "kind": "validity", "fields": ["action_taken", "property_value"],
     "text": "If Action Taken equals 4 or 5, then Property Value must be NA or Exempt.",
     "check": lambda r: _action(r) in (4, 5) and not _is_na_or_exempt(r.get("property_value"))},
    {"id": "FRC-V05", "kind": "validity", "fields": ["action_taken", "combined_loan_to_value_ratio"],
     "text": "If Action Taken equals 4, 5, or 6, then Combined Loan-to-Value Ratio must be NA or Exempt.",
     "check": lambda r: _action(r) in (4, 5, 6) and not _is_na_or_exempt(r.get("combined_loan_to_value_ratio"))},
    {"id": "FRC-V06", "kind": "validity", "fields": ["action_taken", "debt_to_income_ratio"],
     "text": "If Action Taken equals 4, 5, or 6, then Debt-to-Income Ratio must be NA or Exempt.",
     "check": lambda r: _action(r) in (4, 5, 6) and not _is_na_or_exempt(r.get("debt_to_income_ratio"))},
    {"id": "FRC-V07", "kind": "validity", "fields": ["action_taken", "rate_spread"],
     "text": "If Action Taken equals 3, 4, 5, 6, or 7, then Rate Spread must be NA or Exempt.",
     "check": lambda r: _action(r) in (3, 4, 5, 6, 7) and not _is_na_or_exempt(r.get("rate_spread"))},
    {"id": "FRC-V08", "kind": "validity", "fields": ["action_taken", "hoepa_status"],
     "text": "If Action Taken equals 2, 3, 4, 5, 7, or 8, then HOEPA Status must equal 3.",
     "check": lambda r: _action(r) in (2, 3, 4, 5, 7, 8) and _num(r.get("hoepa_status")) != 3},
    {"id": "FRC-V09", "kind": "validity", "fields": ["loan_type"],
     "text": "Loan Type must equal 1, 2, 3, or 4, and cannot be left blank.",
     "check": lambda r: _num(r.get("loan_type")) not in (1, 2, 3, 4)},
    {"id": "FRC-V10", "kind": "validity", "fields": ["action_taken", "interest_rate"],
     "text": "If Action Taken equals 3, 4, 5, or 7, then Interest Rate must be NA or Exempt.",
     "check": lambda r: _action(r) in (3, 4, 5, 7) and not _is_na_or_exempt(r.get("interest_rate"))},
    {"id": "FRC-V11", "kind": "validity", "fields": ["action_taken", "purchaser_type"],
     "text": "If Action Taken equals 2, 3, 4, 5, 7, or 8, then Type of Purchaser must equal 0 (not applicable).",
     "check": lambda r: _action(r) in (2, 3, 4, 5, 7, 8) and _num(r.get("purchaser_type")) not in (0, None)},
    {"id": "FRC-V12", "kind": "validity", "fields": ["reverse_mortgage", "open-end_line_of_credit"],
     "text": "Reverse Mortgage and Open-End Line of Credit must each equal 1111, 1, or 2, and cannot be left blank.",
     "check": lambda r: _num(r.get("reverse_mortgage")) not in (1111, 1, 2) or _num(r.get("open-end_line_of_credit")) not in (1111, 1, 2)},
    {"id": "FRC-Q01", "kind": "quality", "fields": ["purchaser_type", "loan_type"],
     "text": "If Type of Purchaser equals 2 (Ginnie Mae), then Loan Type generally should equal 2, 3, or 4.",
     "check": lambda r: _num(r.get("purchaser_type")) == 2 and _num(r.get("loan_type")) not in (2, 3, 4)},
    {"id": "FRC-Q02", "kind": "quality", "fields": ["purchaser_type", "hoepa_status"],
     "text": "If Type of Purchaser equals 1 or 3, then HOEPA Status generally should be 2 or 3.",
     "check": lambda r: _num(r.get("purchaser_type")) in (1, 3) and _num(r.get("hoepa_status")) not in (2, 3)},
    {"id": "FRC-Q03", "kind": "quality", "fields": ["total_loan_costs", "origination_charges"],
     "text": "If Total Loan Costs and Origination Charges are both numbers greater than 0, Total Loan Costs generally should be greater than Origination Charges.",
     "check": lambda r: (_num(r.get("total_loan_costs")) or 0) > 0 and (_num(r.get("origination_charges")) or 0) > 0 and _num(r.get("total_loan_costs")) <= _num(r.get("origination_charges"))},
    {"id": "FRC-Q04", "kind": "quality", "fields": ["interest_rate"],
     "text": "If Interest Rate is a number greater than 0 but less than 0.5, or greater than 20, it may indicate a misplaced decimal point.",
     "check": lambda r: _num(r.get("interest_rate")) is not None and (0 < _num(r.get("interest_rate")) < 0.5 or _num(r.get("interest_rate")) > 20)},
    {"id": "FRC-Q05", "kind": "quality", "fields": ["combined_loan_to_value_ratio"],
     "text": "If Combined Loan-to-Value Ratio is a number greater than 0 but less than 1, it may indicate a misplaced decimal point.",
     "check": lambda r: _num(r.get("combined_loan_to_value_ratio")) is not None and 0 < _num(r.get("combined_loan_to_value_ratio")) < 1},
    {"id": "FRC-Q06", "kind": "quality", "fields": ["debt_to_income_ratio"],
     "text": "If Debt-to-Income Ratio is a number greater than 0 but less than 1, it may indicate a misplaced decimal point (bucketed public values are exempt from this check).",
     "check": lambda r: _num(r.get("debt_to_income_ratio")) is not None and 0 < _num(r.get("debt_to_income_ratio")) < 1},
]

RULE_IDS = [x["id"] for x in RULES]
RULE_INDEX = {x["id"]: x for x in RULES}


def fired(record: dict) -> list[str]:
    out = []
    for rule in RULES:
        try:
            hit = rule["check"](record)
        except (TypeError, ValueError, KeyError):  # a malformed field never crashes grading; it simply does not fire
            hit = False
        if hit:
            out.append(rule["id"])
    return out


def rulebook_text() -> str:
    return "\n".join(f"{x['id']} ({x['kind']}): {x['text']}" for x in RULES)

# ---- rewards ----



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


# ---- environment ----
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


def _text(completion) -> str:
    if isinstance(completion, str):
        return completion
    for m in reversed(list(completion)):
        if (m.get("role") if isinstance(m, dict) else getattr(m, "role", None)) == "assistant":
            c = m.get("content") if isinstance(m, dict) else getattr(m, "content", "")
            return c if isinstance(c, str) else "".join(p.get("text", "") for p in c if isinstance(p, dict))
    return ""


def _score(completion, info) -> dict:
    text = _text(completion)
    if info["task_type"] == "arith":
        return arithmetic_reward(text, info["truth"])
    return audit_reward(text, info["truth"]["rules_fired"])


def reward(completion, info, **kwargs) -> float:
    return _score(completion, info)["reward"]


def parsed(completion, info, **kwargs) -> float:
    return 1.0 if _score(completion, info).get("parsed") else 0.0


def invented_ids(completion, info, **kwargs) -> float:
    return float(_score(completion, info).get("invented", 0))


def exact(completion, info, **kwargs) -> float:
    s = _score(completion, info)
    return 1.0 if (s.get("exact") or s.get("hits") == 4) else 0.0


def red_line(completion, info, **kwargs) -> float:
    return 1.0 if _score(completion, info).get("red_line") else 0.0


def load_dataset_local() -> Dataset:
    with open(os.path.join(HERE, "tasks.json"), encoding="utf-8") as f:
        raw = json.load(f)["tasks"]
    a = [t for t in raw if t["type"] == "arith"]; b = [t for t in raw if t["type"] != "arith"]
    tasks = []
    for i in range(max(len(a), len(b))):
        if i < len(a):
            tasks.append(a[i])
        if i < len(b):
            tasks.append(b[i])
    def prompt(t):
        head = ARITH_INSTRUCTIONS if t["type"] == "arith" else AUDIT_INSTRUCTIONS
        return head + "\nRECORD\n" + json.dumps(t["record"], indent=1, ensure_ascii=False)
    return Dataset.from_dict({
        "question": [prompt(t) for t in tasks],
        "answer": [json.dumps(t["truth"]) for t in tasks],
        "info": [{"tid": t["id"], "task_type": t["type"], "truth": t["truth"], "perturbation": t.get("perturbation")} for t in tasks],
        "task": [t["id"] for t in tasks],
    })


def load_environment(**kwargs) -> vf.Environment:
    rubric = vf.Rubric(funcs=[reward, parsed, invented_ids, exact, red_line], weights=[1.0, 0.0, 0.0, 0.0, 0.0])
    return vf.SingleTurnEnv(dataset=load_dataset_local(), system_prompt=SYSTEM_PROMPT, rubric=rubric, **kwargs)
