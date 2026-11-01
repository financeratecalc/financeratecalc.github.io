#!/usr/bin/env python3
"""Where FHA applications end: the five HMDA outcomes, by lender and nationally, 2025.

Most published figures reduce HMDA to one ratio (denied / decisioned). The record records five ends for an
application that a lender acted on:

    1  originated                      4  withdrawn by the applicant
    2  approved but not accepted       5  file closed for incompleteness
    3  denied

(6 = purchased loans and 7/8 = preapproval requests are not applications acted on and are left out.)

This script streams the CFPB HMDA extract once (FHA forward loans, loan_type 2, reverse mortgages excluded) and
publishes, for the nation and for every lender with >= MIN_LENDER applications acted on:

    outcome shares      each of the five ends as a share of applications acted on (1-5)
    denial_rate_pct     denied / decisioned (1,2,3) — the site's published definition, unchanged
    ana_share_pct       approved-but-not-accepted / (originated + approved-but-not-accepted): approvals that walked away
    reason_other_pct    denials whose first stated reason is "other" (code 10) — a reporting-comparability indicator
    rate_spread_na_pct  originated loans with no rate spread reported — same purpose

No ranking field is written; lenders are in LEI order. Nothing here is a prediction, a cause, or a judgement of
any lender's practice: a high incomplete share can be a process, a market or an applicant-pool fact, and the
record does not say which.

    python3 scripts/application_outcomes.py <hmda_2025_fha.csv> [data/application-outcomes-2025.json]
"""
import csv
import datetime as dt
import glob
import json
import os
import sys
from collections import defaultdict

if len(sys.argv) < 2:
    sys.exit("usage: application_outcomes.py <hmda_2025_fha.csv> [out.json]")
PATH = sys.argv[1]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "data", "application-outcomes-2025.json")
MIN_LENDER = 500

with open(PATH, "r", encoding="utf-8", errors="ignore") as f:
    head = f.readline()
for sep in [",", "|", "\t", ";"]:
    cols = [c.strip().strip('"').lower() for c in head.split(sep)]
    if len(cols) > 8:
        break


def find(*names):
    for n in names:
        if n in cols:
            return cols.index(n)
    return None


IX = {"action": find("action_taken"), "ltype": find("loan_type"), "lei": find("lei", "legal_entity_identifier"),
      "rev": find("reverse_mortgage"), "reason1": find("denial_reason-1", "denial_reason_1"), "spread": find("rate_spread")}
missing = [k for k, v in IX.items() if v is None and k not in ("reason1", "spread")]
if missing:
    sys.exit(f"columns not found: {missing}; header: {cols[:20]}")
print("columns:", IX, flush=True)

names = {}
for fn in glob.glob(os.path.join(ROOT, "api", "lender", "*.json")):
    try:
        L = json.load(open(fn, encoding="utf-8"))
    except Exception:
        continue
    if L.get("lei"):
        names[L["lei"]] = {"name": L.get("lender"), "slug": L.get("slug") or os.path.basename(fn)[:-5]}
try:
    for lei, nm in (json.load(open(os.path.join(ROOT, "data", "lei-names.json"), encoding="utf-8")).get("names") or {}).items():
        names.setdefault(lei, {"name": nm, "slug": None})
except FileNotFoundError:
    pass

ACTIONS = {"1": "originated", "2": "approved_not_accepted", "3": "denied", "4": "withdrawn", "5": "closed_incomplete"}
cnt = defaultdict(lambda: defaultdict(int))   # lei -> action -> n
other = defaultdict(int)                       # lei -> denials with reason-1 == 10
spread_na = defaultdict(int)                   # lei -> originated with rate_spread NA/blank
rows = hecm = skipped = 0
with open(PATH, "r", encoding="utf-8", errors="ignore", newline="") as f:
    rd = csv.reader(f, delimiter=sep)
    next(rd)
    for r in rd:
        rows += 1
        try:
            if r[IX["ltype"]].strip() != "2":
                continue
            if IX["rev"] is not None and r[IX["rev"]].strip() == "1":
                hecm += 1
                continue
            a = r[IX["action"]].strip()
            if a not in ACTIONS:
                skipped += 1
                continue
            lei = r[IX["lei"]].strip()
            cnt[lei][a] += 1
            cnt["_national"][a] += 1
            if a == "3" and IX["reason1"] is not None and r[IX["reason1"]].strip() == "10":
                other[lei] += 1; other["_national"] += 1
            if a == "1" and IX["spread"] is not None and r[IX["spread"]].strip().upper() in ("", "NA", "EXEMPT"):
                spread_na[lei] += 1; spread_na["_national"] += 1
        except IndexError:
            skipped += 1


def summarise(lei):
    c = cnt[lei]
    acted = sum(c.values())
    decisioned = c["1"] + c["2"] + c["3"]
    approved = c["1"] + c["2"]
    pct = lambda x, y: round(100 * x / y, 1) if y else None
    return {
        "applications_acted_on": acted,
        "decisioned_applications": decisioned,
        "outcomes": {ACTIONS[k]: {"n": c[k], "share_of_acted_pct": pct(c[k], acted)} for k in ACTIONS},
        "denial_rate_pct": pct(c["3"], decisioned),
        "ana_share_pct": pct(c["2"], approved),
        "reason_other_pct": pct(other[lei], c["3"]),
        "rate_spread_na_pct": pct(spread_na[lei], c["1"]),
    }


lenders = []
for lei in sorted(k for k in cnt if k != "_national"):
    if sum(cnt[lei].values()) < MIN_LENDER:
        continue
    nm = names.get(lei, {})
    lenders.append({"lei": lei, "name": nm.get("name"), "slug": nm.get("slug"), **summarise(lei)})

out = {
    "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "universe": "FHA forward loans (loan_type 2), 2025, reverse mortgages excluded; applications acted on = action_taken 1-5 "
                "(purchased loans 6 and preapproval requests 7-8 excluded); decisioned = 1,2,3; denial = 3",
    "definitions": {
        "share_of_acted_pct": "outcome / applications acted on (actions 1-5)",
        "denial_rate_pct": "denied / decisioned (actions 1,2,3) — the site's published definition",
        "ana_share_pct": "approved but not accepted / (originated + approved but not accepted)",
        "reason_other_pct": "denials whose first stated reason is code 10 'other' / denials; a reporting-comparability indicator, not a judgement",
        "rate_spread_na_pct": "originated loans with rate_spread NA, blank or Exempt / originated; same purpose",
    },
    "does_not_establish": [
        "why any application ended where it did (process, market, applicant pool and reporting practice are not separable in this record)",
        "that any lender's practice is better or worse than another's for a given applicant",
        "any individual applicant's outcome at any lender",
    ],
    "rows_read": rows, "hecm_excluded": hecm, "rows_skipped": skipped, "min_lender_applications": MIN_LENDER,
    "national": summarise("_national"),
    "lenders": lenders,   # LEI order; no ranking field
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
n = out["national"]
print(f"rows {rows}, hecm {hecm}, skipped {skipped}; national acted {n['applications_acted_on']}, decisioned {n['decisioned_applications']}, "
      f"denial {n['denial_rate_pct']}%, ANA {n['ana_share_pct']}%, lenders published {len(lenders)} -> {os.path.relpath(OUT, ROOT)}", flush=True)
