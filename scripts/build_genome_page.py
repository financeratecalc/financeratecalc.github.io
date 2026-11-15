#!/usr/bin/env python3
"""denial-genome.html, rebuilt from the published 2025 data after its original claims were withdrawn (2026-11-15).

The June 2026 page named a single reason each lender 'rejects on', called the pattern stable for eight years and told
readers to match their file to a lender. The site's own 2025 reason shares contradict the named reasons for several of
the lenders, the stability claim was never published with data, and lender matching is advice this site does not give.
This script writes what the record does show for the same eleven lenders: the receipted 2025 denial rate and the
reasons cited most often among that lender's denials, from api/lender/<slug>.json. No number is typed.

    python3 scripts/build_genome_page.py [--check]
"""
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LENDERS = [("CrossCountry Mortgage", "crosscountry-mortgage"), ("Guild Mortgage", "guild-mortgage"), ("Rocket Mortgage", "rocket-mortgage"), ("United Wholesale Mortgage", "united-wholesale-mortgage"),
           ("PennyMac Loan Services", "pennymac-loan-services"), ("Nationstar (Mr. Cooper)", "nationstar-mortgage"), ("loanDepot", "loandepotcom"), ("Planet Home Lending", "planet-home-lending"),
           ("Freedom Mortgage", "freedom-mortgage"), ("Wells Fargo Bank", "wells-fargo-bank"), ("NewRez", "newrez")]
WORD = {"dti": "debt-to-income ratio", "credit_history": "credit history", "collateral": "collateral", "insufficient_cash": "insufficient cash", "incomplete": "incomplete application",
        "unverifiable_info": "unverifiable information", "employment": "employment history", "other": "other", "mortgage_insurance_denied": "mortgage insurance denied"}
WAS = {"crosscountry-mortgage": "debt-to-income ratio", "wells-fargo-bank": "credit history", "freedom-mortgage": "incomplete application", "rocket-mortgage": "credit history"}  # what the withdrawn page named


def build():
    src = open(os.path.join(ROOT, "claim-audit.html"), encoding="utf-8").read()
    style = src[src.index("<style>"):src.index("</style>") + 8].replace("</style>", ".small{font-size:13px;color:#a5a094}td.n{text-align:right;font-family:'DM Mono',monospace}</style>")
    nav = src[src.index("<nav data-frc-nav"):src.index("</nav>") + 6]
    rows, wrong = "", []
    for name, slug in LENDERS:
        d = json.load(open(os.path.join(ROOT, "api", "lender", slug + ".json"), encoding="utf-8"))
        c = json.load(open(os.path.join(ROOT, "claims", f"lender-{slug}-2025.json"), encoding="utf-8"))
        sh = sorted((d.get("denial_reason_shares_pct") or {}).items(), key=lambda x: -x[1])
        top = "; ".join(f"{WORD.get(k, k.replace('_', ' '))} {v:.1f}%" for k, v in sh[:3]) or "not reported"
        if slug in WAS and sh and WORD.get(sh[0][0]) != WAS[slug]:
            wrong.append(f"{html.escape(name)} (page said {WAS[slug]}; most cited in 2025: {WORD.get(sh[0][0], sh[0][0])}, {sh[0][1]:.1f}%)")
        rows += (f'<tr><td>{html.escape(name)}</td><td class="n">{c["display_value"]}</td><td class="n">{d["decisioned_applications"]:,}</td><td>{top}</td>'
                 f'<td class="small"><a href="/claims/lender-{slug}-2025.json">receipt</a></td></tr>\n')
    title = "The Denial Genome (withdrawn claims, corrected figures)"
    return f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | FinanceRateCalc</title>
<meta name="description" content="A June 2026 page said each FHA lender rejects on one reason and that the pattern was stable. Those claims are withdrawn. This page shows what the 2025 record does show for the same eleven lenders: denial rate and the reasons cited most often.">
<link rel="canonical" href="https://financeratecalc.com/denial-genome.html">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,900&family=DM+Sans:wght@300;400;600;700&family=DM+Mono&display=swap" rel="stylesheet">
{style}</head><body>
{nav}
<div class="wrap">
<div class="kicker">Corrected 15 November 2026 · original claims withdrawn</div>
<h1>The Denial Genome: what the record shows, and what this page used to say</h1>
<div class="limit"><b>Withdrawn.</b> From June 2026 this page said that each FHA lender &ldquo;rejects on&rdquo; one characteristic reason, that the pattern had been stable for eight years, and that a borrower should match a file&rsquo;s weakness to a lender. None of that stands. The named reasons do not match this site&rsquo;s own 2025 reason shares for {len(wrong)} of the four lenders it named: {"; ".join(wrong)}. The stability claim was never published with data behind it. Matching a file to a lender is advice about one application, which aggregate records cannot support and this site does not give. The page&rsquo;s LSI scores were not receipted figures and are removed. <a href="/corrections.html#2026-11-15-genome-withdrawn">Correction entry</a>.</div>
<h2>The same eleven lenders, from the 2025 federal record</h2>
<table><tr><th>Lender</th><th>Denied, 2025</th><th>Decisioned FHA applications</th><th>Reasons cited most often among its denials</th><th></th></tr>
{rows}</table>
<p class="sub" style="font-size:14.5px">Denial rate: share of decisioned FHA applications (originated, approved but not accepted, or denied) that were denied in 2025; reverse mortgages excluded. Reason shares: share of the lender&rsquo;s denials on which that reason was reported. A lender may report up to four reasons per denial, so shares do not add to 100.</p>
<h2>What these figures do not establish</h2>
<div class="card">Reason codes are filed by lenders under federal reporting rules. They describe what was reported, not why an underwriter decided, and they partly reflect who applies to each lender, through which channel and for which product. A lender&rsquo;s most-cited reason says nothing about how one application would be treated there. Nothing here ranks lenders or recommends one.</div>
<p class="sub" style="font-size:14.5px">The maintained pages: <a href="/fha-denial-reasons-by-lender.html">denial reasons by lender</a> (all lenders that report reasons) &middot; <a href="/fha-denial-rates-top-100.html">denial rates, 100 largest lenders</a> &middot; <a href="/corrections.html">corrections</a>. Generated by <span class="mono">scripts/build_genome_page.py</span> from <span class="mono">api/lender/</span> and the claim documents.</p>
<div style="margin-top:40px;border-top:1px solid #23262e;padding-top:14px;font-size:13px;color:#a5a094">FinanceRateCalc &middot; Measured, not assumed.</div>
</div></body></html>
'''


if __name__ == "__main__":
    page = build(); p = os.path.join(ROOT, "denial-genome.html")
    if "--check" in sys.argv:
        if open(p, encoding="utf-8").read() != page:
            print("denial-genome.html is STALE; run scripts/build_genome_page.py"); sys.exit(1)
        print("denial-genome.html is current")
    else:
        open(p, "w", encoding="utf-8").write(page); print("wrote", p, len(page), "bytes")
