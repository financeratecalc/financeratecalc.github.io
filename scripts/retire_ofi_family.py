#!/usr/bin/env python3
"""Retire the Overlay Friction Index (OFI) family, 2026-11-28.

The OFI was a 0-100 "overlay strictness" score published quarterly from May 2026, with a dashboard, a state map,
forecasts, signals, an annual report, an API page and twenty data files. Its historical values, which its forecasting
model was trained on, are typed into the model's code with no source (.github/scripts/ofi_macro_model.py,
QUARTERLY_DATA); its methodology page said it was recalculated from HMDA releases, which are annual and cannot give
quarterly values, and cited "3.0M+ loan-level FHA records, 2025" where the 2025 record has 1,187,606 decisioned FHA
applications. A figure that cannot be traced to a source is not published on this site, so every page becomes a
notice and every data file a retirement record. Idempotent; reports what it changed.

    python3 scripts/retire_ofi_family.py [--check]
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from legacy_research_pages import shell  # noqa: E402

ANCHOR = "/corrections.html#2026-11-28-ofi-family"
WHY = ("The index&rsquo;s historical values, which its forecasting model was trained on, are typed into the model&rsquo;s code with no source; "
       "its methodology said it was recalculated from HMDA releases, which are annual and cannot give quarterly values. "
       "A figure that cannot be traced to a source is not published on this site.")
PAGES = {
    "overlay-friction-index.html": ("Overlay Friction Index (OFI)", "This page defined the OFI, a quarterly 0&ndash;100 score of how much lenders add to agency rules, and gave its current value (47 in Q2 2026)."),
    "ofi.html": ("OFI", "This page presented the OFI as a mortgage market signal."),
    "ofi-methodology.html": ("OFI methodology", "This page, shown to search engines, described how the OFI was made, citing &ldquo;3.0M+ loan-level FHA records, 2025&rdquo; (the 2025 record has 1,187,606 decisioned FHA applications) and quarterly recalculation from HMDA releases."),
    "ofi-dashboard.html": ("OFI dashboard", "This page charted the OFI&rsquo;s history and components."),
    "ofi-evidence.html": ("OFI evidence base", "This page listed the evidence said to support the OFI."),
    "ofi-state-map.html": ("OFI state map", "This page gave an OFI score to every state."),
    "ofi-validation.html": ("OFI validation", "This page presented what AI systems said about the OFI as &ldquo;independent validation&rdquo;. An AI system restating a site&rsquo;s own description is not validation."),
    "ofi-weekly.html": ("OFI Weekly Briefing", "This page, shown to search engines, offered a weekly e-mail briefing built on the OFI."),
    "ofi-badge.html": ("OFI badge", "This page offered an embeddable badge showing the current OFI."),
    "ofi-for-borrowers.html": ("OFI for borrowers", "This page told borrowers how to use the OFI in their own application."),
    "ofi-for-lenders.html": ("OFI for lenders", "This page offered the OFI to lenders for credit policy. This site does not sell to lenders."),
    "ofi-international-buyers.html": ("OFI for international buyers", "This page offered the OFI to buyers from abroad as a guide to US approval conditions."),
    "q2-2026-overlay-climate-report.html": ("Q2 2026 Overlay Climate Report", "This report described lender overlay conditions in Q2 2026 by kind of lender, built on the OFI."),
    "state-of-underwriting-2026.html": ("State of Underwriting 2026", "This annual report, shown to search engines, summarised the OFI cycle, &ldquo;SSDI acceptance&rdquo; rates and a 64-point spread between kinds of lender, none of them with a source a reader could check."),
    "state2026.html": ("State of Underwriting 2026: key findings", "This page listed the findings of the 2026 annual report, built on the OFI."),
    "frc-signals.html": ("FRC Signals", "This page issued named &ldquo;signals&rdquo; when the OFI moved, meant to change borrower strategy."),
    "approval-window.html": ("Mortgage Approval Window", "This page told brokers whether conditions were &ldquo;opening or narrowing&rdquo; for their borrowers, that is, when to apply. Advice on when one borrower should apply is a prediction this site does not make."),
    "live-underwriting-radar.html": ("Live Underwriting Radar", "This page showed &ldquo;real-time&rdquo; denial intelligence from complaints classified by an AI model into an OFI update."),
    "mortgage-decision-cycle.html": ("Mortgage Decision Macro-Cycle", "This page placed the market in an underwriting &ldquo;state&rdquo; from the OFI, with an embeddable badge."),
    "mortgage-decision-glossary.html": ("Mortgage Decision Glossary", "This page defined the OFI and related terms as &ldquo;canonical&rdquo; vocabulary."),
    "mortgage-decision-report.html": ("Mortgage Decision Report", "This page promised a reader &ldquo;why you were denied &mdash; and who will say yes&rdquo; and their &ldquo;highest historical fit&rdquo; among lenders. That is an individual prediction and a lender recommendation, which this site does not make."),
    "lender-intelligence.html": ("Lender Behavior Intelligence", "This page scored named lenders on &ldquo;cycle sensitivity&rdquo; with OFI values (Freedom Mortgage &ldquo;OFI 79.7&rdquo;)."),
    "lender-taxonomy.html": ("FHA Lender Taxonomy", "This page sorted named lenders into four behavioural &ldquo;types&rdquo; for borrowers to choose between."),
    "lender-overlay-database.html": ("Lender Overlay Database", "This page listed named lenders&rsquo; overlay rules from a hand-made file whose own notes give its sources as search-result snippets and estimates (&ldquo;0.5 = estimated&rdquo;), not the lenders&rsquo; documents."),
    "lender-overlay-explained.html": ("Lender Overlay Explained", "This page told a denied reader that their denial was &ldquo;likely&rdquo; an overlay and that another lender &ldquo;may approve you the same day&rdquo;, and offered to identify &ldquo;the specific overlay that triggered&rdquo; a denial."),
    "fha-state-map.html": ("FHA approval climate by state", "This map coloured states by OFI score (&ldquo;lower OFI = easier approval environment&rdquo;). Receipted state denial rates are at <a href=\"/fha-denial-rates-by-state.html\">FHA denial rates by state</a>."),
    "frc-research.html": ("FRC Research", "This page, shown to search engines, presented the OFI, an &ldquo;SSDI acceptance rate&rdquo; and other indices as live research &ldquo;based on agency guideline comparison and anonymous denial data submissions&rdquo;, and told professionals to use them to advise clients on timing and lender selection."),
    "appeal-letter.html": ("Reconsideration letter generator", "This page, shown to search engines, wrote a reconsideration letter to a reader&rsquo;s lender that told the lender its denial &ldquo;appears to reflect your institution&rsquo;s internal overlay policy&rdquo;, quoting a credit-score &ldquo;overlay&rdquo; for each named lender (for example 640 for Rocket Mortgage, 680 for Wells Fargo) that had no source, and 2024 denial rates labelled &ldquo;OFI analysis&rdquo;; it then suggested &ldquo;wholesale channel alternatives&rdquo;. An unsourced claim about a named lender&rsquo;s policy, a guess about why one application was denied and a pointer to other channels are things this site does not publish. What to ask a lender in writing after a denial is in <a href=\"/fha-loan-denied-now-what.html\">The Denial Map</a>."),
    "api.html": ("FRC API", "This page, shown to search engines, documented the OFI data files as a public API. The site&rsquo;s figures with receipts are served by <a href=\"/mcp-server.html\">its tool server</a> and listed in the <a href=\"/data-catalog.html\">data catalog</a>."),
}
DATA = sorted(set(glob.glob(os.path.join(ROOT, "ofi-*.json"))) - {os.path.join(ROOT, "ofi-lender-predictions.json")}) + [
    os.path.join(ROOT, f) for f in ("frc-ofi-data.json", "overlay-climate.json", "overlay-intelligence.json", "lender-overlay-database-2026.json",
                                    "live-intelligence.json") if os.path.exists(os.path.join(ROOT, f))]


SUB = [
    # the "current indicators" strip: OFI value, an OFI "signal", overlay climate and an unsourced "SSDI acceptance" rate
    (re.compile(r'\n  <!-- FRC VOCABULARY \+ CITATION STANDARD -->\n  <div[^>]*>.*?Updated quarterly · CC BY 4\.0\n    </div>\n  </div>\n', re.S), "\n"),
    (re.compile(r"analyzes lender overlays and agency guidelines to explain loan denials and predict approval paths"),
     "explains what the public federal record says about loan denials, and where it stops"),
    (re.compile(r"Full transparency on how FinanceRateCalc builds its mortgage intelligence signals\. Every number has a source\. Every model has a formula\."),
     "How every figure on this site is made, what it rests on, and where it stops."),
    (re.compile(r' ?<a href="/ofi\.html"[^>]*>OFI</a>'), ""),
]


def notice(fname, title, what):
    plain = re.sub(r"<[^>]+>|&[a-z]+;", "", what)[:150].replace('"', "")
    body = f'''<h1>This page has been retired.</h1>
<!-- rulecheck:ignore: describes the retired page --><div class="box">{what} It was part of the Overlay Friction Index (OFI) family, published from May 2026. {WHY} The page was withdrawn on 28 November 2026 and now records that.</div>
<p>What this site does instead: it shows what the record supports and where the evidence ends &mdash; <a href="/fha-loan-denied-now-what.html">The Denial Map</a> &middot; <a href="/fha-denial-rates-top-100.html">FHA denial rates by lender, with receipts</a> &middot; <a href="/official-figures.html">Official figures</a> &middot; <a href="{ANCHOR}">Corrections log</a>.</p>
<p style="font-size:13px;color:#8a8678">The data behind everything remains free.</p>'''
    return shell(f"{title} — Retired | FinanceRateCalc", f"Retired page. {plain}", body, fname=fname)


def record(path):
    return json.dumps({
        "retired": "2026-11-28",
        "what_this_was": "A data file of the Overlay Friction Index (OFI) family: a 0-100 lender overlay score, its forecasts, components or the data behind its pages.",
        "why": re.sub(r"&rsquo;", "'", WHY),
        "corrections": "https://financeratecalc.com" + ANCHOR,
        "previous_versions": "https://github.com/financeratecalc/financeratecalc.github.io/commits/main/" + os.path.basename(path),
    }, indent=1) + "\n"


def main():
    check = "--check" in sys.argv
    changed = []
    for fname, (title, what) in PAGES.items():
        p = os.path.join(ROOT, fname)
        if not os.path.exists(p):
            continue
        new = notice(fname, title, what)
        if open(p, encoding="utf-8").read() != new:
            changed.append(fname)
            if not check:
                open(p, "w", encoding="utf-8").write(new)
    for p in DATA:
        new = record(p)
        if open(p, encoding="utf-8").read() != new:
            changed.append(os.path.basename(p))
            if not check:
                open(p, "w", encoding="utf-8").write(new)
    for f in glob.glob(os.path.join(ROOT, "*.html")):
        rel = os.path.basename(f)
        if rel in PAGES or rel in ("corrections.html", "watch.html"):
            continue
        t = open(f, encoding="utf-8").read(); o = t
        for rx, rep in SUB:
            t = rx.sub(rep, t)
        if t != o:
            changed.append(rel)
            if not check:
                open(f, "w", encoding="utf-8").write(t)
    print(f"files rewritten: {len(changed)}")
    for c in changed:
        print("  ", c)
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
