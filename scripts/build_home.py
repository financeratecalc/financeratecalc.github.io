#!/usr/bin/env python3
"""index.html — the home page, generated. Identity: receipts for numbers from public records.

    python3 scripts/build_home.py [--check]

Every figure on the page is read from the data files and claim documents at build time (api/, data/programs/,
data/official/, claims/, corrections.json, eval/). Nothing is typed. The analytics snippet and the organisation /
website structured data live in assets/home-head.html; the claim JSON-LD block is added afterwards by
scripts/build_claim_jsonld.py. --check exits 1 if the committed page (ignoring that injected block) differs.
"""
import glob
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "index.html")
E = html.escape


def J(rel):
    return json.load(open(os.path.join(ROOT, rel), encoding="utf-8"))


def claim(cid):
    return J(f"claims/{cid}.json")


def bare(receipt):
    return receipt


def main():
    nat = J("api/index.json")["national"]
    fha = claim("national-fha-denial-rate-2025")
    va_d = J("data/programs/va-2025.json") if os.path.exists(os.path.join(ROOT, "data/programs/va-2025.json")) else None
    va = claim("va-national-denial-rate-2025") if va_d else None
    eds = sorted(f for f in glob.glob(os.path.join(ROOT, "data", "official", "*.json")) if os.path.basename(f) != "index.json")
    off = [json.load(open(f, encoding="utf-8")) for f in eds]
    revised = None
    for d in off:                                       # the most recent figure a later edition revised
        for fid, f in d["figures"].items():
            if f.get("revised_to") is not None:
                revised = (d, fid, f, claim(f"official-{d['source_id']}-{d['period']}-{fid}"))
    latest = off[-1] if off else None
    latest_c = claim(f"official-{latest['source_id']}-{latest['period']}-endorsements-count") if latest else None

    idx = J("claims/index.json")["claims"]
    rec = [c for c in idx if c.get("receipt")]
    fam = {"fha": 0, "prog": 0, "official": 0}
    for c in rec:
        i = c["id"]
        if i.startswith("official-"):
            fam["official"] += 1
        elif re.match(r"(outcome-)?(va|usda|conv)-", i):
            fam["prog"] += 1
        else:
            fam["fha"] += 1
    total = sum(fam.values())
    corr = J("corrections.json")["items"]
    own = [c for c in corr if c.get("type") != "atom"]
    qsi = J("eval/qsi/qsi.json")
    sight = J("eval/sightings.json")["named_citations"]["items"]
    engines = sorted({s["site"].split(" ")[0].replace("(answer", "").strip() for s in sight if "engine" in s["site"] or ".ai" in s["site"] or ".com" in s["site"]})
    mis = J("eval/misquotes-graded.json")["graded"]
    dry = J("provenance/release-day-dryrun.json")
    lenders = len(glob.glob(os.path.join(ROOT, "api", "lender", "*.json")))
    states = len(glob.glob(os.path.join(ROOT, "api", "state", "*.json")))

    def strip(rc, status, cls, sub):
        return (f'<li class="rc {cls}"><div class="rc-line"><code>{E(rc["receipt"])}</code></div>'
                f'<div class="rc-meta"><span class="stamp">{status}</span><span>{sub}</span>'
                f'<a href="/verify.html?r={E(rc["receipt"])}">Check this receipt</a></div></li>')

    strips = strip(fha, "Computed", "computed",
                   f'{nat["denials"]:,} denials of {nat["apps"]:,} FHA applications that reached a decision, 2025 federal HMDA record.')
    if va:
        n = va_d["national"]
        strips += strip(va, "Computed", "computed", f'{n["denials"]:,} denials of {n["decisioned_applications"]:,} VA applications that reached a decision, 2025.')
    if revised:
        d, fid, f, c = revised
        strips += strip(c, "Revised by the publisher", "revised",
                        f'HUD printed {E(f["display"])} {E(f["description"])} for {E(f["period"])}, then restated it as {f["revised_to"]:,} one edition later. The report does not mark the change.')
    elif latest_c:
        strips += strip(latest_c, "Restated as printed", "restated", f'{E(latest["document"]["title"])}, {E(latest["document"]["edition"])}.')

    fam_rows = (
        f'<tr><td><a href="/fha-denial-rates-top-100.html">FHA denial rates and application outcomes</a></td><td>Computed from the 2025 federal HMDA file</td><td class="n">{fam["fha"]}</td>'
        f'<td>National, {states} states and territories, {lenders} lenders, metro gaps, <a href="/where-fha-applications-end.html">five outcomes</a></td></tr>')
    if va:
        fam_rows += (f'<tr><td><a href="/va-loan-denial-rates-2025.html">VA denial rates and outcomes</a></td><td>Computed from the same file</td><td class="n">{fam["prog"]}</td>'
                     f'<td>National, every state, five outcomes. USDA and conventional are declared and next.</td></tr>')
    if off:
        fam_rows += (f'<tr><td><a href="/official-figures.html">HUD monthly FHA production figures</a></td><td>Restated as printed from the official report</td><td class="n">{fam["official"]}</td>'
                     f'<td>{len(off)} editions, each bound to the PDF&rsquo;s SHA-256, with revision status against the next edition</td></tr>')

    agg = {}
    for r in qsi["rows"]:                                # one line per engine; answers whose engine the owner did not name are grouped
        nm = r["engine"].split(" (")[0].split(" — ")[0].strip()
        nm = "Engine not named" if nm.upper().startswith("UNKNOWN") else nm
        agg.setdefault(nm, []).append(r["qsi"])
    eng_rows = "".join(f'<tr><td>{E(e)}</td><td class="n">{len(v)}</td><td class="n">{sum(v) / len(v):.2f}</td></tr>'
                       for e, v in sorted(agg.items(), key=lambda kv: (kv[0] == "Engine not named", -sum(kv[1]) / len(kv[1]))))

    def short(t, n=140):
        t = re.sub(r"^Our own error, found [0-9-]+( through [^:]+)?: ", "", t)
        t = t[0].upper() + t[1:]
        return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"
    last3 = "".join(f'<li><time>{E(c["date"])}</time> {E(short(c["title"]))}</li>' for c in own[:3])
    head_extra = open(os.path.join(ROOT, "assets", "home-head.html"), encoding="utf-8").read()
    desc = (f"FinanceRateCalc issues receipts for numbers from public records: {total} figures, each with a verifiable receipt, a use contract and a "
            f"corrections history. Computed from the federal HMDA file (FHA {nat['rate_pct']:.1f}% of {nat['apps']:,} decisions denied in 2025) or restated as printed "
            f"from official reports. Free, CC BY 4.0, no lender funding.")

    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>FinanceRateCalc — receipts for the numbers AI quotes from public records</title>
<meta name="description" content="{E(desc)}">
<meta property="og:title" content="Receipts for numbers from public records">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="https://financeratecalc.com/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="FinanceRateCalc">
<meta property="og:image" content="https://financeratecalc.com/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<link rel="license" type="application/rsl+xml" href="https://financeratecalc.com/rsl.xml">
<link rel="canonical" href="https://financeratecalc.com/">
<link rel="icon" href="/favicon.ico">
<link rel="alternate" type="application/rss+xml" title="FinanceRateCalc Weekly Signal" href="/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Besley:wght@500;700&family=Public+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
{head_extra.strip()}
<style>
:root{{--paper:#f2f5f3;--sheet:#fbfcfb;--ink:#14213d;--soft:#4a566e;--rule:#c8d1cc;--ok:#0b6e4f;--amber:#a4580c;--void:#9b1c1c;--wash:#e4ece8}}
*{{box-sizing:border-box;margin:0;padding:0}}
html{{-webkit-text-size-adjust:100%}}
body{{background:var(--paper);color:var(--ink);font-family:'Public Sans',system-ui,sans-serif;font-size:17px;line-height:1.6}}
a{{color:var(--ink);text-decoration-thickness:1px;text-underline-offset:3px}}
a:hover{{color:var(--ok)}}
a:focus-visible,input:focus-visible,button:focus-visible{{outline:3px solid var(--ok);outline-offset:2px}}
.skip{{position:absolute;left:-999px}}.skip:focus{{left:12px;top:12px;background:var(--sheet);padding:8px 12px;z-index:9}}
.bar{{display:flex;justify-content:space-between;align-items:baseline;gap:18px;flex-wrap:wrap;max-width:1080px;margin:0 auto;padding:22px 24px 0}}
.mark{{font-family:'Besley',Georgia,serif;font-weight:700;font-size:20px;text-decoration:none;letter-spacing:-.2px}}
.bar nav{{display:flex;gap:20px;flex-wrap:wrap;font-size:15px}}
.bar nav a{{text-decoration:none;color:var(--soft)}}.bar nav a:hover{{color:var(--ink);text-decoration:underline}}
main{{max-width:1080px;margin:0 auto;padding:0 24px 80px}}
h1{{font-family:'Besley',Georgia,serif;font-weight:700;font-size:clamp(34px,5.6vw,60px);line-height:1.06;letter-spacing:-1.2px;max-width:17ch;margin:64px 0 22px}}
.lede{{font-size:clamp(18px,2vw,21px);line-height:1.55;max-width:62ch;color:var(--soft)}}
.lede b{{color:var(--ink);font-weight:600}}
h2{{font-family:'Besley',Georgia,serif;font-weight:700;font-size:clamp(24px,3vw,32px);line-height:1.15;letter-spacing:-.5px;margin:84px 0 14px;max-width:26ch}}
p{{max-width:68ch}}p+p{{margin-top:12px}}
.roll{{list-style:none;margin:44px 0 0;border-top:2px solid var(--ink)}}
.rc{{padding:18px 0 16px;border-bottom:1px dashed var(--rule)}}
.rc-line code{{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:clamp(13px,1.75vw,19px);font-weight:500;word-break:break-all;letter-spacing:-.2px}}
.rc-meta{{display:flex;gap:14px;flex-wrap:wrap;align-items:baseline;margin-top:8px;font-size:15px;color:var(--soft)}}
.rc-meta a{{white-space:nowrap}}
.stamp{{font-weight:600;font-size:13.5px;padding:1px 9px 2px;border:1.5px solid currentColor;border-radius:3px;transform:rotate(-1.2deg);display:inline-block}}
.computed .stamp{{color:var(--ok)}}.restated .stamp{{color:var(--ink)}}.revised .stamp{{color:var(--amber)}}
.check{{margin:34px 0 0;background:var(--sheet);border:1px solid var(--rule);padding:22px;max-width:760px}}
.check label{{display:block;font-weight:600;margin-bottom:8px}}
.check .row{{display:flex;gap:10px;flex-wrap:wrap}}
.check input{{flex:1 1 320px;font:500 15px 'IBM Plex Mono',ui-monospace,monospace;padding:12px 12px;border:1.5px solid var(--ink);background:#fff;color:var(--ink);min-width:0}}
.check button{{font:600 16px 'Public Sans',sans-serif;padding:12px 20px;background:var(--ink);color:#fff;border:0;cursor:pointer}}
.check button:hover{{background:var(--ok)}}
.check small{{display:block;margin-top:10px;color:var(--soft);font-size:14px}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:0;margin-top:26px;border-top:2px solid var(--ink)}}
.two>div{{padding:22px 28px 6px 0}}.two>div+div{{padding-left:28px;border-left:1px solid var(--rule)}}
.two h3{{font-family:'Besley',Georgia,serif;font-size:21px;margin-bottom:8px}}
.two ul{{margin:10px 0 0 18px;color:var(--soft);font-size:16px}}
table{{border-collapse:collapse;width:100%;margin-top:22px;font-size:16px}}
th{{text-align:left;font-weight:600;font-size:14px;color:var(--soft);padding:8px 14px 8px 0;border-bottom:2px solid var(--ink)}}
td{{padding:12px 14px 12px 0;border-bottom:1px solid var(--rule);vertical-align:top}}
td.n,th.n{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
.split{{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,4fr);gap:56px;align-items:start}}
.log{{list-style:none;margin-top:18px}}.log li{{padding:11px 0;border-bottom:1px solid var(--rule);font-size:16px}}
.log time{{font-family:'IBM Plex Mono',monospace;font-size:13.5px;color:var(--amber);margin-right:8px}}
.doors{{list-style:none;margin-top:22px;border-top:2px solid var(--ink)}}
.doors li{{display:grid;grid-template-columns:minmax(0,16rem) 1fr;gap:24px;padding:16px 0;border-bottom:1px solid var(--rule)}}
.doors b{{font-weight:600}}
.fine{{margin-top:90px;padding-top:22px;border-top:2px solid var(--ink);font-size:15px;color:var(--soft)}}
.fine .links{{display:flex;flex-wrap:wrap;gap:6px 18px;margin-bottom:16px}}
.fine p{{max-width:86ch}}
@media(max-width:760px){{.two,.split{{grid-template-columns:1fr}}.two>div+div{{padding-left:0;border-left:0;border-top:1px solid var(--rule)}}.doors li{{grid-template-columns:1fr;gap:4px}}h1{{margin-top:44px}}td,th{{padding-right:10px}}.hide-s{{display:none}}}}
@media(prefers-reduced-motion:no-preference){{.rc{{animation:feed .5s ease-out both}}.rc:nth-child(2){{animation-delay:.12s}}.rc:nth-child(3){{animation-delay:.24s}}@keyframes feed{{from{{opacity:0;transform:translateY(-8px)}}to{{opacity:1;transform:none}}}}}}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="bar"><a class="mark" href="/">FinanceRateCalc</a>
<nav aria-label="Site"><a href="/verify.html">Check a receipt</a><a href="/official-figures.html">Official figures</a><a href="/fha-denial-rates-top-100.html">FHA data</a><a href="/corrections.html">Corrections</a><a href="/mcp-server.html">For AI agents</a><a href="/site-index.html">Index</a></nav></div>
<main id="main">
<h1>A receipt for every number taken from the public record.</h1>
<p class="lede">AI systems quote statistics with the wrong month, the wrong denominator, or a value the publisher has since revised. FinanceRateCalc publishes figures from public records with a <b>receipt</b> attached: a short code that fixes the number to its source file, its definition and its period, and that anyone can check without asking us.</p>

<ul class="roll" aria-label="Three receipts issued by this site">
{strips}
</ul>

<form class="check" action="/verify.html" method="get">
<label for="r">Check a receipt</label>
<div class="row"><input id="r" name="r" type="text" inputmode="text" autocomplete="off" spellcheck="false" placeholder="⟦FRC:…⟧ paste a receipt from an AI answer or an article" required>
<button type="submit">Check receipt</button></div>
<small>The answer is one of: current, superseded by a correction, or not ours. Got a sentence instead of a receipt? <a href="/check-answer.html">Check an AI answer</a>.</small>
</form>

<h2>Two kinds of receipt, and what each one attests</h2>
<div class="two">
<div><h3>Computed</h3>
<p>We count the figure ourselves from the complete public file, with published code. The receipt binds the number to the file&rsquo;s hash, the universe and the denominator.</p>
<ul><li>{nat["apps"]:,} FHA decisions in 2025; {nat["rate_pct"]:.1f}% denied</li><li>A full rebuild reproduces {dry.get("numeric_equal", 0):,} of {dry.get("numeric_fields", 0):,} published fields</li><li>An unaffiliated HMDA package arrives at the same counts</li></ul></div>
<div><h3>Restated as printed</h3>
<p>An agency published the figure; we compute nothing. The receipt binds the number to the official document&rsquo;s hash, its table and row, its period &mdash; and records when a later edition changes it.</p>
<ul><li>HUD&rsquo;s monthly FHA production report, {len(off)} editions</li><li>{sum(1 for d in off for f in d["figures"].values() if f.get("revised_to") is not None)} figures already revised by the publisher, unmarked in the report</li><li>An endorsement is not an application: the contract says so</li></ul></div>
</div>

<h2>What carries a receipt today</h2>
<table>
<thead><tr><th>Figures</th><th class="hide-s">How</th><th class="n">Receipts</th><th>Coverage</th></tr></thead>
<tbody>{fam_rows.replace("<td>Computed", '<td class="hide-s">Computed').replace("<td>Restated", '<td class="hide-s">Restated')}
<tr><td><b>All receipts</b></td><td class="hide-s"></td><td class="n"><b>{total}</b></td><td>One file for machines: <a href="/llms-full.txt">llms-full.txt</a> &middot; signed snapshot in a <a href="/transparency/log.json">public log</a></td></tr></tbody>
</table>

<div class="split">
<div>
<h2>We publish our own errors</h2>
<p>A receipt is only worth something if the publisher admits when a number changes. The log has {len(own)} dated entries; several were found because an AI system quoted a stale copy of ours exactly.</p>
<ul class="log">{last3}</ul>
<p style="margin-top:14px"><a href="/corrections.html">Read the corrections log</a> &middot; <a href="/corrections.json">feed for machines</a></p>
</div>
<div>
<h2>How faithfully AI systems carry our figures</h2>
<p>{qsi["answers_graded"]} archived answers that quote us, graded on seven qualifiers: value, period, denominator, program, universe, no added claim, attribution. 1.00 means all seven survived.</p>
<table><thead><tr><th>Answer engine</th><th class="n">Answers</th><th class="n">Score</th></tr></thead><tbody>{eng_rows}</tbody></table>
<p style="margin-top:14px"><a href="/qualifier-survival.html">Method and every answer</a> &middot; <a href="/misquotes.html">{len(mis)} graded misquotes</a></p>
</div>
</div>

<h2>Where to start</h2>
<ul class="doors">
<li><b>An AI gave me a number</b><span>Paste the receipt above, or <a href="/check-answer.html">paste the whole answer</a>: we mark what the number carries and what was added.</span></li>
<li><b>I was denied an FHA loan</b><span><a href="/denial-code-lookup.html">What the reason on your letter means</a> and what to ask the lender in writing. No prediction, no lender pick.</span></li>
<li><b>I report or research</b><span>The record: <a href="/fha-denial-rates-top-100.html">100 largest FHA lenders</a>, <a href="/fha-denial-rates-by-state.html">every state</a>, <a href="/metro/index.html">metros</a>, <a href="/why-fha-denial-rates-differ.html">why published rates differ</a>, <a href="/methodology.html">method</a>, <a href="/reconciliation.html">how to check us</a>.</li>
<li><b>I build agents</b><span><a href="/mcp-server.html">MCP server</a> with {18} tools, <a href="/data-catalog.html">open datasets</a>, <a href="/spec/receipt-1.0.md">the Receipt 1.0 format</a>, <a href="/pricing.html">pricing</a>. Reading is free; the licence is <a href="/license.html">CC BY 4.0</a>.</li>
</ul>

<div class="fine">
<div class="links"><a href="/site-index.html">Every page</a><a href="/metro/index.html">Metro pages</a><a href="/stat/index.html">Question pages</a><a href="/city/index.html">City pages</a><a href="/fha-denial-rates-by-lender.html">Lender table</a><a href="/fha-denial-reasons-by-lender.html">Denial reasons</a><a href="/door-effect.html">The door effect</a><a href="/benchmark-scorecard.html">AI benchmark</a><a href="/answers.html">Answers</a><a href="/tools.html">Tools</a><a href="/top-100-pack.html">Top-100 pack</a><a href="/glossary.html">Glossary</a><a href="/data.html">Data</a></div>
<p>Published by Ziya Yeti&#351;, 23 years in bank credit, working independently. No lender, servicer, vendor or AI company funds this site, and it carries no advertising. Figures are historical aggregates from public records: not predictions about any application, not ratings of any lender, not advice. Computed figures have been reproduced by an unaffiliated implementation and not yet by an unaffiliated person; <a href="/reconciliation.html">the specification for checking them is public</a>.</p>
</div>
</main>
</body>
</html>
'''
    if "--check" in sys.argv:
        cur = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        cur = re.sub(r'<script type="application/ld\+json" id="frc-claims-jsonld">.*?</script>\n?', "", cur, flags=re.S)
        ok = cur.strip() == page.strip()
        print("home page:", "current" if ok else "STALE"); sys.exit(0 if ok else 1)
    open(OUT, "w", encoding="utf-8").write(page)
    print(f"wrote index.html: {total} receipts ({fam}), {len(own)} corrections, {qsi['answers_graded']} graded answers")


if __name__ == "__main__":
    main()
