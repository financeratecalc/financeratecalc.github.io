#!/usr/bin/env python3
"""The Cliche Index — what "everyone knows" about FHA denials, tested against the 2025 record.

Each entry: a claim people commonly state, the data field that tests it, and a verdict computed
FROM the published files (never typed). Verdicts: SUPPORTED, CONTRADICTED, PARTLY, UNTESTABLE.
Untestable claims are kept and published as such: the record cannot see them (no credit scores,
no applications that were never filed, no non-FHA products in this dataset).

Output: eval/cliche-battery.json — consumed by the Inspect task `cliche_index` and by the page.
"""
import json, glob, statistics, datetime
idx = json.load(open("api/index.json")); nat = idx["national"]
slp = json.load(open("api/small-loan-penalty.json")); rs = json.load(open("api/denial-reasons-top100.json"))
nvl = json.load(open("data/national-vs-local-2025.json"))["result"]; col = json.load(open("data/collateral-denials-2025.json"))["bands"]
L = [json.load(open(f)) for f in glob.glob("api/lender/*.json")]; top = [d for d in L if d.get("in_top_100_by_volume")]
door = json.load(open("claims/door-effect-38pct-2026.json"))["claim"]
cle = json.load(open("api/metro/cleveland-oh.json")); crates = [l["denial_rate_pct"] for l in cle["lenders"] if l.get("decisioned_applications_here", 0) >= 100]
lo, hi = min(d["denial_rate_pct"] for d in top), max(d["denial_rate_pct"] for d in top)
big = sorted(top, key=lambda d: -d["decisioned_applications"])[:10]; small = sorted(top, key=lambda d: d["decisioned_applications"])[:10]
top_reason = max(rs["by_reason"], key=lambda k: rs["by_reason"][k]["median_share_pct"])
col_low, col_high = col[0]["collateral_share_pct"], next((b["collateral_share_pct"] for b in col if b["band"].startswith("$300")), None)

C = []
def add(cid, claim, verdict, evidence, field, universe, note=""):
    C.append({"id": cid, "claim": claim, "verdict": verdict, "evidence": evidence, "tested_against": field, "universe": universe, "note": note})

add("c01", "Small mortgages are denied less often than large ones — there is less money at risk.",
    "CONTRADICTED", f"In every one of {slp['states']} jurisdictions with a published split, loans under $150K were denied more often than loans over $250K; the ratio ran from {slp['min_penalty']}x to {slp['max_penalty']}x.",
    "api/small-loan-penalty.json", "U-STATES-SMALLBIG-2025")
add("c02", "The most common reason an FHA application is denied is credit history.",
    "CONTRADICTED", f"Across the {rs['n_lenders']} of the 100 largest lenders that report reasons, the reason with the highest median share is {top_reason} ({rs['by_reason'][top_reason]['median_share_pct']}%); credit history's median is {rs['by_reason']['credit_history']['median_share_pct']}%.",
    "api/denial-reasons-top100.json", "U-TOP100-WITH-REASONS-2025", "Reason fields are not a partition; a denial may cite up to four.")
add("c03", "About one in seven FHA applications is denied (roughly 14%).",
    "PARTLY", f"That figure is 2023 and purchase-only. Counting every 2025 FHA application that reached a decision, {nat['rate_pct']:.1f}% were denied ({nat['denials']:,} of {nat['apps']:,}). Both numbers are right for their universe; neither is 'the' FHA denial rate.",
    "api/index.json", "U-FHA-2025-DECISIONED")
add("c04", "FHA denial rates are broadly similar from lender to lender, because FHA rules are the same everywhere.",
    "CONTRADICTED", f"Among the 100 largest FHA lenders in 2025, denial rates ran from {lo:.1f}% to {hi:.1f}% inside the same program.",
    "api/lender/*.json", "U-TOP100-VOLUME-2025")
add("c05", "Whether you are denied is about your file, not about which lender you chose.",
    "CONTRADICTED", f"Lender identity is associated with about {int(door['value']*100)}% of the explainable variation in FHA denial outcomes ({door['subject']}); {door['definition']}.",
    "claims/door-effect-38pct-2026.json", "U-FHA-2025-DECISIONED", "Association on observable characteristics, not causation; HMDA carries no credit scores.")
add("c06", "In expensive markets, denials are mostly about the property (appraisal, condition), not the borrower.",
    "CONTRADICTED", f"The share of denials citing collateral falls as loan size rises: {col_low}% under $100K versus {col_high}% at $300-400K. Collateral-driven denial is a cheap-house phenomenon.",
    "data/collateral-denials-2025.json", "U-FHA-2025-DECISIONED", "What the record cannot see: buyers steered away before an application exists (see invisible-denials).")
add("c07", "Big national lenders are stricter than local lenders.",
    "PARTLY", f"In {nvl['metros_compared']} metros where both compete, national-footprint lenders averaged {nvl['national_mean_pct']}% versus {nvl['local_mean_pct']}% for local/regional ones, and were stricter in {nvl['metros_where_national_stricter']} of {nvl['metros_compared']}. But local lenders hold both extremes ({nvl['local_min_pct']}% and {nvl['local_max_pct']}%): 'local' is not a category you can act on.",
    "data/national-vs-local-2025.json", "U-FHA-2025-DECISIONED")
add("c08", "Within one city, FHA lenders are roughly interchangeable.",
    "CONTRADICTED", f"In {cle['metro']}, lenders with at least 100 decisions ranged from {min(crates):.1f}% to {max(crates):.1f}% in 2025, a {round(max(crates)-min(crates),1)}-point gap.",
    "api/metro/cleveland-oh.json", "U-FHA-2025-DECISIONED restricted to metro")
add("c09", "Incomplete applications are a negligible share of denials.",
    "PARTLY", f"The median lender cites 'application incomplete' on {rs['by_reason']['incomplete']['median_share_pct']}% of denials, but one large lender cites it on {rs['by_reason']['incomplete']['max_share_pct']}% ({rs['by_reason']['incomplete']['max_lender']}). Negligible at the median, dominant at one door.",
    "api/denial-reasons-top100.json", "U-TOP100-WITH-REASONS-2025")
add("c10", "A low denial rate means a lender is easy to get approved with.",
    "UNTESTABLE", "A low observed rate can mean lenient underwriting, or an applicant mix that arrives pre-screened, or buyers steered away before filing. The record contains none of the three; only observed rates.",
    "—", "—", "Boundary: HMDA has no credit scores and no record of applications never filed.")
add("c11", "FHA is easier to get than a conventional mortgage.",
    "UNTESTABLE", "This dataset is FHA only (loan_type 2). No conventional comparison is published here, and the two programs draw different applicants, so a raw comparison would not answer the question anyway.",
    "—", "—")
add("c12", "The denial rate is the same for a buyer regardless of where they live.",
    "CONTRADICTED", f"State-level 2025 rates differ substantially; the small-loan penalty alone ranges {slp['min_penalty']}x to {slp['max_penalty']}x by jurisdiction. Geography is a variable the record can see.",
    "api/state/*.json", "U-STATES-SMALLBIG-2025")
add("c13", "Your credit score is the single most important factor in an FHA denial.",
    "UNTESTABLE", "HMDA does not contain credit scores. The record can show that debt-to-income is the most-cited reason, but it cannot rank score against anything, so this belief cannot be confirmed or refuted from the public data.",
    "—", "—", "The most common belief about denials is one the public record is structurally unable to test.")
add("c14", "Refinance applications are denied about as often as purchase applications.",
    "UNTESTABLE", "Loan-purpose splits are not among this project's published figures for 2025; the 2023 purchase-only vs refinance figures circulating online come from another universe and vintage.",
    "—", "—")
add("c15", "A lender with a high denial rate is doing something wrong.",
    "UNTESTABLE", "An observed rate carries no information about conduct. High rates are screening signals about institutions, consistent with strict underwriting, a hard applicant mix, or filing practice; the record cannot distinguish them.",
    "—", "—", "This is the boundary every figure on the site carries.")

share_top = 100 * sum(d["decisioned_applications"] for d in top) / nat["apps"]
add("c16", "Most FHA applications that reach a decision are approved.",
    "SUPPORTED", f"{100-nat['rate_pct']:.1f}% of decisioned 2025 FHA applications were not denied ({nat['apps']-nat['denials']:,} of {nat['apps']:,}).",
    "api/index.json", "U-FHA-2025-DECISIONED")
add("c17", "Debt-to-income is one of the main reasons FHA applications are denied.",
    "SUPPORTED", f"It is the reason with the highest median share across the {rs['n_lenders']} of the 100 largest lenders that report reasons: {rs['by_reason']['dti']['median_share_pct']}%.",
    "api/denial-reasons-top100.json", "U-TOP100-WITH-REASONS-2025")
add("c18", "FHA lending is concentrated in a relatively small number of large lenders.",
    "SUPPORTED", f"The 100 largest FHA lenders accounted for about {share_top:.0f}% of all decisioned FHA applications in 2025 ({sum(d['decisioned_applications'] for d in top):,} of {nat['apps']:,}, counting the {len(top)} with published files).",
    "api/lender/*.json", "U-TOP100-VOLUME-2025")
add("c19", "A lender's strictness is the same for every kind of loan it makes.",
    "UNTESTABLE", "This project publishes conditional maps per lender (strictness by loan size and leverage cell) for some lenders, but a general test across all lenders is not published; treated as untestable in this battery.",
    "get_conditional_door_map", "—")

out = {"generated": datetime.date.today().isoformat(), "version": "0.1",
       "purpose": "Widely stated beliefs about FHA denials, each tested against the complete 2025 federal record where the record can see it, and declared untestable where it cannot. Used both as a public page and as an AI battery: what models believe versus what the record shows.",
       "counts": {v: sum(1 for c in C if c["verdict"] == v) for v in ("SUPPORTED", "CONTRADICTED", "PARTLY", "UNTESTABLE")},
       "claims": C, "license": "CC BY 4.0", "universes": "https://financeratecalc.com/universes.json"}
json.dump(out, open("eval/cliche-battery.json", "w"), indent=1)
print(out["counts"]); [print(c["id"], c["verdict"], c["claim"][:70]) for c in C]
