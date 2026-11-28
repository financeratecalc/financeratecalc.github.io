#!/usr/bin/env python3
"""Decide the legacy research pages Black Hole Lender, Black Hole Report, Shock Beta and CLTV 85 Trap (2026-11-28).

Each page got one of three outcomes: receipts and scope added (none qualified), relabelled as a provisional research
note (Black Hole Lender), or retired (the other three). The figures these pages fed into other pages are removed
there too: the Shock Beta and OFI cards, the "black-hole cell" and "statistical relatives" sections on eleven lender
pages, the paid-report boxes, and two entries of data/citable.json. Buttons left from a retired assistant that read
"Analyze a file" or "Get a file analysis" now say where they go. Idempotent; reports what it changed.

    python3 scripts/legacy_research_pages.py [--check]
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHOR = "/corrections.html#2026-11-28-legacy-research-pages"
NOTE = "/black-hole-lender.html"

RETIRE = {
    "shock-beta.html": ("Shock Beta",
        "This page gave eleven lenders a &ldquo;Shock Beta&rdquo; score from 0 to 100, described as a world-first measure of how violently each lender&rsquo;s underwriting reacts to economic shocks, and said the score had been validated at r&nbsp;=&nbsp;+0.946. "
        "On 28 November 2026 the scores were recomputed from the page&rsquo;s own data file with the method the page stated, and they did not come out as published: Freedom 100 and NewRez 90 on the page, NewRez 100 and Freedom 99 recomputed; Rocket 9 on the page, 16 recomputed; loanDepot 24 on the page, 37 recomputed. "
        "The page did not show enough to check its correlation, and a correlation across eleven lenders could not carry the prediction it was used for. A score that does not reproduce from its own data cannot be defended, and this site does not forecast how named lenders will behave."),
    "cltv-85-trap.html": ("The CLTV 85 Trap",
        "This page said that above 85% combined loan-to-value FHA denial rates hit a wall that is &ldquo;not an FHA rule&rdquo; but a lender overlay, told a reader what named lenders did to applicants &ldquo;with your profile&rdquo;, and asked readers to &ldquo;route to a lender with a flat surface above 85&rdquo;. "
        "This site&rsquo;s own check of that claim says part of the jump is likely program mechanics (FHA cash-out refinances have been capped at 80% since 2019), so the page stated as fact a cause the record does not show; and sending a reader to a lender is a recommendation this site does not make."),
    "underwriting-weather.html": ("Underwriting Weather Map",
        "This page, dated May 2026, gave &ldquo;weather&rdquo; ratings and overlay scores from 8 to 72 for six kinds of lender (VA specialists, credit unions, conservative banks and others), described their current underwriting without a source, and told readers near 48&ndash;50% debt-to-income to &ldquo;consider FHA or portfolio alternatives&rdquo;. "
        "Its scores came from the Overlay Friction Index, whose method the page described as agency guideline comparison and &ldquo;typical lender behavior&rdquo;; no figure on it had a source a reader could check. Advice to one kind of borrower about where to go is a recommendation this site does not make."),
    "lender-response-surface.html": ("Lender Response Surface Explorer",
        "This page drew each of six lenders&rsquo; denial rates over debt-to-income and loan-to-value as a 3D &ldquo;surface&rdquo; with &ldquo;cliffs&rdquo;, &ldquo;black holes&rdquo; and &ldquo;safe zones&rdquo;, and asked a denied reader to enter their numbers to &ldquo;see exactly where your file lands on the cliff, and which door has a ramp instead&rdquo;. "
        "It gave its basis both as &ldquo;310K FHA records&rdquo; and as &ldquo;1,187,606 records&rdquo;, kept cells with as few as 30 applications, and the script behind its data file is not published. Placing one reader&rsquo;s file and pointing to another lender is a prediction and a recommendation this site does not make."),
    "mortgage-correlation-research.html": ("6 Correlations in Mortgage Data",
        "This page reported six correlations (for example r&nbsp;=&nbsp;+0.618 between FHA denial rates and delinquency two years later, r&nbsp;=&nbsp;&minus;0.696 between unemployment and denial rates), each computed from seven or eight yearly values, with yearly denial rates that are not this site&rsquo;s receipted national rate (27.1% for 2025 against a receipted 22.1%), causal stories for each, and the advice &ldquo;in a tightening cycle, route away from rate-sensitive lenders&rdquo;. "
        "A correlation of a handful of yearly points cannot carry &ldquo;predict&rdquo;, and routing readers away from named lenders is a recommendation this site does not make. Its statements are listed as not citable in <a href=\"/data/citable-queue.json\">the citation queue</a>."),
    "black-hole-report.html": ("The Mortgage Black Hole Report 2025",
        "This page sold, for $49, an 11-page PDF that mapped each of six lenders&rsquo; &ldquo;black hole&rdquo; (the debt-to-income and loan-to-value cell with its highest denial rate) and, for each, &ldquo;escape-route tables&rdquo; of how the other five lenders had treated the same zone, sorted. "
        "A sorted list of other lenders for a reader&rsquo;s zone is a lender recommendation, which this site does not make, and the report&rsquo;s figures cannot be reproduced from this site&rsquo;s published code: see the <a href=\"/black-hole-lender.html\">research note</a> that records what is known about them."),
}

CELLS = os.path.join(ROOT, "_data", "black_hole_2025.json")
NAMES = {"Rocket": "Rocket Mortgage", "PennyMac": "PennyMac", "Freedom": "Freedom Mortgage", "CrossCountry": "CrossCountry Mortgage",
         "Guild": "Guild Mortgage", "MrCooper": "Mr. Cooper (Nationstar)"}


def shell(title, desc, body, robots="noindex,follow", fname=""):
    src = open(os.path.join(ROOT, "bank-rejection-engine.html"), encoding="utf-8").read()
    nav = re.search(r'<nav data-frc-nav="1".*?</nav>', src, re.S).group(0)
    style = re.search(r"<style>.*?</style>", src, re.S).group(0)
    fonts = re.search(r'<link href="https://fonts.googleapis.com[^>]+>', src).group(0)
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}"><meta name="robots" content="{robots}">
<link rel="canonical" href="https://financeratecalc.com/{fname}">
{fonts}
{style}</head>
<body>
{nav}
<div class="wrap">{body}
</div>
</body></html>
'''


def notice(fname, title, what):
    plain = re.sub(r"<[^>]+>|&[a-z]+;", "", what)[:150].replace('"', "")
    body = f'''<h1>This page has been retired.</h1>
<!-- rulecheck:ignore: describes the retired page --><div class="box">{what} The page was withdrawn on 28 November 2026 and now records that.</div>
<p>What this site does instead: it shows what the record supports and where the evidence ends &mdash; <a href="/fha-loan-denied-now-what.html">The Denial Map</a> &middot; <a href="/evidence-navigator.html">Evidence Navigator</a> &middot; <a href="/fha-denial-rates-top-100.html">FHA denial rates by lender, with receipts</a> &middot; <a href="{ANCHOR}">Corrections log</a>.</p>
<p style="font-size:13px;color:#8a8678">The data behind everything remains free.</p>'''
    return shell(f"{title} — Retired | FinanceRateCalc", f"Retired page. {plain}", body, fname=fname)


def research_note():
    cells = json.load(open(CELLS, encoding="utf-8"))
    rows = "".join(
        f'<tr><td>{NAMES[k]}</td><td>{v["dti_min"]}&ndash;{v["dti_max"]}</td><td>{v["cltv_min"]}&ndash;{v["cltv_max"]}</td>'
        f'<td style="text-align:right">{v["rate"]:.1f}%</td><td style="text-align:right">{v["n"]}</td></tr>'
        for k, v in sorted(cells.items(), key=lambda kv: NAMES[kv[0]]))
    body = f'''<h1>Highest-denial cells by lender, 2025: a provisional research note</h1>
<!-- rulecheck:ignore: records what the earlier page said --><div class="box"><b>Provisional. Not receipted. Do not cite as a finding.</b> These six figures were computed once in 2026 from the 2025 HMDA loan-level file. The script that produced them is not in this site&rsquo;s published code, so the site cannot reproduce them today. They stay here, relabelled on 28 November 2026, so that anyone who read or cited the earlier page &ldquo;The Black Hole Lender&rdquo; can see what it said and what is wrong with it.</div>
<p>For each of six lenders, the cell of debt-to-income ratio and combined loan-to-value with the highest denial rate among cells with at least 50 applications, as recorded in <code>_data/black_hole_2025.json</code>. Lenders in alphabetical order.</p>
<table style="width:100%;border-collapse:collapse;font-size:15px;margin:10px 0 24px"><thead><tr><th style="text-align:left">Lender</th><th style="text-align:left">DTI %</th><th style="text-align:left">CLTV %</th><th style="text-align:right">Denial rate</th><th style="text-align:right">Applications</th></tr></thead><tbody>{rows}</tbody></table>
<h2>What is wrong with these figures, or not yet shown</h2>
<ul>
<li><b>Chosen as the highest.</b> Each figure is the highest of many cells for its lender, some with only 63 applications. The highest of many small cells looks more extreme than the lender&rsquo;s record is. The earlier page did not say how many cells were compared.</li>
<li><b>Not the same applicants.</b> The earlier page compared lenders as if they faced &ldquo;the same profile&rdquo;. The cells it compared are different cells: PennyMac&rsquo;s is DTI 36&ndash;38 with CLTV 100&ndash;105, CrossCountry&rsquo;s is DTI 48&ndash;50 with CLTV 80&ndash;85.</li>
<li><b>Inconsistent with itself.</b> The earlier page said 248 of 249 PennyMac applications in its cell were denied (99%). Its own data file says 98.8%, which is 246 of 249.</li>
<li><b>Method not checkable.</b> The method line named a loan-product code (&ldquo;2 or 32&rdquo;) that is not how the public file marks FHA loans, and counted only originated and denied applications. Without the script, it cannot be told which records were used.</li>
<li><b>Cause not shown.</b> The earlier page called these zones lender overlays. The record shows how many applications were denied, not why. Part of a high-CLTV cell can come from program limits rather than a lender&rsquo;s choice.</li>
<li><b>Not about one file.</b> A cell&rsquo;s rate describes the applications that lender received. It does not say how the lender would decide one application, and it is not a reason to choose or avoid a lender.</li>
</ul>
<p>What would make these citable: the same cells recomputed from the public file by a published script, with the number of cells compared, at least 100 applications per cell, and a receipt for each figure. Until then this note stays provisional. The paid report built on these cells and the page that sent readers to other lenders are retired; the <a href="{ANCHOR}">corrections log</a> records why.</p>
<p>Figures with receipts: <a href="/fha-denial-rates-top-100.html">FHA denial rates, 100 largest lenders</a>.</p>'''
    return shell("Highest-Denial Cells by Lender, 2025 — Provisional Research Note | FinanceRateCalc",
                 "Provisional research note: six lender cells with high 2025 FHA denial rates, computed once and not reproducible from published code, with what is wrong with them. Not receipted.",
                 body, fname="black-hole-lender.html")


SUB = [
    # lender pages: cards, profile line and sections fed by retired pages
    (re.compile(r'<div class="card"><div class="k">Shock Beta</div><div class="v">[^<]*</div></div>\n'), ""),
    (re.compile(r'<div class="card"><div class="k">Macro sensitivity \(OFI\)</div><div class="v">[^<]*</div></div>\n'), ""),
    (re.compile(r'<p><b style="color:#fff">Shock profile:</b>.*?</p>\n', re.S), ""),
    (re.compile(r'<h2>The black-hole cell</h2><p>.*?</p>\n', re.S), ""),
    (re.compile(r'<h2>Statistical relatives</h2>\n<p>.*?</p>\n', re.S), ""),
    # paid report boxes and links
    (re.compile(r'<!-- BLACK HOLE REPORT CTA -->\n<div[^>]*>.*?Secure checkout by Lemon Squeezy</span>\n</div>\n', re.S), ""),
    (re.compile(r'<a class="cta" href="/black-hole-report\.html"[^>]*>[^<]*</a>\n?'), ""),
    # Shock Beta links in research pages
    (re.compile(r'<a href="/shock-beta\.html" style="color:rgba\(255,255,255,\.45\);text-decoration:none;">⚡ Shock Beta</a>\n'), ""),
    (re.compile(r'\s*<div class="cta-strip"[^>]*>\s*<p>New: these findings led to Shock Beta.*?</div>\n', re.S), "\n"),
    (re.compile(r'<a href="/shock-beta\.html" style="[^"]*">Shock Beta →</a>'), "<span></span>"),
    (re.compile(r' &nbsp;·&nbsp; <a href="/shock-beta\.html">Shock Beta</a>'), ""),
    # buttons left from the retired assistant
    (re.compile(r'(<a [^>]*href="/evidence-navigator\.html"[^>]*>)Get a file analysis — free →</a>'), r"\1Evidence Navigator →</a>"),
    (re.compile(r'(<a [^>]*href="/evidence-navigator\.html"[^>]*>)Analyze a file →</a>'), r"\1Evidence Navigator →</a>"),
    (re.compile(r'(<a [^>]*href="/evidence-navigator\.html"[^>]*>)⚡ Analyze a file</a>'), r"\1Evidence Navigator</a>"),
    (re.compile(r'(<a [^>]*href="/evidence-navigator\.html"[^>]*>)Route my file(?: — free)? →</a>'), r"\1Evidence Navigator →</a>"),
    (re.compile(r'(<a [^>]*href="/evidence-navigator\.html"[^>]*>)⚡ Route my file</a>'), r"\1Evidence Navigator</a>"),
    # search index and dictionary
    (re.compile(r'\{"t": "The Black Hole Report 2025", "u": "/black-hole-report\.html"[^}]*\},\s*'), ""),
    (re.compile(r'\{"t": "Shock Beta", "u": "/shock-beta\.html"[^}]*\},\s*'), ""),
    (re.compile(r'\{"term": "Shock Beta".*?"link_text": "[^"]*"\},\s*', re.S), ""),
]
CITABLE_DROP = ("/black-hole-report.html", "/shock-beta.html")


def main():
    check = "--check" in sys.argv
    changed = []

    def put(rel, new):
        p = os.path.join(ROOT, rel)
        if open(p, encoding="utf-8").read() != new:
            changed.append(rel)
            if not check:
                open(p, "w", encoding="utf-8").write(new)

    for fname, (title, what) in RETIRE.items():
        put(fname, notice(fname, title, what))
    put("black-hole-lender.html", research_note())
    for f in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True):
        rel = os.path.relpath(f, ROOT)
        if rel.startswith(("scripts/", "eval/", "readers/")) or rel in RETIRE or rel in ("black-hole-lender.html", "corrections.html", "watch.html"):
            continue
        s = open(f, encoding="utf-8").read(); o = s
        for rx, rep in SUB:
            s = rx.sub(rep, s)
        if s != o:
            put(rel, s)
    cp = os.path.join(ROOT, "data", "citable.json")
    d = json.load(open(cp, encoding="utf-8"))
    keep = [x for x in d["statistics"] if not x.get("url", "").endswith(CITABLE_DROP)]
    if len(keep) != len(d["statistics"]):
        d["statistics"] = keep
        put("data/citable.json", json.dumps(d, indent=1) + "\n")
    print(f"files rewritten: {len(changed)}")
    for c in changed:
        print("  ", c)
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
