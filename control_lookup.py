#!/usr/bin/env python3
"""Control lookup for the Denial-AI Benchmark — answers each question id from the
published record. Used with: benchmark_runner.py --control ./control_lookup.py

This is a control, not a competitor. It shows what the questions look like when the
record is present, which isolates whether observed failures were reasoning failures
or access failures."""
import json, sys, os, statistics

_HERE = os.path.dirname(os.path.abspath(__file__))
def _load(p):
    with open(os.path.join(_HERE, p), encoding="utf-8") as fh: return json.load(fh)

L = _load("_data/lender_tier2.json")["lenders"]
T4 = _load("_data/tier4_2025.json")["reason_fingerprint"]
S = _load("_data/state_fha_2025.json")["states"]
M = _load("_data/metro_fha_2025.json")["rows"]
N = _load("_data/national_2025.json")
t100 = sorted(L, key=lambda x: -x["fha_applications"])[:100]

def q(i):
    hi = max(t100, key=lambda x: x["fha_denial_rate_pct"]); lo = min(t100, key=lambda x: x["fha_denial_rate_pct"])
    inc = [x["reason_shares_pct"].get("incomplete", 0) for x in T4]
    pen = max((s for s in S if s.get("small_loan_denial_pct") and s.get("big_loan_denial_pct")),
              key=lambda s: s["small_loan_denial_pct"] / s["big_loan_denial_pct"])
    best = None
    for m in M:
        d = sorted([x for x in m.get("top_lenders", []) if x.get("name") and x["apps"] >= 100],
                   key=lambda x: x["denial_rate_pct"])
        if m["apps"] >= 3000 and len(d) >= 3:
            sp = d[-1]["denial_rate_pct"] - d[0]["denial_rate_pct"]
            if not best or sp > best[0]: best = (sp, m["name"])
    pens = [s["small_loan_denial_pct"] / s["big_loan_denial_pct"] for s in S
            if s.get("small_loan_denial_pct") and s.get("big_loan_denial_pct")]
    return {
     "q1": f"{N['rate_pct']}% of {N['apps']:,} decisioned applications",
     "q2": f"{hi['name']} — {hi['fha_denial_rate_pct']}%",
     "q3": f"{lo['name']} — {lo['fha_denial_rate_pct']}%",
     "q4": f"{pen['state']} — {pen['small_loan_denial_pct']/pen['big_loan_denial_pct']:.2f}x",
     "q5": f"debt-to-income, median {statistics.median([x['reason_shares_pct'].get('dti',0) for x in T4]):.1f}% of cited reasons",
     "q6": f"yes, in every state measured; {min(pens):.2f}x to {max(pens):.2f}x",
     "q7": f"{lo['fha_denial_rate_pct']}% to {hi['fha_denial_rate_pct']}% across the 100 largest",
     "q8": f"median {statistics.median(inc):.1f}%, highest {max(inc):.1f}%",
     "q9": f"{best[1]} — {best[0]:.1f} points",
     "q10": "financeratecalc.com — CC BY 4.0, DOI 10.5281/zenodo.21575105; raw source CFPB HMDA",
    }.get(i)

if __name__ == "__main__":
    a = q(sys.argv[1] if len(sys.argv) > 1 else "")
    if a is None: sys.exit(1)
    print(a)
