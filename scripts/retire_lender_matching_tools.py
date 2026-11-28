#!/usr/bin/env python3
"""Retire the tools that matched a reader to lenders, gave an approval verdict, scored lenders' treatment of borrowers,
or forecast what named lenders would do. Found 2026-11-28 by the recorded errors watch and an outside review of its
first run. Each page becomes a notice saying what it was and why it was withdrawn; links that sent readers to these
tools are pointed at the Denial Map. Idempotent; reports what it changed.

    python3 scripts/retire_lender_matching_tools.py [--check]
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP = "/fha-loan-denied-now-what.html"
WHY_MATCH = "Matching one reader to lenders is a lender recommendation, which this site does not make: the federal record describes each lender's applicant pool, not how it would decide one file."
WHY_VERDICT = "An approval verdict for one person is an individual approval prediction, which this site does not make."
TOOLS = {
    "two-doors.html": ("Two Doors", "This tool took a reader's profile and showed two named lenders as that reader's &ldquo;doors&rdquo;, with a denial rate &ldquo;for profiles like yours&rdquo;. " + WHY_MATCH),
    "test-your-lender.html": ("Test Your Lender", "This tool took a reader's lender and profile and reported how that lender &ldquo;treats borrowers like you&rdquo;. " + WHY_MATCH),
    "second-door.html": ("The Second Door", "This tool took the lender that denied a reader and showed &ldquo;which lender historically approves profiles like yours&rdquo;. " + WHY_MATCH),
    "people-like-you.html": ("People Like You", "This tool, held back from publication, listed lenders with denial rates for a reader's kind of file. " + WHY_MATCH),
    "fingerprint.html": ("Lender Fit Fingerprint", "This tool took a reader's profile and gave a &ldquo;lender fit&rdquo; code and an &ldquo;approval fit&rdquo; chart. " + WHY_MATCH),
    "lender-personality.html": ("Lender Personality Test", "This page matched a reader's answers to a lender &ldquo;archetype&rdquo;. " + WHY_MATCH),
    "lender-similarity.html": ("Lender Similarity Engine", "This page grouped lenders by &ldquo;decision DNA&rdquo; and told a reader denied by one lender which others not to apply to. " + WHY_MATCH),
    "mortgage-approval-window.html": ("Mortgage Approval Window", "This tool took a reader's numbers and said at what rate they could &ldquo;actually qualify&rdquo;. " + WHY_VERDICT),
    "physician-loan-calculator.html": ("Physician Loan Calculator", "This calculator returned an approval verdict and a percentage (&ldquo;Good Approval Odds&rdquo;, 70) from a reader's numbers. " + WHY_VERDICT),
    "self-employed-mortgage-qualification.html": ("Self-Employed Mortgage Qualification Simulator", "This simulator returned an approval percentage from a reader's income and write-offs. " + WHY_VERDICT),
    "ssdi-mortgage-qualification.html": ("SSDI Mortgage Qualification Simulator", "This simulator returned an approval percentage from a reader's disability income. " + WHY_VERDICT),
    "intelligence-dashboard.html": ("Mortgage Intelligence Dashboard", "This page, offered to brokers in May 2026, showed composite scores including &ldquo;Income Type Approval Odds&rdquo;, with no dated source or receipt for its figures."),
    "frc-score.html": ("FRC Lender Score", "This page gave each lender one score said to measure &ldquo;how lenders treat borrowers&rdquo;. Scoring lenders' quality is a ranking this site does not make; a denial rate describes an applicant pool, not treatment."),
    "ofi-lender-forecast.html": ("OFI Lender Behavior Forecast", "This page published 60&ndash;90 day predictions of what named lenders would do. This site does not forecast the behaviour of named lenders; its figures are historical aggregates."),
    "mortgage-denial-help.html": ("Why Was My Mortgage Denied?", "This tool took a reader's answers, named the factor it guessed had caused the denial, and told the reader to find &ldquo;lenders whose historical overlay patterns accept this combination&rdquo;. A guess about one denial and a pointer to lenders are an individual prediction and a lender recommendation, which this site does not make."),
    "fha-vs-conventional-vs-va-calculator.html": ("FHA vs Conventional vs VA Calculator", "This calculator compared payments, which is arithmetic, but also declared a winning loan &ldquo;for you&rdquo; and showed a percentage for each loan type, labelled &ldquo;Observed Denial Rates&rdquo;, that was not observed: it was computed in the page from the reader&rsquo;s debt-to-income ratio and credit score by a formula with no source. A made-up likelihood presented as an observed rate is the error this site exists to catch, and an approval likelihood for one person is a prediction it does not make."),
    "ofi-futures.html": ("OFI Futures", "This page invited predictions on where named lenders' denial patterns would move next quarter. This site does not forecast the behaviour of named lenders."),
}
LINKS = [
    (re.compile(r'<a href="/two-doors\.html">Find your two doors →</a>'), f'<a href="{MAP}">The Denial Map →</a>'),
    (re.compile(r'<a href="/second-door\.html"([^>]*)>Find your second door →</a>'), rf'<a href="{MAP}"\1>The Denial Map →</a>'),
    (re.compile(r'>Full routing →</a>'), '>Evidence Navigator →</a>'),
    (re.compile(r"See which lenders approve files like yours\."), "What the record can and cannot say about lenders."),
    (re.compile(r'<div class="cta-box">\s*<div[^>]*>Find Your Best Lender Match</div>\s*<p[^>]*>Run a Pre-Flight Check to see which lenders historically approve your specific profile type\.</p>'),
     '<div class="cta-box">\n    <div style="font-family:\'Fraunces\',serif;font-size:20px;font-weight:900;margin-bottom:8px;">What the record can and cannot say</div>\n    <p style="color:rgba(255,255,255,0.55);font-size:13px;margin-bottom:16px;">A lender&rsquo;s rate describes its applicant pool, not how it would decide one file.</p>'),
    (re.compile(r'\s*<a href="/pre-flight\.html\?[^"]*"[^>]*>✈️ Pre-Flight Check</a>'), ""),
]


def notice(fname, title, what):
    src = open(os.path.join(ROOT, "bank-rejection-engine.html"), encoding="utf-8").read()
    nav = re.search(r'<nav data-frc-nav="1".*?</nav>', src, re.S).group(0)
    style = re.search(r"<style>.*?</style>", src, re.S).group(0)
    fonts = re.search(r'<link href="https://fonts.googleapis.com[^>]+>', src).group(0)
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Retired | FinanceRateCalc</title>
<meta name="description" content="Retired page. {re.sub(r'&[a-z]+;', '', what)[:150]}"><meta name="robots" content="noindex,follow">
<link rel="canonical" href="https://financeratecalc.com/{fname}">
{fonts}
{style}</head>
<body>
{nav}
<div class="wrap"><h1>This page has been retired.</h1>
<!-- rulecheck:ignore: describes the retired page --><div class="box">{what} The page was withdrawn on 28 November 2026 and now records that.</div>
<p>What this site does instead: it shows what the record supports and where the evidence ends &mdash; <a href="{MAP}">The Denial Map</a> &middot; <a href="/evidence-navigator.html">Evidence Navigator</a> &middot; <a href="/fha-denial-rates-top-100.html">FHA denial rates by lender, with receipts</a> &middot; <a href="/corrections.html#2026-11-28-lender-matching-tools">Corrections log</a>.</p>
<p style="font-size:13px;color:#8a8678">The data behind everything remains free.</p>
</div>
</body></html>
'''


def main():
    check = "--check" in sys.argv
    changed = []
    for fname, (title, what) in TOOLS.items():
        p = os.path.join(ROOT, fname)
        if not os.path.exists(p):
            continue
        new = notice(fname, title, what)
        if open(p, encoding="utf-8").read() != new:
            changed.append(fname)
            if not check:
                open(p, "w", encoding="utf-8").write(new)
    for f in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True):
        rel = os.path.relpath(f, ROOT)
        if rel.startswith(("scripts/", "eval/", "readers/")) or rel in TOOLS or rel in ("corrections.html", "watch.html"):
            continue
        s = open(f, encoding="utf-8").read(); o = s
        for rx, rep in LINKS:
            s = rx.sub(rep, s)
        if s != o:
            changed.append(rel)
            if not check:
                open(f, "w", encoding="utf-8").write(s)
    print(f"pages rewritten: {len(changed)}")
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
