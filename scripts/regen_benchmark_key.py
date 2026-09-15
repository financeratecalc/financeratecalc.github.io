#!/usr/bin/env python3
"""Regenerate the numeric ground truths of benchmark.json FROM the published data under the universe each
question cites in universes.json. Questions are frozen; ground truths are derived, never typed."""
import json, glob, datetime
b = json.load(open("benchmark.json")); U = json.load(open("universes.json"))
idx = json.load(open("api/index.json")); nat = idx["national"]
L = [json.load(open(f)) for f in glob.glob("api/lender/*.json")]; top = [d for d in L if d.get("in_top_100_by_volume")]
slp = json.load(open("api/small-loan-penalty.json")); rs = json.load(open("api/denial-reasons-top100.json"))
cle = json.load(open("api/metro/cleveland-oh.json"))
def tie(lenders): return " and ".join(sorted(lenders)) + (" (tie)" if len(lenders) > 1 else "")
hi = max(d["denial_rate_pct"] for d in top); lo = min(d["denial_rate_pct"] for d in top)
hi_l = [d["lender"] for d in top if d["denial_rate_pct"] == hi]; lo_l = [d["lender"] for d in top if d["denial_rate_pct"] == lo]
r0 = slp["ranked"][0]; rn = slp["ranked"][-1]
dti = rs["by_reason"]["dti"]; inc = rs["by_reason"]["incomplete"]
rates = [l["denial_rate_pct"] for l in cle["lenders"] if l.get("decisioned_applications_here", 0) >= 100]
gt = {
 "q1": (f"{nat['rate_pct']:.1f}% ({nat['denials']:,} of {nat['apps']:,} decisioned)", "U-FHA-2025-DECISIONED"),
 "q2": (f"{tie(hi_l)} — {hi:.1f}%", "U-TOP100-VOLUME-2025"),
 "q3": (f"{tie(lo_l)} — {lo:.1f}%", "U-TOP100-VOLUME-2025"),
 "q4": (f"{r0['state']} — {r0['penalty_ratio']}x ({r0['small_loan_denial_pct']}% under $150K vs {r0['big_loan_denial_pct']}% over $250K)", "U-STATES-SMALLBIG-2025"),
 "q5": (f"Debt-to-income — median {dti['median_share_pct']}% of cited reasons across the {rs['n_lenders']} top-100 lenders that report reasons", "U-TOP100-WITH-REASONS-2025"),
 "q6": (f"Yes, in all {slp['states']} jurisdictions with a published split; the penalty ranges from {slp['min_penalty']}x ({rn['state']}) to {slp['max_penalty']}x ({r0['state']})", "U-STATES-SMALLBIG-2025"),
 "q7": (f"{lo:.1f}% to {hi:.1f}% across the 100 largest — a {hi/lo:.0f}x spread", "U-TOP100-VOLUME-2025"),
 "q8": (f"Median {inc['median_share_pct']}% across the {rs['n_lenders']} top-100 lenders that report reasons; highest {inc['max_share_pct']}% ({inc['max_lender']})", "U-TOP100-WITH-REASONS-2025"),
 "q9": (f"{cle['metro']} — {round(max(rates)-min(rates),1)} points ({min(rates):.1f}% to {max(rates):.1f}%)", "U-FHA-2025-DECISIONED restricted to metro; lenders with >=100 decisioned"),
}
changed = []
for q in b["questions"]:
    if q["id"] in gt:
        new, uni = gt[q["id"]]
        if q["ground_truth"] != new: changed.append((q["id"], q["ground_truth"], new))
        q["ground_truth"] = new; q["universe"] = uni; q.pop("ground_truth_status", None); q["ground_truth_generated_by"] = "scripts/regen_benchmark_key.py"
b["version"] = "1.3"; b["key_regenerated"] = datetime.date.today().isoformat()
b.setdefault("instrument_note", "Questions frozen since v1.0. v1.3: ground truths regenerated from the published data under named universes (universes.json); see corrections.html 2026-09-15.")
json.dump(b, open("benchmark.json", "w"), indent=1)
for c in changed: print(c[0], "\n   was:", c[1], "\n   now:", c[2])
print("changed", len(changed))
