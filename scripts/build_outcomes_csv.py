#!/usr/bin/env python3
"""Write data/fha-application-outcomes-2025.csv from data/application-outcomes-2025.json: one row for the nation and one
per lender, with column names that state the denominator, so a reader (or an answer engine) cannot take a share for a
rate. Run after scripts/application_outcomes.py; no number is typed here."""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "application-outcomes-2025.json")
OUT = os.path.join(ROOT, "data", "fha-application-outcomes-2025.csv")
OUTCOMES = ["originated", "approved_not_accepted", "denied", "withdrawn", "closed_incomplete"]


def row(scope, lei, name, x):
    o = x["outcomes"]
    r = {"scope": scope, "lei": lei, "lender": name, "applications_acted_on_actions_1_5": x["applications_acted_on"],
         "decisioned_applications_actions_1_3": x["decisioned_applications"]}
    for k in OUTCOMES:
        r[f"{k}_n"] = o[k]["n"]
    for k in OUTCOMES:
        r[f"{k}_share_of_acted_on_pct"] = o[k]["share_of_acted_pct"]
    r["denial_rate_denied_over_decisioned_pct"] = x["denial_rate_pct"]
    return r


def main():
    d = json.load(open(SRC, encoding="utf-8"))
    rows = [row("national", "", "All FHA lenders", d["national"])]
    rows += [row("lender", L["lei"], L["name"], L) for L in sorted(d["lenders"], key=lambda L: -L["applications_acted_on"])]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {os.path.relpath(OUT, ROOT)}: {len(rows)} rows (universe: {d['universe']})")


if __name__ == "__main__":
    main()
