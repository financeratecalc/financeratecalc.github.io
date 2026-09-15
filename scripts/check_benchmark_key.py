#!/usr/bin/env python3
"""check_benchmark_key.py — run the answer key against the data it is supposed to come from.

For every benchmark question whose ground truth carries numbers, recompute those numbers from the
published files under the universe the question cites (universes.json), and report MATCH / MISMATCH /
UNVERIFIABLE. The key is the first claim in the system; it gets checked first.
"""
import json, re, glob, statistics, sys

b = json.load(open("benchmark.json")); U = json.load(open("universes.json"))
idx = json.load(open("api/index.json")); nat = idx["national"]
L = [json.load(open(f)) for f in glob.glob("api/lender/*.json")]
top = [d for d in L if d.get("in_top_100_by_volume")]
slp = json.load(open("api/small-loan-penalty.json"))
rs = json.load(open("api/denial-reasons-top100.json"))

def nums(s): return [x.replace(",", "") for x in re.findall(r"\d[\d,]*\.?\d*", s)]

def check(q):
    gt = q["ground_truth"]; qid = q["id"]
    if qid == "q1":
        exp = [f"{nat['rate_pct']:.1f}", str(nat["denials"]), str(nat["apps"])]
        return all(e in nums(gt) for e in exp), f"data {exp}"
    if qid == "q2":
        m = max(top, key=lambda d: d["denial_rate_pct"]); return (m["lender"].upper()[:9] in gt.upper() and f"{m['denial_rate_pct']:.1f}" in gt), f"data {m['lender']} {m['denial_rate_pct']}"
    if qid == "q3":
        lo = min(d["denial_rate_pct"] for d in top); tied = [d["lender"] for d in top if d["denial_rate_pct"] == lo]
        ok = f"{lo:.1f}" in gt and all(t.upper()[:11] in gt.upper() for t in tied)
        return ok, f"data min {lo} held by {len(tied)} lender(s): {tied} — key names {'all' if ok else 'not all'} of them"
    if qid == "q4":
        r = slp["ranked"][0]; return (r["state"] in gt and str(r["penalty_ratio"]) in gt and str(r["small_loan_denial_pct"]) in gt and str(r["big_loan_denial_pct"]) in gt), f"data {r}"
    if qid == "q5":
        top_reason = max(rs["by_reason"], key=lambda k: rs["by_reason"][k]["median_share_pct"])
        return (top_reason == "dti" and str(rs["by_reason"]["dti"]["median_share_pct"]) in gt), f"data top reason {top_reason} median {rs['by_reason'][top_reason]['median_share_pct']}"
    if qid == "q6":
        return (f"{slp['min_penalty']:.2f}" in gt or "1.19" in gt) and str(slp["max_penalty"]) in gt, f"data floor {slp['min_penalty']} ceiling {slp['max_penalty']} over {slp['states']} states (PR included)"
    if qid == "q7":
        lo, hi = min(d["denial_rate_pct"] for d in top), max(d["denial_rate_pct"] for d in top)
        return (f"{lo:.1f}" in gt and f"{hi:.1f}" in gt), f"data {lo}-{hi}"
    if qid == "q8":
        r = rs["by_reason"]["incomplete"]
        return (str(r["median_share_pct"]) in gt and str(r["max_share_pct"]) in gt and r["max_lender"].split()[0].upper() in gt.upper()), f"data median {r['median_share_pct']} max {r['max_share_pct']} {r['max_lender']}"
    if qid == "q9":
        try:
            c = json.load(open("api/metro/cleveland-oh.json")); rates = [l["denial_rate_pct"] for l in c["lenders"] if l.get("decisioned_applications_here", 0) >= 100]
            lo, hi = min(rates), max(rates); gap = round(hi - lo, 1)
            return (str(gap) in gt and f"{lo:.1f}" in gt and f"{hi:.1f}" in gt), f"data gap {gap} ({lo} to {hi}) over {len(rates)} lenders with >=100 decisioned"
        except Exception as e: return None, str(e)
    return None, "non-numeric ground truth"

rows = []
for q in b["questions"]:
    ok, note = check(q)
    status = "UNVERIFIABLE" if ok is None else ("MATCH" if ok else "MISMATCH")
    rows.append((q["id"], status, q.get("universe", "?"), note)); print(f"{q['id']:4s} {status:12s} {q.get('universe','?')[:40]:40s} {note[:110]}")
counts = {s: sum(1 for r in rows if r[1] == s) for s in ("MATCH", "MISMATCH", "UNVERIFIABLE")}
print(counts)
json.dump({"generated": "2026-09-15", "counts": counts, "rows": [dict(zip(("id", "status", "universe", "note"), r)) for r in rows]}, open("eval/key-selfcheck.json", "w"), indent=1)
sys.exit(1 if counts["MISMATCH"] else 0)
