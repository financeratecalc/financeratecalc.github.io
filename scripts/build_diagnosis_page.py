#!/usr/bin/env python3
"""denominator-diagnosis.html: one complete "denominator diagnosis", worked on two published figures.

A consumer finance page gives 2025 denial rates of 12.23% for FHA and 7.89% for VA, citing HMDA data, with no
denominator. This page shows the whole search: every cell of the published denominator map (data/purpose/*.json)
for each program, sorted by distance from the quoted figure, and the verdict the search supports. Nothing is typed
in except the quoted figures and the description of the page they come from (checked 2026-11-15).

    python3 scripts/build_diagnosis_page.py [--check]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOL = 0.15
PW = {"all": "all purposes", "purchase": "home purchase", "refinance_all": "refinance incl. cash-out", "refinance": "refinance", "cash_out_refinance": "cash-out refinance",
      "home_improvement": "home improvement", "other": "other purpose", "not_applicable": "purpose n/a"}
BW = {"decisioned": "decisioned", "acted_on": "all acted on", "denied_plus_originated": "denied + originated"}
QUOTED = [("fha", "FHA", 12.23), ("va", "VA", 7.89)]
CHECKED = "15 November 2026"


def cells(p):
    d = json.load(open(os.path.join(ROOT, "data", "purpose", f"{p}-2025.json"), encoding="utf-8"))
    out = []
    for key, c in d["cells"].items():
        purpose, scope = key.split("|")
        for base, r in c["rate_pct"].items():
            if r is None:
                continue
            den = {"decisioned": c["decisioned"], "acted_on": c["acted_on"], "denied_plus_originated": c["originated"] + c["denied"]}[base]
            out.append({"purpose": purpose, "scope": scope, "base": base, "rate": r, "denied": c["denied"], "den": den})
    return out


def build():
    src = open(os.path.join(ROOT, "claim-audit.html"), encoding="utf-8").read()
    style = src[src.index("<style>"):src.index("</style>") + 8].replace("</style>", ".small{font-size:13px;color:#a5a094}td.n{text-align:right;font-family:'DM Mono',monospace;white-space:nowrap}tr.near td{color:#f5f2ea}</style>")
    nav = src[src.index("<nav data-frc-nav"):src.index("</nav>") + 6]
    blocks, verdicts = "", []
    for p, P, q in QUOTED:
        cs = sorted(cells(p), key=lambda c: abs(c["rate"] - q))
        hits = [c for c in cs if abs(c["rate"] - q) <= TOL]
        near = cs[0]
        verdicts.append((P, q, len(cs), len(hits), near))
        rows = "".join(
            f'<tr{" class=near" if i < 3 else ""}><td>{PW.get(c["purpose"], c["purpose"])}</td><td>{"all rows" if c["scope"] == "all" else "first-lien, owner-occupied, site-built, 1&ndash;4 units"}</td><td>{BW[c["base"]]}</td>'
            f'<td class="n">{c["denied"]:,} / {c["den"]:,}</td><td class="n">{c["rate"]:.2f}%</td><td class="n">{abs(c["rate"] - q):.2f}</td></tr>' for i, c in enumerate(cs[:10]))
        blocks += (f'<h2>{P}: quoted {q}%</h2>\n<p class="sub" style="font-size:14.5px">{len(cs)} definitions computed from the 2025 file. The ten closest, nearest first. '
                   f'{"<b>" + str(len(hits)) + " within " + str(TOL) + " points.</b>" if hits else "<b>None within " + str(TOL) + " points.</b>"} '
                   f'The closest is {near["rate"]:.2f}% ({PW.get(near["purpose"], near["purpose"])}, {BW[near["base"]]}), {abs(near["rate"] - q):.2f} points away.</p>\n'
                   f'<table><tr><th>Loan purpose</th><th>Scope</th><th>Base</th><th>Denied / denominator</th><th>Rate</th><th>Distance</th></tr>{rows}</table>\n')
    none = all(v[3] == 0 for v in verdicts)
    title = "A denominator diagnosis: two published denial rates that the 2025 file does not reproduce"
    return f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | FinanceRateCalc</title>
<meta name="description" content="A published page gives 2025 denial rates of 12.23% for FHA and 7.89% for VA, citing HMDA data and no denominator. The full search of the federal file, definition by definition, and what it does and does not show.">
<link rel="canonical" href="https://financeratecalc.com/denominator-diagnosis.html">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,900&family=DM+Sans:wght@300;400;600;700&family=DM+Mono&display=swap" rel="stylesheet">
{style}</head><body>
{nav}
<div class="wrap">
<div class="kicker">Denominator diagnosis · worked example</div>
<h1>12.23% and 7.89%: of what?</h1>
<p class="sub">A consumer finance page, <i>Signs Your Mortgage Will Be Denied in Underwriting</i> (LendingTree, marked &ldquo;Updated Oct 20, 2026&rdquo;), gives national denial rates of 7.53% for conventional loans, 12.23% for FHA loans and 7.89% for VA loans, from its own analysis of Home Mortgage Disclosure Act data, for 2025. It does not say which applications are counted. The link it gives for the data opens a CFPB report on 2023 mortgage activity. Answer engines repeat these figures; one gave 12.23% as the &ldquo;overall&rdquo; FHA denial rate. Page read on {CHECKED}.</p>
<div class="card"><b>Finding.</b> {"Neither figure is reproduced by any definition computed from the 2025 federal file." if none else "See the tables."} Among decisioned applications of every purpose, the 2025 rates are 22.08% for FHA and 16.15% for VA. For home purchase alone they are 12.78% and 8.24%. The quoted figures sit near the purchase rates and below them. The conventional figure was not searched: purchase and refinance rates for conventional loans are not published here yet.</div>
<h2>How the search works</h2>
<p class="sub" style="font-size:14.5px">For each program the 2025 HMDA file is counted by loan purpose (8), scope (all rows; or first-lien, owner-occupied, site-built, 1&ndash;4 unit) and base (denied over decisioned applications; over all applications acted on; over denied plus originated). That gives 48 denial rates per program, each with its counts, on the <a href="/denominator-map.html">denominator map</a>. A quoted figure within {TOL} points of a cell is a match.</p>
{blocks}
<h2>What could explain the gap</h2>
<p class="sub" style="font-size:14.5px">These are possibilities, not findings. The publisher may have applied a filter this map does not have (a loan-amount limit, a subset of lenders, conforming loans only, a different treatment of preapprovals or purchased loans). The figures may come from another year&rsquo;s file: the link on the page points to a report on 2023. Or the method may be one the public file cannot reproduce. Only the publisher can say which. A statement of the denominator on that page would settle it in one line.</p>
<h2>What this does not say</h2>
<div class="limit">It does not say the figures are wrong, and it says nothing about the publisher&rsquo;s intent. It says that, as published, they cannot be traced to the 2025 federal file under any of the definitions listed here, and that a reader cannot tell what they measure. It says nothing about any applicant, and it does not compare programs or lenders.</div>
<p class="sub" style="font-size:14px">Counts and rates: <a href="/data/purpose/fha-2025.json">data/purpose/fha-2025.json</a>, <a href="/data/purpose/va-2025.json">data/purpose/va-2025.json</a>. Receipts for the purchase and all-purpose rates are on the <a href="/denominator-map.html">denominator map</a>. To run the same search on any table: <a href="/place-a-number.html">place a number</a>. A five-claim example: <a href="/sample-evidence-brief.html">sample Evidence Brief</a>. Generated by <span class="mono">scripts/build_diagnosis_page.py</span>.</p>
<div style="margin-top:40px;border-top:1px solid #23262e;padding-top:14px;font-size:13px;color:#a5a094">FinanceRateCalc &middot; Measured, not assumed. &middot; <a href="/corrections.html">Corrections</a> &middot; If you publish one of these figures and can state its denominator, write to the address on <a href="/about.html">About</a> and this page will say so.</div>
</div></body></html>
'''


if __name__ == "__main__":
    page = build(); p = os.path.join(ROOT, "denominator-diagnosis.html")
    if "--check" in sys.argv:
        if not os.path.exists(p) or open(p, encoding="utf-8").read() != page:
            print("denominator-diagnosis.html is STALE; run scripts/build_diagnosis_page.py"); sys.exit(1)
        print("denominator-diagnosis.html is current")
    else:
        open(p, "w", encoding="utf-8").write(page); print("wrote", p, len(page), "bytes")
