#!/usr/bin/env python3
"""Build data/citable.json from receipts only, and data/citable-queue.json for everything that is not citable yet.

Rule: a statement is listed as citable only if every figure in it is a receipted claim. Each entry is built from
claims/<id>.json and checked against the record itself: the claim is resolved again from the site's data
(Verifier.claim_object, the same code /verify uses offline), its hash recomputed, and the figure in the sentence
compared with the receipt. Nothing is computed or guessed by a model. Statements that were offered as citable before
2026-11-28 without receipts are kept in the queue with a status and a reason, and safe_to_cite false.

    python3 scripts/build_citable.py [--check]
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "rl-env"))
from frc_citation.verify_offline import Verifier, sha8  # noqa: E402

BASE = "https://financeratecalc.com"
OUT = os.path.join(ROOT, "data", "citable.json")
QUEUE = os.path.join(ROOT, "data", "citable-queue.json")
NATIONAL = "national-fha-denial-rate-2025"
LENDERS = [  # the eleven lenders the earlier file listed; alphabetical, no rank
    ("CrossCountry Mortgage", "crosscountry-mortgage", "crosscountry"), ("Freedom Mortgage", "freedom-mortgage", "freedom"),
    ("Guild Mortgage", "guild-mortgage", "guild"), ("loanDepot", "loandepotcom", "loandepot"),
    ("Mr. Cooper (Nationstar Mortgage)", "nationstar-mortgage", "mr-cooper"), ("NewRez", "newrez", "newrez"),
    ("PennyMac", "pennymac-loan-services", "pennymac"), ("Planet Home Lending", "planet-home-lending", "planet-home"),
    ("Rocket Mortgage", "rocket-mortgage", "rocket"), ("United Wholesale Mortgage", "united-wholesale-mortgage", "uwm"),
    ("Wells Fargo", "wells-fargo-bank", "wells-fargo")]
# Wording a citable statement may not carry: it would turn an aggregate into a statement about one file or a choice.
BANNED = re.compile(r"\b(?:identical (?:borrower|profile)s?|same borrower|predicts?|your odds|approval odds|best lender|should choose|"
                    r"lender choice|profiles? like yours|will (?:deny|approve))\b", re.I)
LIMITS = ["A historical aggregate of decisioned FHA applications (originated, approved not accepted, denied), 2025; not a prediction for any one application.",
          "A lender's rate describes the applications it received, including their mix; it is not a measure of how it treats borrowers and not a reason to choose or avoid it."]

# What the file offered before 2026-11-28, with what happened to each statement. Kept verbatim so a reader who cited one can find it.
QUEUED = [
    ("In 2025, FHA denial rates across 11 major lenders ranged from 6.5% (CrossCountry, lowest) to 52.3% (NewRez, highest) — an ~8x spread on the same federal loan program.", "/fha-denial-rates-by-lender.html",
     "retired", "CONTRADICTS_RECEIPT", "Both ends disagree with the receipted rates (CrossCountry 6.2%, NewRez 52.8%). Replaced by the receipted range in data/citable.json."),
    ("The lender with the HIGHEST 2025 FHA denial rate among major originators is NewRez at 52.3%. The lowest is CrossCountry at 6.5%.", "/fha-denial-rates-by-lender.html",
     "retired", "CONTRADICTS_RECEIPT", "Same figures as above; the receipted rates are 52.8% and 6.2%."),
    ("The deepest single denial cell in 2025 FHA records: Rocket Mortgage, DTI 48-50 x CLTV 90-95%, 97.6% denial rate (n=84).", "/black-hole-report.html",
     "retired", "NOT_REPRODUCIBLE", "Computed once by a script that is not published; the highest of many small cells. See /black-hole-lender.html (provisional research note)."),
    ("FRC Denial Climate Index 2025: 54.3/100 (NEUTRAL). 2023 was the tightest credit year of the era at 66/100; 2021 the loosest at 21/100 — a 3x climate difference for an identical borrower.", "/climate.html",
     "needs_reproduction", "RECEIPT_MISSING", "A composite index without a published computation or receipt; 'for an identical borrower' states something an index of many applications cannot show."),
    ("At the median first-time-buyer down payment (10%, CLTV 90-94), the denial spread between major FHA lenders is ~79 percentage points (16.5% to 95.2%) — versus ~16 points at 20% down. Lower down payment makes lender choice ~5x more consequential.", "/lender-response-surface.html",
     "retired", "LANGUAGE", "Frames a spread between lenders' applicant pools as the value of choosing a lender; figures not receipted."),
    ("Lender DTI cliffs differ sharply: one major lender's denial rate jumps ~+15 percentage points across DTI 44-45, while another's moves only +1.4pp.", "/lender-response-surface.html",
     "needs_reproduction", "RECEIPT_MISSING", "Cell-level figures without receipts, cell sizes or the number of cells compared."),
    ("Texas home prices turned negative in 2026 (-0.1% YoY) for the first time in the FHFA state series, while California sits near-flat (+0.8%).", "/geographic-lottery.html",
     "needs_reproduction", "RECEIPT_MISSING", "An FHFA figure without the release, quarter or receipt; 'for the first time in the series' not shown."),
    ("FHA denial rates predict FHA delinquency rates two years ahead (r=+0.618).", "/mortgage-correlation-research.html",
     "needs_reproduction", "RECEIPT_MISSING", "A correlation without its n, series, years or method; 'predict' claims more than a correlation shows."),
    ("Unemployment correlates inversely with mortgage denial rates (r=-0.696) — the Recession Paradox.", "/mortgage-correlation-research.html",
     "needs_reproduction", "RECEIPT_MISSING", "A correlation without its n, series, years or method."),
    ("Fed SLOOS survey responses show near-zero correlation with actual HMDA denial behavior (r=-0.150).", "/mortgage-correlation-research.html",
     "needs_reproduction", "RECEIPT_MISSING", "A correlation without its n, series, years or method."),
    ("Rocket Mortgage's FHA denial rate jumps +54.9pp above 85% LTV; Mr. Cooper's jumps +1.7pp (2025 HMDA).", "/lender-response-surface.html",
     "needs_reproduction", "RECEIPT_MISSING", "Cell-level figures without receipts or cell sizes; part of a jump above 85% can be program limits (see /corrections.html#2026-11-28-legacy-research-pages)."),
    ("Identical high-risk FHA profiles face 26.7% denial at Mr. Cooper vs 91.2% at Rocket — a 64.5pp spread.", "/mortgage-correlation-research.html",
     "retired", "LANGUAGE", "Presents two lenders' applicant pools as the same applicant; figures not receipted."),
    ("Shock Beta: pre-shock volatility predicted lender tightening response at r=+0.946; placebo easing episode confirmed at r=-0.605.", "/shock-beta.html",
     "retired", "NOT_REPRODUCIBLE", "The scores do not reproduce from their own data file (see /corrections.html#2026-11-28-legacy-research-pages)."),
    ("UWM's FHA denial rate rose from 16.2% (2022) to 21.8% (2025) — a 35% increase.", "/lender-stress-index.html",
     "retired", "CONTRADICTS_RECEIPT", "The receipted 2025 rate is 21.4%; the 2022 figure has no receipt."),
    ("Lender table: CrossCountry 6.5, Guild 8.6, Planet Home 18.4, UWM 21.8, Freedom 24.2, PennyMac 24.5, Mr. Cooper 25.8, Rocket 31.0, loanDepot 37.8, Wells Fargo 47.2, NewRez 52.3 (percent, 2025, with a rank of 11).", "/fha-denial-rates-by-lender.html",
     "retired", "CONTRADICTS_RECEIPT", "Every one of the eleven rates differed from its receipt, by up to 4.3 points (Freedom 24.2 vs 19.9); replaced by the receipted rates in data/citable.json, alphabetical and without a rank."),
]


def entry(v, cid, text_fn):
    cur, obj = v.claim_object(cid)
    doc = json.load(open(os.path.join(ROOT, "claims", cid + ".json"), encoding="utf-8"))
    h = sha8(obj)
    if doc["hash8"] != h or doc["display_value"] != cur:
        raise SystemExit(f"{cid}: claim document disagrees with the record (hash {doc['hash8']} vs {h}, value {doc['display_value']} vs {cur}); run scripts/build_claim_documents.py")
    return cur, obj, {"claim_id": doc["passport_id"], "text": text_fn(cur, obj), "value": cur, "period": obj.get("period", "2025"),
                      "receipt": doc["receipt"], "verify_url": doc["verify_url"], "claim_url": doc["canonical_url"],
                      "reproduce": doc.get("reproduce"), "verification_status": "verified", "safe_to_cite": True}


def build():
    v = Verifier(ROOT)
    stats = []
    _, nobj, e = entry(v, NATIONAL, lambda cur, o: f"In 2025, {cur} of decisioned FHA applications reported under HMDA were denied (all reporting lenders, reverse mortgages excluded).")
    e["limitations"] = [LIMITS[0]]
    stats.append(e)
    rates = []
    for name, slug, page in LENDERS:
        cur, obj, e = entry(v, f"lender-{slug}-2025", lambda cur, o, name=name: f"{name}: {cur} of its {o['n']:,} decisioned FHA applications in 2025 were denied.")
        e.update({"lender": name, "applications": obj["n"], "url": f"{BASE}/{page}-fha-denial-rate.html", "limitations": LIMITS})
        stats.append(e); rates.append((float(cur.rstrip("%")), name, cur, e))
    lo, hi = min(rates), max(rates)
    stats.insert(1, {"claim_id": None, "derived_from": [lo[3]["claim_id"], hi[3]["claim_id"]],
                     "text": f"Among these eleven large FHA lenders, 2025 denial rates ranged from {lo[2]} ({lo[1]}) to {hi[2]} ({hi[1]}).",
                     "receipts": [lo[3]["receipt"], hi[3]["receipt"]], "verification_status": "verified", "safe_to_cite": True,
                     "limitations": LIMITS})
    for s in stats:
        if BANNED.search(s["text"]):
            raise SystemExit(f"banned wording in a citable statement: {s['text']}")
    doc = {"source": "FinanceRateCalc — financeratecalc.com",
           "publisher": {"name": "FinanceRateCalc", "contact": "press@financeratecalc.com",
                         "description": "Independent analysis of the public federal HMDA record and of official mortgage reports. No ads, no affiliates, no lender money."},
           "rule": "Every statement here is built from receipted claims only, and each receipt is checked against the record when this file is built. A statement without a receipt is not listed here; it is in citable-queue.json with safe_to_cite false.",
           "license": "CC BY 4.0. Cite with the receipt: it lets a reader check the figure and see if it was later corrected.",
           "dataset_basis": "CFPB/FFIEC HMDA public record 2025, FHA (loan_type 2), decisioned applications (action_taken 1, 2, 3), reverse mortgages excluded.",
           "methodology_url": f"{BASE}/methodology.html", "verify": f"{BASE}/verify.html", "corrections": f"{BASE}/corrections.json",
           "queue": f"{BASE}/data/citable-queue.json",
           "statistics": stats}
    queue = {"about": "Statements this site offered as citable before 2026-11-28 without receipts, kept so that anyone who cited one can see what happened to it. None of them is safe to cite. needs_reproduction: may come back once recomputed by a published script with a receipt. retired: will not come back in this form.",
             "corrections_entry": f"{BASE}/corrections.html#2026-11-28-citable-receipts-only",
             "items": [{"text": t, "url": BASE + u, "status": st, "reason_code": rc, "reason": r, "safe_to_cite": False} for t, u, st, rc, r in QUEUED]}
    return doc, queue


def main():
    check = "--check" in sys.argv
    doc, queue = build()
    changed = []
    for path, obj in ((OUT, doc), (QUEUE, queue)):
        text = json.dumps(obj, indent=1, ensure_ascii=False) + "\n"
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        if old != text:
            changed.append(os.path.relpath(path, ROOT))
            if not check:
                open(path, "w", encoding="utf-8").write(text)
    print(f"citable: {len(doc['statistics'])} statements, all receipted; queue: {len(queue['items'])}; changed: {', '.join(changed) or 'none'}")
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
