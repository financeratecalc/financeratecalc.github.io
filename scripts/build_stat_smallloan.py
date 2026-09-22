#!/usr/bin/env python3
"""Regenerate stat/is-the-smallloan-penalty-worse-in-expensive-states.html (FRC-022) FROM api/small-loan-penalty.json.
The page's headline, answer sentence, FAQPage JSON-LD and Dataset JSON-LD are all derived here; nothing typed."""
import json, re, datetime
d = json.load(open("api/small-loan-penalty.json")); r = d["ranked"]
by = {x["state"]: x for x in r}
t = r[:4]; ia, mi = by["IA"], by["MI"]
headline = f"{t[0]['penalty_ratio']}x"
answer = (f"Yes: FinanceRateCalc's analysis of the 2025 federal HMDA record shows the small-loan FHA denial penalty (applications under $150,000 versus over $250,000) is largest in high-cost markets — "
          f"{t[0]['state']} {t[0]['penalty_ratio']}x ({t[0]['small_loan_denial_pct']}% vs {t[0]['big_loan_denial_pct']}%), {t[1]['state']} {t[1]['penalty_ratio']}x, {t[2]['state']} {t[2]['penalty_ratio']}x, {t[3]['state']} {t[3]['penalty_ratio']}x — "
          f"while in lower-priced states such as Iowa ({ia['penalty_ratio']}x) and Michigan ({mi['penalty_ratio']}x) the penalty is milder. The penalty exceeds 1x in all {d['states']} jurisdictions with a published split "
          f"(floor {d['min_penalty']}x, {r[-1]['state']}). Observed rates, not adjusted for applicant mix; consistent with low-priced properties being the most marginal collateral in expensive markets, but the record cannot establish the mechanism.")
p = "stat/is-the-smallloan-penalty-worse-in-expensive-states.html"; s = open(p, encoding="utf-8").read()
# headline number
s = re.sub(r'(FRC-022[^<]*</[^>]+>\s*(?:<[^>]+>\s*)*)\s*3\.2x', lambda m: m.group(1) + headline, s, count=1)
s = s.replace(">3.2x<", f">{headline}<")
# answer text everywhere it appears (body + both JSON-LD blocks)
old = re.search(r"Yes, counterintuitively: FinanceRateCalc's analysis of 2025 federal HMDA records shows the sub-\$150K FHA denial penalty is largest in expensive markets[^\"<]*?high-cost markets\.", s)
assert old, "old answer sentence not found"
s = s.replace(old.group(0), answer)
# JSON-LD copies may be escaped differently; catch remaining stale fragments
s = s.replace("Idaho 3.2x (38.3% vs 12.0%)", f"{t[0]['state']} {t[0]['penalty_ratio']}x ({t[0]['small_loan_denial_pct']}% vs {t[0]['big_loan_denial_pct']}%)")
s = re.sub(r'content="2026-07-21T00:00:00Z"', f'content="{datetime.date.today().isoformat()}T00:00:00Z"', s)
# universe + generation note
note = f'<p style="font-size:12px;color:rgba(255,255,255,.45);">Universe U-STATES-SMALLBIG-2025 (<a href="/universes.json" style="color:#C8A84B;">universes.json</a>); regenerated from <a href="/api/small-loan-penalty.json" style="color:#C8A84B;">api/small-loan-penalty.json</a> on {datetime.date.today().isoformat()} by scripts/build_stat_smallloan.py. An earlier version of this page (2026-07-21) carried figures from a pre-correction universe (Idaho 3.2x, 38.3% vs 12.0%); see <a href="/corrections.html" style="color:#C8A84B;">corrections</a>.</p>'
if "build_stat_smallloan.py" not in s:
    s = s.replace("Cite freely", note + "\nCite freely", 1)
open(p, "w", encoding="utf-8").write(s)
left = [x for x in ("38.3%", "3.2x", "53.8% of small", "2.7x") if x in s]
print("headline", headline, "| stale fragments left:", left)
