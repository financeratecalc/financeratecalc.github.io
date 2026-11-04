#!/usr/bin/env python3
"""Release-day step 2: turn frc_rebuild.json (scripts/reference_implementation.py on a CFPB file) into the site's
data files — api/index.json, api/lender/<slug>.json, api/state/<xx>.json, api/metro/<slug>.json — in the schema the
published files use, under an output directory. Nothing is typed by hand; names and slugs come from
data/release-day-registry.json (new LEIs fall back to GLEIF legal names, new MSA codes to the code).

    python3 scripts/materialize_rebuild.py <frc_rebuild.json> --year 2025 --out <dir>

Dry run on the 2025 file: the output must equal the committed api/ files (scripts/compare_tree.py reports every
difference). On release day for a new year the same command writes the new files, and the rest of the site
(claims, contracts, pages, bundle) is rebuilt from them by the existing builders.
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://financeratecalc.com"
REASONS = {"1": "dti", "2": "employment", "3": "credit_history", "4": "collateral", "5": "insufficient_cash", "6": "unverifiable_info",
           "7": "incomplete", "8": "mortgage_insurance_denied", "9": "other"}


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def meta(year, n, rate):
    return {"source": f"CFPB Home Mortgage Disclosure Act {year}", "publisher": "FinanceRateCalc",
            "universe": "FHA applications (loan_type 2) reaching a credit decision (action_taken 1,2,3), excluding reverse mortgages; denial = action 3",
            "n": n, "national_denial_rate_pct": rate, "method": f"{BASE}/methodology.html", "license": "CC BY 4.0",
            "dataset_doi": "10.5281/zenodo.21575105", "verification_status": "reproducible; not independently reproduced",
            "verify": f"{BASE}/reconciliation.html",
            "caveat": "Historical observations about institutions. Not ratings, not recommendations, not predictions about any individual application. Rates reflect applicant composition as well as lender practice."}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rebuild")
    ap.add_argument("--year", default="2025")
    ap.add_argument("--out", required=True)
    ap.add_argument("--panel", choices=["fresh", "frozen"], default="fresh",
                    help="fresh: the 100 largest by decisioned volume in this file (release day). frozen: the lenders in the registry (the published 2025 panel, whose membership was fixed on the pre-correction file; 5 lenders at the margin differ from a fresh cut).")
    a = ap.parse_args()
    rb = json.load(open(a.rebuild, encoding="utf-8"))
    reg = json.load(open(os.path.join(ROOT, "data", "release-day-registry.json"), encoding="utf-8"))
    gleif = {}
    try:
        gleif = {k: (v.get("legal_name") if isinstance(v, dict) else v) for k, v in json.load(open(os.path.join(ROOT, "data", "lei-names.json"))).get("names", {}).items()}
    except FileNotFoundError:
        pass
    nat = rb["national"]
    N, D = nat["apps"], nat["denials"]
    rate2 = round(100 * D / N, 2)
    M = meta(a.year, N, rate2)
    out = a.out
    for sub in ("lender", "state", "metro"):
        os.makedirs(os.path.join(out, "api", sub), exist_ok=True)

    # ---- lenders: the 100 largest by decisioned volume carry a page; reason shares and peer-adjusted figures join by LEI
    lenders = sorted(rb["lenders"], key=lambda x: -x["apps"])
    top100 = [x for x in lenders if x["lei"] in reg["lenders"]] if a.panel == "frozen" else lenders[:100]
    panel = {x["lei"] for x in top100}
    fps = {f["lei"]: f for f in rb.get("fingerprints", [])}
    adj = {x["lei"]: x for x in rb.get("adjusted", [])}
    peer_rate = round(statistics.median(x["rate"] for x in top100), 1)
    peer_med = {}
    fps = {k: v for k, v in fps.items() if k in panel}
    for r in ("dti", "credit_history", "collateral", "insufficient_cash", "incomplete", "unverifiable_info", "employment", "other"):
        vals = [f["reason_shares_pct"].get(r, 0.0) for f in fps.values()]
        if vals:
            peer_med[r] = round(statistics.median(vals), 1)
    peer_med["denial_rate_pct"] = peer_rate
    if a.panel == "frozen":
        # the published 2025 peer medians were fixed in July on the pre-correction fingerprint set; a frozen panel keeps them
        try:
            peer_med = json.load(open(os.path.join(ROOT, "api", "index.json")))["national"]["peer_medians"]
            peer_rate = peer_med["denial_rate_pct"]
        except (FileNotFoundError, KeyError):
            pass
    index_lenders = []
    for x in top100:
        lei = x["lei"]
        r = reg["lenders"].get(lei) or {}
        name = r.get("lender") or gleif.get(lei) or lei
        slug = r.get("slug") or slugify(name)
        L = {"lender": name, "lei": lei, "slug": slug, "decisioned_applications": x["apps"], "denials": x["denials"], "denial_rate_pct": x["rate"],
             "approval_rate_pct": round(100 - x["rate"], 1), "peer_median_denial_rate_pct": peer_rate, "in_top_100_by_volume": True}
        A = adj.get(lei)
        L.update({"peer_adjusted_ratio": A["adjusted_ratio"] if A else None, "expected_denial_rate_pct": A["expected_rate_pct"] if A else None,
                  "profile_coverage_pct": A["profile_coverage_pct"] if A else None})
        if lei in fps:
            sh = fps[lei]["reason_shares_pct"]
            L["denial_reason_shares_pct"] = sh
            L["deviation_from_peer_median_pts"] = {k: round(sh.get(k, 0.0) - peer_med[k], 1) for k in peer_med if k != "denial_rate_pct"}
        L["page"] = r.get("page") or f"{BASE}/{slug}-fha-denial-rate.html"
        L["meta"] = M
        json.dump(L, open(os.path.join(out, "api", "lender", slug + ".json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        index_lenders.append({"lender": name, "slug": slug, "denial_rate_pct": x["rate"], "decisioned_applications": x["apps"], "url": f"{BASE}/api/lender/{slug}.json"})

    # ---- states
    index_states = []
    for s in sorted(rb["states"], key=lambda x: -x["apps"]):
        sm, bg = s.get("small_loan_denial_pct"), s.get("big_loan_denial_pct")
        S = {"state": s["state"], "decisioned_applications": s["apps"], "denials": s["denials"], "denial_rate_pct": s["denial_rate_pct"],
             "national_denial_rate_pct": rate2, "small_loan_denial_pct": sm, "big_loan_denial_pct": bg,
             "small_loan_penalty": round(sm / bg, 2) if sm and bg else None, "meta": M}
        json.dump(S, open(os.path.join(out, "api", "state", s["state"].lower() + ".json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        index_states.append({"state": s["state"], "denial_rate_pct": s["denial_rate_pct"], "url": f"{BASE}/api/state/{s['state'].lower()}.json"})

    # ---- metros
    index_metros = []
    for m in sorted(rb["metros"], key=lambda x: -x["apps"]):
        code = str(m["msa"])
        r = reg["metros"].get(code) or {}
        name = r.get("metro") or f"MSA {code}"
        slug = r.get("slug") or slugify(name)
        cells = []
        for c in sorted(m.get("top_lenders", []), key=lambda c: (c["denial_rate_pct"], -c["apps"])):
            if c["lei"] not in panel:
                continue   # the metro table names only lenders that have a page (the panel)
            lr = reg["lenders"].get(c["lei"]) or {}
            cells.append({"lender": lr.get("lender") or gleif.get(c["lei"]) or c["lei"], "decisioned_applications_here": c["apps"], "denial_rate_pct": c["denial_rate_pct"]})
        sm, bg = m.get("small_denial_pct"), m.get("big_denial_pct")
        rates = [c["denial_rate_pct"] for c in cells]
        T = {"metro": name, "msa_code": code, "slug": slug, "decisioned_applications": m["apps"], "denials": m["denials"], "denial_rate_pct": m["denial_rate_pct"],
             "national_denial_rate_pct": rate2, "small_loan_denial_pct": sm, "big_loan_denial_pct": bg, "small_loan_penalty": round(sm / bg, 2) if sm and bg else None,
             "lenders": cells, "spread_between_lenders_pts": round(max(rates) - min(rates), 1) if len(rates) >= 2 else None,
             "page": r.get("page") or f"{BASE}/metro/{slug}.html", "meta": M}
        json.dump(T, open(os.path.join(out, "api", "metro", slug + ".json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        index_metros.append({"metro": name, "slug": slug, "denial_rate_pct": m["denial_rate_pct"], "decisioned_applications": m["apps"], "url": f"{BASE}/api/metro/{slug}.json"})

    idx = {"national": {"apps": N, "denials": D, "rate_pct": rate2, "hecm_excluded": nat.get("hecm_excluded"), "peer_medians": peer_med},
           "endpoints": {"lender": f"{BASE}/api/lender/{{slug}}.json", "metro": f"{BASE}/api/metro/{{slug}}.json", "state": f"{BASE}/api/state/{{two-letter-code}}.json", "index": f"{BASE}/api/index.json"},
           "counts": {"lenders": len(index_lenders), "metros": len(index_metros), "states": len(index_states)},
           "lenders": index_lenders, "metros": index_metros, "states": index_states, "meta": M}
    json.dump(idx, open(os.path.join(out, "api", "index.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"materialized: national {N:,} / {D:,} = {rate2}%; {len(index_lenders)} lenders, {len(index_states)} states, {len(index_metros)} metros -> {out}/api")


if __name__ == "__main__":
    main()
