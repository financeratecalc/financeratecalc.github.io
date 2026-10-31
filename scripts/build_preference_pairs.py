#!/usr/bin/env python3
"""Preference pairs (DPO/ORPO shape) from the citation-decision fixtures and the correction pairs.

One row per (question, rejected candidate): the chosen answer is the genuine, receipted sentence the gate passes;
the rejected one is a candidate the record cannot support, labelled by why (forged receipt, wrong role, wrong
tier or cell, wrong period, superseded value, unverifiable, condition missing, qualifier dropped). Correction
pairs (old value -> corrected value) are appended with kind=correction. No model made any row; every chosen
sentence carries a receipt that verifies, every rejected one a reason code from the deterministic gate.

    python3 scripts/build_preference_pairs.py                 # writes eval/preference-pairs.jsonl (+ .json summary)
    python3 scripts/build_preference_pairs.py --out <dir>     # also copies the files for the HF upload
"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "fixtures", "citation-decision", "fixtures.json")
CORR = os.path.join(ROOT, "eval", "correction-pairs.json")
OUT = os.path.join(ROOT, "eval", "preference-pairs.jsonl")
SUMMARY = os.path.join(ROOT, "eval", "preference-pairs.json")

# How far apart the two answers are, for trainers that weight pairs (ORPO/DPO margin). Dropped qualifier is a small
# margin: the number is right, the sentence incomplete. A forged receipt is the full margin.
MARGIN = {"genuine_needs_qualifier": 0.25, "condition_missing": 0.5, "unverifiable": 0.5, "wrong_period": 0.75,
          "superseded": 0.75, "wrong_tier_or_cell": 1.0, "wrong_role": 1.0, "forged": 1.0}
SYSTEM = ("Answer with the publisher's figure in its canonical form: period, population and program kept, the receipt "
          "next to the number. Do not invent a receipt, change the role or tier of a figure, quote a superseded value, "
          "or turn an aggregate into a prediction, a recommendation, a cause or a legal conclusion.")


def main():
    fx = json.load(open(FIX, encoding="utf-8"))
    rows = []
    for item in fx["items"]:
        genuine = [c for c in item["candidates"] if c["class"] == "genuine"]
        if not genuine:
            continue
        chosen = genuine[0]
        for c in item["candidates"]:
            if c["class"] == "genuine":
                continue
            rows.append({
                "prompt": item["question"], "system": SYSTEM,
                "chosen": chosen["text"], "rejected": c["text"],
                "kind": "fixture", "rejected_class": c["class"], "margin": MARGIN.get(c["class"], 1.0),
                "rejected_reason_codes": (c.get("gate") or {}).get("codes") or [],
                "rejected_expected_decision": c.get("expected_decision"),
                "chosen_receipt": chosen.get("receipt"), "chosen_verify": chosen.get("verify"),
                "chosen_source_url": chosen.get("source_url"), "chosen_vintage": chosen.get("vintage"),
                "question_id": item["id"], "gate_passport_id": item.get("gate_passport_id"),
                "provenance": c.get("provenance"),
            })
    corr = json.load(open(CORR, encoding="utf-8"))
    for p in corr["pairs"]:
        rows.append({
            "prompt": p["question"], "system": SYSTEM, "chosen": p["chosen"], "rejected": p["rejected"],
            "kind": p.get("kind", "correction"), "rejected_class": "superseded" if p.get("kind") == "correction" else "circulating_error",
            "margin": 0.75, "rejected_reason_codes": ["SUPERSEDED"] if p.get("kind") == "correction" else ["UNSUPPORTED"],
            "old_value": p.get("old_value"), "new_value": p.get("new_value"), "superseded_on": p.get("superseded_on"),
            "why": p.get("why"), "chosen_source_url": p.get("claim_url") or p.get("source"), "claim_id": p.get("claim_id"),
        })
    with open(OUT, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    by_class = {}
    for r in rows:
        by_class[r["rejected_class"]] = by_class.get(r["rejected_class"], 0) + 1
    summary = {
        "generated": fx.get("generated"), "fixture_version": fx.get("fixture_version"), "rows": len(rows), "by_rejected_class": by_class,
        "format": "one JSON object per line: prompt, system, chosen, rejected, margin in (0,1], rejected_class, rejected_reason_codes; chosen carries the receipt that verifies",
        "method": "No model. chosen = the genuine candidate the deterministic gate passes (receipt verifies as current); rejected = every candidate the record cannot support, from fixtures/citation-decision/fixtures.json, plus the publisher's dated corrections (old value rejected, corrected value chosen).",
        "license": fx.get("license", "CC BY 4.0"), "spec": fx.get("spec"),
        "file": "https://financeratecalc.com/eval/preference-pairs.jsonl",
    }
    json.dump(summary, open(SUMMARY, "w", encoding="utf-8"), indent=1)
    print(f"{len(rows)} pairs -> {OUT}; {by_class}")
    if "--out" in sys.argv:
        outdir = sys.argv[sys.argv.index("--out") + 1]
        os.makedirs(outdir, exist_ok=True)
        shutil.copy(OUT, os.path.join(outdir, "preference-pairs.jsonl"))
        shutil.copy(SUMMARY, os.path.join(outdir, "preference-pairs.json"))


if __name__ == "__main__":
    main()
