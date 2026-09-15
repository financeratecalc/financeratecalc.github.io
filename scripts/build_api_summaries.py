#!/usr/bin/env python3
"""Generate api/small-loan-penalty.json and api/denial-reasons-top100.json FROM api/state/*.json and api/lender/*.json.
Nothing typed by hand. Re-run after any data refresh."""
import json, glob, statistics, datetime
today = datetime.date.today().isoformat()
# 1. small-loan penalty by state
rows = []
for f in sorted(glob.glob("api/state/*.json")):
    d = json.load(open(f))
    if d.get("small_loan_penalty") is None: continue
    rows.append({"state": d["state"], "small_loan_denial_pct": d["small_loan_denial_pct"], "big_loan_denial_pct": d["big_loan_denial_pct"],
                 "penalty_ratio": d["small_loan_penalty"], "denial_rate_pct": d["denial_rate_pct"], "decisioned_applications": d["decisioned_applications"]})
rows.sort(key=lambda r: -r["penalty_ratio"])
meta = json.load(open(glob.glob("api/state/*.json")[0])).get("meta", {})
json.dump({"generated": today, "definition": "small = loan amount under $150,000; big = over $250,000; penalty_ratio = small-loan denial rate / big-loan denial rate; FHA (loan_type 2), decisioned applications (actions 1,2,3), HECM excluded, 2025",
           "states": len(rows), "all_states_penalty_above_1": all(r["penalty_ratio"] > 1 for r in rows),
           "min_penalty": min(r["penalty_ratio"] for r in rows), "max_penalty": max(r["penalty_ratio"] for r in rows),
           "ranked": rows, "meta": meta, "source_files": "api/state/{xx}.json", "license": "CC BY 4.0"}, open("api/small-loan-penalty.json", "w"), indent=1)
# 2. denial reason shares across the top-100 lenders
lenders = []
for f in sorted(glob.glob("api/lender/*.json")):
    d = json.load(open(f))
    if d.get("in_top_100_by_volume") and d.get("denial_reason_shares_pct"):
        lenders.append({"lender": d["lender"], "slug": d["slug"], "shares": d["denial_reason_shares_pct"], "denial_rate_pct": d["denial_rate_pct"], "decisioned_applications": d["decisioned_applications"]})
reasons = sorted({k for l in lenders for k in l["shares"]})
summary = {}
for r in reasons:
    vals = [(l["shares"][r], l["lender"]) for l in lenders if r in l["shares"]]
    summary[r] = {"median_share_pct": round(statistics.median(v for v, _ in vals), 1), "max_share_pct": max(vals)[0], "max_lender": max(vals)[1], "n_lenders": len(vals)}
json.dump({"generated": today, "universe": "100 largest FHA lenders by 2025 decisioned volume; reason fields are not a partition, shares need not sum to 100",
           "n_lenders": len(lenders), "by_reason": summary, "lenders": lenders, "source_files": "api/lender/{slug}.json", "license": "CC BY 4.0"}, open("api/denial-reasons-top100.json", "w"), indent=1)
print("states", len(rows), "top penalty", rows[0]["state"], rows[0]["penalty_ratio"], rows[0]["small_loan_denial_pct"], rows[0]["big_loan_denial_pct"], "| min", min(r["penalty_ratio"] for r in rows))
print("lenders", len(lenders), "| incomplete median", summary.get("incomplete", {}).get("median_share_pct"), "max", summary.get("incomplete", {}).get("max_share_pct"), summary.get("incomplete", {}).get("max_lender"))
