"""Record-consistency rules for a public HMDA LAR row (task B).

Each rule carries the rule text as published in the FFIEC/CFPB HMDA Filing Instructions Guide
(edit specifications; wording from the 2021 FIG, unchanged in substance for 2025 for the fields
used here). The official edit numbers are deliberately NOT reproduced: they are renumbered between
filing years and a wrong number would be exactly the kind of error this project measures. Our ids
(FRC-Vxx validity, FRC-Qxx quality) are stable within this environment.

Field names are the public LAR column names of the CFPB data browser extract. A rule returns True
when it FIRES (the record violates the validity rule or trips the quality check).
"""
from __future__ import annotations

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
