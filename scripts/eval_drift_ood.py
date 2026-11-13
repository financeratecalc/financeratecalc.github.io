#!/usr/bin/env python3
"""Out-of-template test of the contract-drift classifier.

The published model scores 0.998 exact match on held-out sentences written by the same rule generator that wrote its
training set. That number says the model learned the generator. This script asks the harder question: sentences written
by hand in ordinary phrasing (eval/drift-ood-set.jsonl), none from the generator's templates.

    python3 scripts/eval_drift_ood.py [--model FinanceRateCalc/frc-contract-drift]   -> eval/drift-model-ood.json

Reported: detection (did the model flag a violating sentence with any code), the right-code rate, the false-flag rate
on clean sentences, and per-code recall, next to the in-template figure. Small n; the file says so."""
import argparse
import json
import os

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--model", default="FinanceRateCalc/frc-contract-drift"); a = ap.parse_args()
    rows = [json.loads(l) for l in open(os.path.join(ROOT, "eval", "drift-ood-set.jsonl"), encoding="utf-8")]
    tok = AutoTokenizer.from_pretrained(a.model); model = AutoModelForSequenceClassification.from_pretrained(a.model); model.eval()
    labels = [model.config.id2label[i] for i in range(model.config.num_labels)]
    enc = tok([r["text"] for r in rows], truncation=True, max_length=96, padding=True, return_tensors="pt")
    with torch.no_grad():
        P = torch.sigmoid(model(**enc).logits).numpy()
    pred = [[labels[k] for k in np.where(p >= 0.5)[0]] for p in P]
    viol = [(r, p) for r, p in zip(rows, pred) if r["codes"]]; clean = [(r, p) for r, p in zip(rows, pred) if not r["codes"]]
    per = {}
    for c in sorted({r["codes"][0] for r, _ in viol}):
        xs = [(r, p) for r, p in viol if r["codes"][0] == c]
        per[c] = {"n": len(xs), "right_code": sum(1 for r, p in xs if c in p), "any_flag": sum(1 for r, p in xs if p)}
    # learned reader against the hand-written gate, on the SAME held-out sentences (odd positions; never used to patch the gate)
    gp = os.path.join(ROOT, "eval", "gate-selfplay.json"); head = None
    if os.path.exists(gp):
        g = json.load(open(gp, encoding="utf-8")); gate_missed = {e["text"] for e in g.get("escapes", [])}; gate_fa = {e["text"] for e in g.get("false_alarms", [])}
        ho = [(r, p) for i, (r, p) in enumerate(zip(rows, pred)) if i % 2]
        hv = [(r, p) for r, p in ho if r["codes"]]; hc = [(r, p) for r, p in ho if not r["codes"]]
        head = {"sentences": "held-out half of eval/drift-ood-set.jsonl (odd positions)", "violating": len(hv), "clean": len(hc),
                "gate_caught": sum(1 for r, _ in hv if r["text"] not in gate_missed), "model_caught": sum(1 for _, p in hv if p),
                "either_caught": sum(1 for r, p in hv if p or r["text"] not in gate_missed), "both_missed": [r["text"] for r, p in hv if not p and r["text"] in gate_missed],
                "gate_false_alarms": sum(1 for r, _ in hc if r["text"] in gate_fa), "model_false_alarms": sum(1 for _, p in hc if p),
                "reading": "gate = rules written by hand (worker sentenceFindings, patched from the development half only); model = the published classifier, trained on rule-generated sentences and never on these. 'either' is what a pipeline using both would catch."}
    it = json.load(open(os.path.join(ROOT, "eval", "drift-model-eval.json"), encoding="utf-8"))
    out = {"model": a.model, "set": "eval/drift-ood-set.jsonl", "n_violating": len(viol), "n_clean": len(clean),
           "detection_rate": round(sum(1 for _, p in viol if p) / len(viol), 3), "right_code_rate": round(sum(1 for r, p in viol if r["codes"][0] in p) / len(viol), 3),
           "false_flag_rate_on_clean": round(sum(1 for _, p in clean if p) / len(clean), 3), "per_code": per,
           "in_template_exact_match_for_comparison": it.get("exact_match"),
           "rules_vs_learned_on_held_out": head,
           "misses": [{"text": r["text"], "expected": r["codes"], "predicted": p} for r, p in viol if r["codes"][0] not in p][:40],
           "false_flags": [{"text": r["text"], "predicted": p} for r, p in clean if p],
           "note": "Hand-written sentences outside the rule generator's templates; written by the publisher's assistant, not by independent annotators; one primary code per sentence; small n. This is the number to quote for the model's use on real text, not the in-template figure."}
    json.dump(out, open(os.path.join(ROOT, "eval", "drift-model-ood.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: out[k] for k in ("detection_rate", "right_code_rate", "false_flag_rate_on_clean", "in_template_exact_match_for_comparison", "rules_vs_learned_on_held_out", "per_code")}, indent=1))


if __name__ == "__main__":
    main()
