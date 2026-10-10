#!/usr/bin/env python3
"""Build fixtures for rl-env/hmda_record_audit from the CFPB HMDA public LAR extract.

usage: hmda_audit_sample.py <hmda_2025_fha.csv> <out_dir> [seed]

Produces out_dir/tasks.json with 500 tasks:
  * 200 task A (arithmetic): originated FHA forward loans (action_taken=1, loan_type=2, numeric
    loan_amount, property_value, loan_term), truth from hmda_record_audit.arith.
  * 300 task B (audit): 150 real records as published ("clean" or whatever fires naturally) and
    150 real records with ONE documented perturbation that trips a rule; truth = rules fired on
    the (possibly perturbed) record, computed by hmda_record_audit.rules. Every perturbation is
    recorded in the task so the ground truth is reproducible.
Records are reduced to the columns the rulebook and the arithmetic use; no names exist in the LAR.
The sampling is seeded; the input SHA-256 is written into the file.
"""
import csv
import datetime as dt
import hashlib
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rl-env"))
from hmda_record_audit.arith import arithmetic_answer
from hmda_record_audit.rules import fired

COLS = ["lei", "state_code", "action_taken", "loan_type", "loan_purpose", "loan_amount", "income", "property_value",
        "combined_loan_to_value_ratio", "debt_to_income_ratio", "rate_spread", "hoepa_status", "purchaser_type",
        "interest_rate", "total_loan_costs", "origination_charges", "loan_term", "reverse_mortgage",
        "open-end_line_of_credit", "denial_reason-1", "denial_reason-2", "lien_status", "occupancy_type"]

PERTURBATIONS = [  # (name, applies-when, mutation)
    ("denial_reason_on_origination", lambda r: r["action_taken"] == "1", lambda r: r.update({"denial_reason-1": "3"})),
    ("no_denial_reason_on_denial", lambda r: r["action_taken"] == "3", lambda r: r.update({"denial_reason-1": "10"})),
    ("property_value_on_withdrawn", lambda r: r["action_taken"] in ("4", "5"), lambda r: r.update({"property_value": r.get("loan_amount") or "250000"})),
    ("rate_spread_on_denial", lambda r: r["action_taken"] == "3", lambda r: r.update({"rate_spread": "1.25"})),
    ("hoepa_not_3_on_denial", lambda r: r["action_taken"] == "3", lambda r: r.update({"hoepa_status": "2"})),
    ("interest_rate_on_denial", lambda r: r["action_taken"] == "3", lambda r: r.update({"interest_rate": "6.5"})),
    ("purchaser_on_denial", lambda r: r["action_taken"] == "3", lambda r: r.update({"purchaser_type": "2"})),
    ("loan_type_invalid", lambda r: True, lambda r: r.update({"loan_type": "5"})),
    ("cltv_decimal_misplaced", lambda r: r["action_taken"] == "1", lambda r: r.update({"combined_loan_to_value_ratio": "0.965"})),
    ("interest_rate_decimal_misplaced", lambda r: r["action_taken"] == "1", lambda r: r.update({"interest_rate": "0.065"})),
    ("costs_below_origination", lambda r: r["action_taken"] == "1", lambda r: r.update({"total_loan_costs": "900", "origination_charges": "1500"})),
    ("ginnie_on_conventional", lambda r: r["action_taken"] == "1", lambda r: r.update({"purchaser_type": "2", "loan_type": "1"})),
    ("reverse_mortgage_blank", lambda r: True, lambda r: r.update({"reverse_mortgage": ""})),
]


def num(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def main(path, out_dir, seed=20261010):
    rng = random.Random(seed)
    with open(path, encoding="utf-8", errors="ignore") as f:
        head = f.readline()
    sep = next((s for s in [",", "|", "\t", ";"] if len(head.split(s)) > 8), ",")
    pool_arith, pool_audit = [], []
    n = 0
    with open(path, encoding="utf-8", errors="ignore") as f:
        rd = csv.DictReader(f, delimiter=sep)
        for row in rd:
            n += 1
            r = {c: (row.get(c, "") or "").strip() for c in COLS}
            if r["loan_type"] != "2" or r.get("reverse_mortgage") == "1":
                continue
            # reservoir-ish: keep with small probability to bound memory, then sample from pools
            if rng.random() < 0.004:
                pool_audit.append(r)
            if (r["action_taken"] == "1" and num(r["loan_amount"]) and num(r["property_value"]) and num(r["loan_term"])
                    and num(r["property_value"]) > 0 and 0.3 <= num(r["loan_amount"]) / num(r["property_value"]) <= 1.1
                    and rng.random() < 0.004):
                pool_arith.append(r)
    rng.shuffle(pool_arith); rng.shuffle(pool_audit)
    tasks = []
    for i, r in enumerate(pool_arith[:200]):
        truth = arithmetic_answer(num(r["loan_amount"]), num(r["property_value"]), int(num(r["loan_term"])))
        tasks.append({"id": f"A{i+1:03d}", "type": "arith", "record": r, "truth": truth, "perturbation": None})
    # audit: 150 as published
    real = pool_audit[:150]
    for i, r in enumerate(real):
        tasks.append({"id": f"B{i+1:03d}", "type": "audit", "record": r, "truth": {"rules_fired": fired(r)}, "perturbation": None})
    # audit: 150 perturbed, one perturbation each, chosen round-robin among applicable ones
    k = 0
    for r in pool_audit[150:]:
        if k >= 150:
            break
        applicable = [p for p in PERTURBATIONS if p[1](r)]
        if not applicable:
            continue
        name, _, mut = applicable[k % len(applicable)]
        before = fired(r)
        r2 = dict(r); mut(r2)
        after = fired(r2)
        if set(after) == set(before):
            continue  # perturbation did not change the truth; skip
        k += 1
        tasks.append({"id": f"B{150+k:03d}", "type": "audit", "record": r2, "truth": {"rules_fired": after},
                      "perturbation": {"name": name, "fields": [c for c in COLS if r.get(c) != r2.get(c)]}})
    with open(path, "rb") as fb:
        sha = hashlib.sha256(fb.read()).hexdigest()
    out = {"generated": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "seed": seed,
           "input_sha256": sha, "rows_read": n,
           "universe": "CFPB HMDA 2025 public LAR, loan_type 2 (FHA), reverse mortgages excluded",
           "counts": {"arith": sum(t["type"] == "arith" for t in tasks), "audit_real": len(real), "audit_perturbed": k},
           "note": "Records reduced to the columns used; the LAR carries no names. Perturbations are documented per task; truth is recomputed from the record by the same code that grades.",
           "tasks": tasks}
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "tasks.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(json.dumps(out["counts"]), "rows", n)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 20261010)
