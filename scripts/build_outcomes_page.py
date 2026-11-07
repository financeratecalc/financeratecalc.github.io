#!/usr/bin/env python3
"""where-fha-applications-end.html from data/application-outcomes-2025.json and the outcome-* claim documents.

One page, generated, idempotent (`--check` exits 1 if the committed page differs). National five ends with receipts,
then the lenders that have a site page, alphabetical (never by any rate), each row carrying the receipt of its
ended-without-decision share. No ranking, no verdict, no cause.
"""
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "where-fha-applications-end.html")
d = json.load(open(os.path.join(ROOT, "data", "application-outcomes-2025.json"), encoding="utf-8"))


def claim(cid):
    return json.load(open(os.path.join(ROOT, "claims", cid + ".json"), encoding="utf-8"))


n = d["national"]
ends = [("originated", "Originated", "the loan was made"), ("approved_not_accepted", "Approved, not accepted", "the lender said yes; the applicant did not take the loan"),
        ("denied", "Denied", "the lender said no"), ("withdrawn", "Withdrawn", "the applicant stopped before a decision"), ("closed_incomplete", "Closed for incompleteness", "the file never became complete")]
rc = {k: claim(f"outcome-{k.replace('_', '-')}-2025")["receipt"] for k, _, _ in ends}
ana = claim("outcome-ana-share-2025")
fmt = lambda x: f"{x:,}"

rows = []
for L in sorted([l for l in d["lenders"] if l.get("slug")], key=lambda l: (l.get("name") or "").lower()):
    o = L["outcomes"]; c = claim(f"outcome-{L['slug']}-2025")
    rows.append(f'<tr><td><a href="/{L["slug"]}-fha-denial-rate.html">{html.escape(L["name"] or L["lei"])}</a></td><td class=n>{fmt(L["applications_acted_on"])}</td>'
                f'<td class=n>{o["originated"]["share_of_acted_pct"]}%</td><td class=n>{o["approved_not_accepted"]["share_of_acted_pct"]}%</td><td class=n>{o["denied"]["share_of_acted_pct"]}%</td>'
                f'<td class=n>{o["withdrawn"]["share_of_acted_pct"]}%</td><td class=n>{o["closed_incomplete"]["share_of_acted_pct"]}%</td>'
                f'<td class=n><b>{c["display_value"]}</b></td><td class=n>{L["ana_share_pct"]}%</td><td class=n>{L["denial_rate_pct"]}%</td><td class="r">{c["receipt"]}</td></tr>')

page = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Where FHA applications end: five outcomes, by lender, 2025 | FinanceRateCalc</title>
<meta name="description" content="Of {fmt(n['applications_acted_on'])} FHA applications lenders acted on in 2025, {n['outcomes']['originated']['share_of_acted_pct']}% were originated, {n['outcomes']['withdrawn']['share_of_acted_pct']}% withdrawn, {n['outcomes']['denied']['share_of_acted_pct']}% denied, {n['outcomes']['closed_incomplete']['share_of_acted_pct']}% closed for incompleteness and {n['outcomes']['approved_not_accepted']['share_of_acted_pct']}% approved but not accepted. Every figure with a receipt; lenders alphabetical, never ranked.">
<link rel="canonical" href="https://financeratecalc.com/where-fha-applications-end.html">
<style>body{{background:#08090c;color:#e8e4da;font-family:'DM Sans',system-ui,sans-serif;margin:0;line-height:1.6}}.wrap{{max-width:1040px;margin:0 auto;padding:36px 18px 70px}}h1{{font-family:Georgia,serif;font-size:27px;color:#f5f2ea;line-height:1.25}}h2{{font-family:Georgia,serif;font-size:19px;color:#f5f2ea;margin-top:28px}}.kicker{{font-family:monospace;font-size:11px;letter-spacing:2px;color:#C8A84B;text-transform:uppercase}}a{{color:#C8A84B}}table{{border-collapse:collapse;width:100%;font-size:13.5px}}th,td{{padding:6px 8px;border-bottom:1px solid rgba(255,255,255,.08);text-align:left;vertical-align:top}}th{{color:rgba(255,255,255,.6);font-weight:600;font-size:12px}}td.n{{font-family:monospace;text-align:right;white-space:nowrap}}td.r{{font-family:monospace;font-size:10.5px;color:rgba(255,255,255,.5);word-break:break-all}}.card{{border:1px solid rgba(255,255,255,.12);border-radius:10px;padding:14px 16px;margin:14px 0;background:#0b0d12}}.small{{font-size:12.5px;opacity:.75}}.big{{font-family:monospace;font-size:22px;color:#f5f2ea}}@media(max-width:760px){{table{{font-size:12px}}td.r{{display:none}}}}</style></head>
<body>
<nav data-frc-nav="1" aria-label="Site" style="font-family:system-ui,sans-serif;font-size:12.5px;padding:8px 16px;background:#0b0d12;border-bottom:1px solid rgba(255,255,255,.08);display:flex;gap:14px;flex-wrap:wrap;align-items:center"><a href="/" style="color:#C8A84B;font-weight:700;text-decoration:none">FinanceRateCalc</a><a href="/fha-denial-rates-top-100.html" style="color:rgba(255,255,255,.7);text-decoration:none">Lenders</a><a href="/fha-denial-rates-by-state.html" style="color:rgba(255,255,255,.7);text-decoration:none">States</a><a href="/why-fha-denial-rates-differ.html" style="color:rgba(255,255,255,.7);text-decoration:none">Why rates differ</a><a href="/site-index.html" style="color:rgba(255,255,255,.7);text-decoration:none">Index</a></nav>
<div class="wrap">
<div class="kicker">FinanceRateCalc &middot; application outcomes &middot; 2025 &middot; generated {d['generated'][:10]}</div>
<h1>Where FHA applications end: the five outcomes the record keeps</h1>
<p><b>Short answer.</b> A denial rate counts one of five ends. In 2025, lenders acted on <b>{fmt(n['applications_acted_on'])}</b> FHA applications (reverse mortgages excluded; purchased loans and preapproval requests not counted). Of those, <b>{n['outcomes']['originated']['share_of_acted_pct']}%</b> were originated, <b>{n['outcomes']['withdrawn']['share_of_acted_pct']}%</b> were withdrawn by the applicant, <b>{n['outcomes']['denied']['share_of_acted_pct']}%</b> were denied, <b>{n['outcomes']['closed_incomplete']['share_of_acted_pct']}%</b> were closed for incompleteness and <b>{n['outcomes']['approved_not_accepted']['share_of_acted_pct']}%</b> were approved but not accepted. More FHA applications were withdrawn than denied. The site&rsquo;s published denial rate, <b>22.1%</b>, is the same denials over a smaller base: the {fmt(n['decisioned_applications'])} applications that reached a credit decision (originated, approved-not-accepted, denied). Both are right; they answer different questions (<a href="/why-fha-denial-rates-differ.html">why FHA denial rates differ</a>, question 5).</p>
<h2>National, 2025</h2>
<table><thead><tr><th>End</th><th>What it means</th><th>Applications</th><th>Share of acted on</th><th>Receipt</th></tr></thead><tbody>
{"".join(f'<tr><td><b>{lab}</b></td><td>{desc}</td><td class=n>{fmt(n["outcomes"][k]["n"])}</td><td class=n><b>{n["outcomes"][k]["share_of_acted_pct"]}%</b></td><td class="r">{rc[k]}</td></tr>' for k, lab, desc in ends)}
</tbody></table>
<div class="card"><div class="small">The approval that walked away</div><div class="big">{ana['display_value']}</div><div>of the {fmt(ana['claim']['n'])} FHA applications lenders approved in 2025 were not accepted by the applicant. <span class="r">{ana['receipt']}</span></div><div class="small">The record does not say why: pricing, a competing offer, a purchase that fell through and reporting practice are not separable here.</div></div>
<h2>By lender, alphabetical</h2>
<p class="small">Lenders with a page on this site ({len(rows)}). Shares are of applications the lender acted on; the last column is the site&rsquo;s denial rate on the decisioned base, for reconciliation. <b>Ended without decision</b> = withdrawn + closed for incompleteness, and carries the row&rsquo;s receipt. The table is alphabetical and nothing on this page sorts by any rate: a high share in any column can be a process, a market, an applicant-pool or a reporting fact, and the record does not say which. This is not a comparison of lender quality and not a prediction for any applicant.</p>
<table><thead><tr><th>Lender</th><th>Acted on</th><th>Originated</th><th>Approved, not accepted</th><th>Denied</th><th>Withdrawn</th><th>Closed incomplete</th><th>Ended without decision</th><th>Approvals not accepted</th><th>Denial rate (decisioned)</th><th>Receipt</th></tr></thead><tbody>
{"".join(rows)}
</tbody></table>
<h2>Definitions</h2>
<ul class="small"><li><b>Universe:</b> {html.escape(d['universe'])}.</li>
<li><b>Share of acted on:</b> {d['definitions']['share_of_acted_pct']}. <b>Denial rate:</b> {d['definitions']['denial_rate_pct']}. <b>Approvals not accepted:</b> {d['definitions']['ana_share_pct']}.</li>
<li><b>Does not establish:</b> {"; ".join(html.escape(x) for x in d['does_not_establish'])}.</li>
<li><b>Source and build:</b> CFPB HMDA 2025 public LAR ({html.escape(d.get('source_url', ''))}), input sha256 <code>{d.get('input_sha256', '')[:16]}&hellip;</code>, code <code>scripts/application_outcomes.py</code> at <code>{d.get('code_commit', '')[:10]}</code>; data file <a href="/data/application-outcomes-2025.json">application-outcomes-2025.json</a> ({len(d['lenders'])} lenders with &ge; {d['min_lender_applications']} applications acted on, LEI order); the same figures as a CSV whose column names state each denominator: <a href="/data/fha-application-outcomes-2025.csv">fha-application-outcomes-2025.csv</a>.</li>
<li><b>Verify any receipt:</b> <a href="/verify.html">verify.html</a> or <code>GET https://frc-mcp.ziyetis.workers.dev/verify?r=&lt;receipt&gt;</code>; the hashed object is the <code>claim</code> block of <code>/claims/outcome-&lt;id&gt;-2025.json</code>.</li></ul>
<p class="small">First published 2026-11-01. Nothing on this page is advice about any loan. Source: FinanceRateCalc analysis of the public CFPB HMDA 2025 record; historical aggregate only. CC BY 4.0.</p>
</div>
</body></html>
'''
if "--check" in sys.argv:
    cur = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else None
    print("outcomes page:", "current" if cur == page else "STALE")
    sys.exit(0 if cur == page else 1)
open(OUT, "w", encoding="utf-8").write(page)
print(f"wrote {os.path.relpath(OUT, ROOT)}: {len(rows)} lender rows")
