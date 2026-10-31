#!/usr/bin/env python3
"""Retire the remaining individual-prediction tools and the phrasings that imply one application at two lenders.

Found 2026-10-31: bank-rejection-engine.html ("You Will Be Approved" / "Most Banks Will Deny You"), mortgage-fate.html
("find out if a bank would approve you") and mortgage-navigator.html ("which lender type fits you") were still live,
noindex but linked from ~1,600 calculator pages through a "Will a Bank Approve You?" call-to-action and a footer link.
This site does not make individual approval predictions or lender recommendations; the pages become retirement
notices and the links go. Idempotent; CI runs it and fails if it changes anything.

    python3 scripts/retire_prediction_tools.py
"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RETIRED = {
    "bank-rejection-engine.html": ("Why Did My Mortgage Get Denied? — Retired", "This page scored a visitor's numbers against five lender types and answered \"You will be approved\" or \"Most banks will deny you\"."),
    "mortgage-fate.html": ("What's Your Mortgage Fate? — Retired", "This page took seven answers and said whether a bank would approve, deny or redirect the visitor."),
    "mortgage-navigator.html": ("Mortgage Navigator — Retired", "This page took a ZIP code and a financial profile and named which lender type fits the visitor."),
}
NAV = ('<nav data-frc-nav="1" aria-label="Site" style="font-family:system-ui,sans-serif;font-size:12.5px;padding:8px 16px;background:#0b0d12;border-bottom:1px solid rgba(255,255,255,.08);display:flex;gap:14px;flex-wrap:wrap;align-items:center">'
       '<a href="/" style="color:#C8A84B;font-weight:700;text-decoration:none">FinanceRateCalc</a><a href="/fha-denial-rates-top-100.html" style="color:rgba(255,255,255,.7);text-decoration:none">Lenders</a>'
       '<a href="/fha-denial-rates-by-state.html" style="color:rgba(255,255,255,.7);text-decoration:none">States</a><a href="/metro-gaps.html" style="color:rgba(255,255,255,.7);text-decoration:none">Metros</a>'
       '<a href="/check-answer.html" style="color:rgba(255,255,255,.7);text-decoration:none">Check an answer</a><a href="/corrections.html" style="color:rgba(255,255,255,.7);text-decoration:none">Corrections</a>'
       '<a href="/about.html" style="color:rgba(255,255,255,.7);text-decoration:none">About</a></nav>')


def notice(fname, title, what):
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | FinanceRateCalc</title>
<meta name="description" content="Retired page. This tool gave visitors a personal approval verdict, which this site does not make; the page records the retirement and points to the Denial Map."><meta name="robots" content="noindex,follow">
<link rel="canonical" href="https://financeratecalc.com/{fname}">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,900&family=DM+Sans:wght@400;600&display=swap" rel="stylesheet">
<style>body{{background:#08090c;color:#e8e4da;font-family:'DM Sans',sans-serif;margin:0;line-height:1.7}}.wrap{{max-width:640px;margin:0 auto;padding:70px 20px}}h1{{font-family:'Fraunces',Georgia,serif;font-size:28px;color:#f5f2ea}}a{{color:#C8A84B}}.box{{border:1px solid #23262e;border-radius:10px;padding:18px 20px;background:#0d0f14;margin:18px 0;font-size:15px}}</style></head>
<body>
{NAV}
<div class="wrap"><h1>This tool has been retired.</h1>
<!-- rulecheck:ignore: quotes the retired tool --><div class="box">{what} That is an individual approval prediction, which this site does not make: the federal record is a historical aggregate and says nothing about one file. The tool was withdrawn on 31 October 2026 and the page now records that.</div>
<p>What this site does instead: it shows what the record supports and where the evidence ends — <a href="/fha-loan-denied-now-what.html">The Denial Map</a> · <a href="/denial-code-lookup.html">Denial code lookup</a> · <a href="/check-answer.html">Check an answer</a> · <a href="/metro-gaps.html">184 metro lender gaps</a> · <a href="/corrections.html">Corrections log</a>.</p>
<p style="font-size:13px;color:#8a8678">Retired products are listed in the <a href="/terms.html" style="color:#8a8678">terms</a>. The data behind everything remains free.</p>
</div>
</body></html>
"""


CTA_RX = re.compile(r'\s*<div class="cta-box"[^>]*>\s*<div class="cta-title">Will a Bank Approve You\?</div>.*?</div>\s*</div>', re.S)
FOOTER_RX = re.compile(r'\s*<a href="/?bank-rejection-engine\.html"[^>]*>[^<]*</a>')
LINK_RX = re.compile(r'href="/?(mortgage-fate|mortgage-navigator)\.html"')
# Second-generation CTAs on the salary, why-did and faq pages: the sentence promises a personal verdict; the link now
# goes to the Denial Map and the sentence states what the record can show.
CTA_TEXT = [
    ("See Your Exact Approval Odds", "See the Denial Map"),
    ("Enter your full profile — income, debts, credit score — and see how 5 lender types would score you.", "Observed FHA denial rates by lender, state and metro from the complete 2025 federal record — historical aggregates, not a verdict on your file."),
    ("See Exactly Why You'd Be Denied", "See the Denial Map"),
    ("Enter your profile — see how all 5 lender types score you, and get a personalized action plan.", "Observed FHA denial rates by lender, state and metro from the complete 2025 federal record — historical aggregates, not a verdict on your file."),
    ("Check your loan eligibility", "See the Denial Map"),
    ("See how your profile looks to a lender before you apply.", "Observed FHA denial rates by lender, state and metro, from the complete 2025 federal record."),
    ("Check My Odds →", "Open the Denial Map →"), ("Run Simulator →", "Open the Denial Map →"), ("Run My Application →", "Open the Denial Map →"),
    ("Bank Rejection Engine →", "The Denial Map →"), ("Bank Rejection Engine", "The Denial Map"),
    ("See Which Lender Fits Your Profile →", "See observed denial rates by lender →"),
]
WORDING = [
    ("fha-loan-denied-now-what.html", "The same borrower faces different odds in different climates.", "Observed denial rates differ from state to state."),
    ("state-of-underwriting-2026.html", "meaning the same borrower faces radically different approval landscapes depending solely on", "meaning observed approval landscapes differ widely by"),
    ("fha-penalty-by-lender.html", "Why the Same Borrower Gets Denied More on FHA Than Conventional", "Why FHA Applications Are Denied More Often Than Conventional"),
    ("frc-certified.html", "explain why the same borrower gets different outcomes at different lenders", "explain why observed outcomes differ between lenders"),
]


def main():
    changed = 0
    for fname, (title, what) in RETIRED.items():
        p = os.path.join(ROOT, fname)
        html = notice(fname, title, what)
        if not os.path.exists(p) or open(p, encoding="utf-8").read() != html:
            open(p, "w", encoding="utf-8").write(html); changed += 1
    for fname, old, new in WORDING:
        p = os.path.join(ROOT, fname)
        if os.path.exists(p):
            s = open(p, encoding="utf-8").read()
            if old in s:
                open(p, "w", encoding="utf-8").write(s.replace(old, new)); changed += 1
    for p in glob.glob(os.path.join(ROOT, "*.html")):
        if os.path.basename(p) in RETIRED or os.path.basename(p) in ("terms.html", "changelog.html", "journey.html", "corrections.html"):
            continue
        s = open(p, encoding="utf-8").read()
        n = CTA_RX.sub("", s)
        n = FOOTER_RX.sub("", n)
        n = LINK_RX.sub('href="/fha-loan-denied-now-what.html"', n)
        if "bank-rejection-engine.html" in n:
            for old, new in CTA_TEXT:
                n = n.replace(old, new)
            n = n.replace('href="bank-rejection-engine.html"', 'href="/fha-loan-denied-now-what.html"').replace('href="/bank-rejection-engine.html"', 'href="/fha-loan-denied-now-what.html"')
            n = n.replace("link: 'bank-rejection-engine.html'", "link: 'fha-loan-denied-now-what.html'").replace('url=/bank-rejection-engine.html', 'url=/fha-loan-denied-now-what.html')
        if n != s:
            open(p, "w", encoding="utf-8").write(n); changed += 1
    print(f"pages rewritten: {changed}")


if __name__ == "__main__":
    main()
