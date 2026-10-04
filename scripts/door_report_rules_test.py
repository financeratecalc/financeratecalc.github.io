#!/usr/bin/env python3
"""Product rules for the Door Report, enforced as tests (not as good intentions):
1. No ranking: the page sorts lenders alphabetically only; no sort by rate, no
   highlight/best/top/recommended class or wording; the data file lists lenders in LEI order.
2. Same caveat on every cohort: the not-a-prediction / not-a-recommendation / not-misconduct
   sentence is present in the page's cohort header and in the rules block.
Run: python scripts/door_report_rules_test.py  (exit 1 on any violation)
"""
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
with open(os.path.join(ROOT, "door-report.html"), encoding="utf-8") as fh:
    page = fh.read()
errors = []

# rule 1a: the only sort in the script is the alphabetical one
sorts = [page[m.end(): m.end() + 160] for m in re.finditer(r"\.sort\(", page)]
for s in sorts:
    if "localeCompare" not in s or "denial_rate" in s or "decisions" in s or "denials" in s:
        errors.append(f"sort that is not alphabetical: {s[:80]}")
if not sorts:
    errors.append("no alphabetical sort found")
# rule 1b: no ranking vocabulary or highlight classes
for w in ["best lender", "top lender", "worst", "avoid", "class=\"best", "class=\"top"]:
    if re.search(re.escape(w), page, re.IGNORECASE):
        errors.append(f"ranking vocabulary/class present: {w}")
# "recommend"/"rank"/"highlight" may appear only in negations
for m in re.finditer(r"recommend|rank|highlight", page, re.IGNORECASE):
    ctx = page[max(0, m.start() - 40): m.end() + 20].lower()
    if not any(neg in ctx for neg in ("not a recommendation", "nor recommended", "none is ranked", "not ranked", "never by rate", "none ranked", "not a prediction", "ranked, highlighted or recommended", "ranked or recommended", "no ranking", "not", "nothing here is ranked")):
        errors.append(f"'{m.group(0)}' outside a negation: ...{ctx.strip()}...")
# rule 2: caveat present in header template and rules block
for phrase in ["not a prediction about any application", "not a recommendation", "not evidence of misconduct"]:
    if page.lower().count(phrase.lower()) < 1:
        errors.append(f"caveat phrase missing: {phrase}")
if "Historical observation; not a prediction about any application; not a recommendation; not evidence of misconduct." not in page:
    errors.append("cohort-header caveat sentence missing or altered")
# rule 1c: data file order is LEI order, no rank field
dp = os.path.join(ROOT, "data", "door-report-cells-2025.json")
if os.path.exists(dp):
    with open(dp, encoding="utf-8") as fh:
        d = json.load(fh)
    for cid, c in list(d["data"].items())[:5000]:
        leis = [x["lei"] for x in c["lenders"]]
        if leis != sorted(leis):
            errors.append(f"data not in LEI order: {cid}"); break
        if any("rank" in x for x in c["lenders"]):
            errors.append(f"rank field in data: {cid}"); break
if errors:
    print("DOOR REPORT RULES: FAIL"); [print(" -", e) for e in errors]; sys.exit(1)
print("DOOR REPORT RULES: pass")
