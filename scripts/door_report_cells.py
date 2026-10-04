#!/usr/bin/env python3
"""Door Report cells: lender denial rates inside a borrower cohort (state x loan-amount
band x purpose), FHA forward loans, 2025, decisioned applications, HECM excluded.

Streams the CFPB HMDA extract once. Publishes every lender with >= MIN_CELL decisions in
the cell, in LEI order, with no ranking field: the page sorts alphabetically and the
product rule (scripts/door_report_rules_test.py) refuses any other order. Output:
data/door-report-cells-2025.json. Same filters as scripts/reference_implementation.py.
"""
import csv
import datetime as dt
import json
import os
import sys
from collections import defaultdict

if len(sys.argv) < 2:
    sys.exit("usage: door_report_cells.py <hmda_2025_fha.csv> [out.json]")
PATH = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "door-report-cells-2025.json")
MIN_CELL = 100

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
    for i, c in enumerate(cols):
        for n in names:
            if n in c:
                return i
    return None


IX = {"action": find("action_taken"), "ltype": find("loan_type"), "lei": find("lei", "legal_entity_identifier"),
      "rev": find("reverse_mortgage"), "amount": find("loan_amount"), "state": find("state_code", "state"),
      "purpose": find("loan_purpose")}
print("columns:", IX)

BANDS = [("u150", 0, 150000), ("150-250", 150000, 250000), ("250p", 250000, 10**12)]
PURPOSE = {"1": "purchase", "31": "refinance", "32": "refinance", "2": "improvement", "4": "other", "5": "other"}


def band(a):
    for b, lo, hi in BANDS:
        if lo <= a < hi:
            return b
    return None


n = hecm = 0
names = {}
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
for fn in os.listdir(os.path.join(root, "api", "lender")):
    if fn.endswith(".json"):
        with open(os.path.join(root, "api", "lender", fn), encoding="utf-8") as fh:
            L = json.load(fh)
        if L.get("lei"):
            names[L["lei"]] = {"name": L.get("lender"), "slug": L.get("slug") or fn[:-5]}

try:
    with open(os.path.join(root, "data", "lei-names.json"), encoding="utf-8") as fh:
        for lei, nm in (json.load(fh).get("names") or {}).items():
            if isinstance(nm, dict):
                nm = nm.get("legal_name") or nm.get("name")
            if nm:
                names.setdefault(lei, {"name": nm, "slug": None})
except FileNotFoundError:
    pass

ct = defaultdict(int); cd = defaultdict(int)
with open(PATH, "r", encoding="utf-8", errors="ignore") as f:
    rd = csv.reader(f, delimiter=sep); next(rd, None)
    for r in rd:
        n += 1
        if n % 400000 == 0:
            print(f"  {n:,} rows")
        try:
            if IX["ltype"] is not None and r[IX["ltype"]].strip() != "2":
                continue
            a = r[IX["action"]].strip()
            if a not in ("1", "2", "3"):
                continue
            if IX["rev"] is not None and r[IX["rev"]].strip() == "1":
                hecm += 1; continue
            lei = r[IX["lei"]].strip()
            st = r[IX["state"]].strip() if IX["state"] is not None else ""
            if not lei or st in ("", "NA", "na", "N/A"):
                continue
            try:
                amt = float(r[IX["amount"]])
            except (ValueError, TypeError, IndexError):
                continue
            b = band(amt)
            if not b:
                continue
            p = PURPOSE.get(r[IX["purpose"]].strip(), "other") if IX["purpose"] is not None else "all"
            den = 1 if a == "3" else 0
            for key in ((st, b, p), (st, b, "all"), (st, "all", p), (st, "all", "all")):
                ct[(key, lei)] += 1; cd[(key, lei)] += den
        except IndexError:
            continue

t = defaultdict(int); d = defaultdict(int)
for (key, lei), nn in ct.items():
    t[key] += nn; d[key] += cd[(key, lei)]
cells = {}
for (key, lei), nn in ct.items():
    if nn < MIN_CELL:
        continue
    st, b, p = key
    cid = f"{st}|{b}|{p}"
    c = cells.setdefault(cid, {"state": st, "amount_band": b, "purpose": p, "decisions": t[key], "denials": d[key],
                              "denial_rate_pct": round(100 * d[key] / t[key], 1) if t[key] else None, "lenders": []})
    nm = names.get(lei, {})
    c["lenders"].append({"lei": lei, "name": nm.get("name"), "slug": nm.get("slug"), "decisions": nn, "denials": cd[(key, lei)],
                         "denial_rate_pct": round(100 * cd[(key, lei)] / nn, 1)})
for c in cells.values():
    c["lenders"].sort(key=lambda x: x["lei"])  # LEI order only; the page sorts alphabetically; never by rate
    c["lenders_published"] = len(c["lenders"])

out = {
    "generated": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "universe": "FHA forward loans (loan_type 2), 2025, decisioned applications (action_taken 1,2,3), reverse mortgages excluded; denial = action 3",
    "universe_id": "U-FHA-2025-DECISIONED",
    "cell": "state x loan-amount band (u150 <$150k, 150-250, 250p >=$250k; 'all') x purpose (purchase, refinance, improvement, other; 'all')",
    "min_cell": MIN_CELL,
    "rule": "Every lender with at least MIN_CELL decisions in the cell is published; none is ranked, highlighted or recommended. Rates are historical observations that reflect applicant composition as well as lender practice; they are not predictions about any application and not evidence of misconduct.",
    "hecm_excluded": hecm, "rows_read": n, "cells": len(cells),
    "source": "CFPB HMDA 2025 public LAR extract (loan_types=2); scripts/door_report_cells.py",
    "license": "CC BY 4.0",
    "data": cells,
}
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, separators=(",", ":"), ensure_ascii=False)
print(f"cells {len(cells)}, rows {n:,}, hecm {hecm:,} -> {OUT} ({os.path.getsize(OUT)/1e6:.1f} MB)")
