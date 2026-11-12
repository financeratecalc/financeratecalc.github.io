#!/usr/bin/env python3
"""Same denials, different denominators: one pass over a CFPB HMDA extract that counts a program's applications by
loan purpose, by scope and by action taken, so that every "denial rate" a reader meets can be placed.

    python3 scripts/denominator_grid.py <hmda_csv> --loan-type 2|3|4|1 [--closed-end] [--sha256 H] [--url U] [--no-universe-check]

Writes data/purpose/<fha|va|usda|conv>-2025.json. Declared before any figure in provenance/universe-purpose-split-2025.md.

Cells = purpose x scope; each cell keeps the five action counts and three rates:
    decisioned              denied / (originated + approved-not-accepted + denied)   <- this site's published definition
    acted_on                denied / (actions 1-5)
    denied_plus_originated  denied / (originated + denied)
Purposes: all, purchase (1), refinance (31), cash_out_refinance (32), refinance_all (31+32), home_improvement (2),
other (4), not_applicable (5). Scopes: all; standard = first lien, owner-occupied principal residence, site-built,
1-4 units (the filter many consumer analyses apply).

Guard: the all|all decisioned count must equal the published universe count (universes.json) or nothing is written.
Only two cells per program carry receipts: purchase|all and refinance_all|all on the decisioned base."""
import csv
import datetime as dt
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
a = sys.argv[1:]
if not a or a[0].startswith("--"):
    sys.exit("usage: denominator_grid.py <hmda_csv> --loan-type N [--closed-end] [--sha256 H] [--url U]")
PATH = a[0]
opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
LT = opt("--loan-type", "2"); CLOSED = "--closed-end" in a
PROG = {"1": "conv", "2": "fha", "3": "va", "4": "usda"}[LT]
NAME = {"conv": "conventional", "fha": "FHA", "va": "VA", "usda": "USDA"}[PROG]
PURPOSE = {"1": "purchase", "31": "refinance", "32": "cash_out_refinance", "2": "home_improvement", "4": "other", "5": "not_applicable"}

with open(PATH, "r", encoding="utf-8", errors="ignore") as f:
    head = f.readline()
for sep in [",", "|", "\t", ";"]:
    cols = [c.strip().strip('"').lower() for c in head.split(sep)]
    if len(cols) > 8:
        break
ix = lambda n: cols.index(n) if n in cols else None
IX = {k: ix(n) for k, n in {"action": "action_taken", "ltype": "loan_type", "rev": "reverse_mortgage", "openend": "open_end_line_of_credit", "purpose": "loan_purpose",
                            "lien": "lien_status", "occ": "occupancy_type", "constr": "construction_method", "units": "total_units"}.items()}
need = [k for k in ("action", "ltype", "rev", "purpose") if IX[k] is None]
if need:
    sys.exit(f"columns not found: {need}; header: {cols[:25]}")
HAS_SCOPE = all(IX[k] is not None for k in ("lien", "occ", "constr", "units"))

cnt = defaultdict(lambda: defaultdict(int))   # "purpose|scope" -> action -> n
rows = hecm = openend = unknown_purpose = 0
with open(PATH, "r", encoding="utf-8", errors="ignore", newline="") as f:
    rd = csv.reader(f, delimiter=sep); next(rd)
    for r in rd:
        rows += 1
        try:
            if r[IX["ltype"]].strip() != LT:
                continue
            if r[IX["rev"]].strip() == "1":
                hecm += 1; continue
            if IX["openend"] is not None and r[IX["openend"]].strip() == "1":
                openend += 1
                if CLOSED:
                    continue
            act = r[IX["action"]].strip()
            if act not in ("1", "2", "3", "4", "5"):
                continue
            p = PURPOSE.get(r[IX["purpose"]].strip())
            if p is None:
                unknown_purpose += 1; p = "not_applicable"
            ps = ["all", p] + (["refinance_all"] if p in ("refinance", "cash_out_refinance") else [])
            std = HAS_SCOPE and r[IX["lien"]].strip() == "1" and r[IX["occ"]].strip() == "1" and r[IX["constr"]].strip() == "1" and r[IX["units"]].strip() in ("1", "2", "3", "4")
            for q in ps:
                cnt[q + "|all"][act] += 1
                if std:
                    cnt[q + "|standard"][act] += 1
        except IndexError:
            continue


def cell(c):
    o, ana, den, wd, inc = c["1"], c["2"], c["3"], c["4"], c["5"]
    r = lambda x, y: round(100 * x / y, 2) if y else None
    return {"originated": o, "approved_not_accepted": ana, "denied": den, "withdrawn": wd, "closed_incomplete": inc,
            "decisioned": o + ana + den, "acted_on": o + ana + den + wd + inc,
            "rate_pct": {"decisioned": r(den, o + ana + den), "acted_on": r(den, o + ana + den + wd + inc), "denied_plus_originated": r(den, o + den)}}


cells = {k: cell(v) for k, v in sorted(cnt.items())}
U = json.load(open(os.path.join(ROOT, "universes.json"), encoding="utf-8"))["universes"]
base_id = f"U-{PROG.upper()}-2025-DECISIONED"
published = (U.get(base_id) or {}).get("count")
got = cells.get("all|all", {}).get("decisioned")
if "--no-universe-check" not in a:
    if published is None:
        sys.exit(f"{base_id} has no published count yet: publish the program's national figure first; nothing written")
    if got != published:
        sys.exit(f"all-purpose decisioned count {got} != published {base_id} count {published}; nothing written")
parts = sum(cells.get(p + "|all", {}).get("decisioned", 0) for p in PURPOSE.values())
if parts != got:
    sys.exit(f"purposes do not add up to the total ({parts} vs {got}); nothing written")

out = {"generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "program": NAME, "program_id": PROG, "loan_type": LT, "closed_end_only": CLOSED, "period": "2025",
       "base_universe_id": base_id, "universe_ids": {"purchase": f"{base_id}-PURCHASE", "refinance_all": f"{base_id}-REFINANCE"},
       "declared_in": "provenance/universe-purpose-split-2025.md",
       "input": {"url": opt("--url"), "sha256": opt("--sha256")}, "code_commit": os.environ.get("GITHUB_SHA"),
       "rows_read": rows, "reverse_mortgage_excluded": hecm, "open_end_rows_seen": openend, "unknown_purpose_rows": unknown_purpose, "scope_columns_present": HAS_SCOPE,
       "definitions": {"purposes": {"purchase": "loan_purpose 1", "refinance": "loan_purpose 31", "cash_out_refinance": "loan_purpose 32", "refinance_all": "loan_purpose 31 or 32",
                                    "home_improvement": "loan_purpose 2", "other": "loan_purpose 4", "not_applicable": "loan_purpose 5", "all": "every loan purpose"},
                       "scopes": {"all": "no further filter", "standard": "lien_status 1, occupancy_type 1, construction_method 1, total_units 1-4"},
                       "bases": {"decisioned": "denied / (originated + approved not accepted + denied); the site's published definition",
                                 "acted_on": "denied / applications acted on (actions 1-5)", "denied_plus_originated": "denied / (originated + denied)"}},
       "receipted_cells": ["purchase|all", "refinance_all|all"], "receipted_base": "decisioned",
       "does_not_establish": ["which denominator any other publisher used (a matching number is a match, not an attribution)",
                              "that one loan purpose or program is easier or harder to obtain for a given applicant (applicant populations differ)",
                              "any individual's chance of denial", "any lender-level figure"],
       "cells": cells}
od = os.path.join(ROOT, "data", "purpose"); os.makedirs(od, exist_ok=True)
p = os.path.join(od, f"{PROG}-2025.json")
json.dump(out, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
for pid, key in (("purchase", "purchase|all"), ("refinance_all", "refinance_all|all")):
    uid = out["universe_ids"][pid]
    reg = json.load(open(os.path.join(ROOT, "universes.json"), encoding="utf-8"))
    if uid in reg["universes"] and key in cells:
        reg["universes"][uid]["count"] = cells[key]["decisioned"]
        reg["universes"][uid]["status"] = f"declared 2026-11-12; count filled by the pipeline on {out['generated'][:10]}"
        json.dump(reg, open(os.path.join(ROOT, "universes.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"{NAME}: rows {rows:,}; decisioned {got:,} (= {base_id}); " + "; ".join(f"{k} {cells[k]['rate_pct']['decisioned']}% of {cells[k]['decisioned']:,}" for k in ("purchase|all", "refinance_all|all") if k in cells) + f" -> {os.path.relpath(p, ROOT)}")
