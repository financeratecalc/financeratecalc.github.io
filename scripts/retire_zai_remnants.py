#!/usr/bin/env python3
"""Remove the last traces of Zai (retired 4 September 2026) from every page.

terms.html, refund.html, zai-for-brokers.html and verdict-casefile.html said the product was
withdrawn; 1,753 template pages still invited readers to "Ask Zai" whether they would be
approved or which lender accepts their profile. Three outside readers found the contradiction on
2026-10-20. Every block is replaced with a link to what the site actually offers after a denial
(the Denial Map and the Evidence Navigator), never with a prediction or a lender suggestion.

Idempotent. Pages that document the retirement (terms, refund, corrections, changelog, journey,
case files, the retired product pages) are left alone.
"""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEEP = {"terms.html", "refund.html", "corrections.html", "changelog.html", "journey.html", "zai-for-brokers.html",
        "verdict-casefile.html", "privacy.html"}
MAP = "/fha-loan-denied-now-what.html"
NAV = "/evidence-navigator.html"

DENIED_BLOCK = (
    '<!-- DENIED NEXT STEPS -->\n'
    '<div style="background:linear-gradient(135deg,rgba(200,164,74,0.08),rgba(107,191,146,0.05));border:1px solid rgba(200,164,74,0.2);border-radius:12px;padding:22px 24px;margin:28px 0;">\n'
    '  <div style="font-size:10px;letter-spacing:0.14em;text-transform:uppercase;color:rgba(200,164,74,0.7);font-weight:700;margin-bottom:8px;">After a denial — no prediction, no lender pick</div>\n'
    '  <div style="font-size:18px;font-weight:700;color:#fff;margin-bottom:8px;">Denied? Four steps, from the federal record.</div>\n'
    '  <p style="font-size:13px;color:rgba(255,255,255,0.55);line-height:1.7;margin-bottom:16px;">What the denial code means, what to ask the lender in writing, and how denial rates differ across lenders for the same program. Historical aggregates; nobody here can tell you your odds.</p>\n'
    '  <div style="display:flex;gap:10px;flex-wrap:wrap;">\n'
    f'    <a href="{MAP}" style="background:#c8a44a;color:#000;padding:11px 20px;border-radius:7px;font-weight:700;font-size:13px;text-decoration:none;display:inline-block;">The Denial Map →</a>\n'
    f'    <a href="{NAV}" style="background:rgba(255,255,255,0.06);color:rgba(255,255,255,0.7);padding:11px 20px;border-radius:7px;font-weight:600;font-size:13px;text-decoration:none;display:inline-block;border:1px solid rgba(255,255,255,0.1);">Evidence Navigator</a>\n'
    '  </div>\n</div>\n')

RULES = [
    # whole CTA widget -> Denial Map block
    (re.compile(r"<!-- ZAI CTA WIDGET -->\s*<div[^>]*>.*?</div>\s*</div>\s*", re.S), DENIED_BLOCK),
    # international note: drop the Zai sentence
    (re.compile(r"\s*Ask Zai which lenders accept international profiles — <a [^>]*>free analysis →</a>"), ""),
    # tile card in link grids
    (re.compile(r'<a href="/frc-banker-ai\.html"([^>]*)>\s*<div[^>]*>🏦 Ask Zai</div>\s*<div[^>]*>Free AI Banker</div>\s*<div([^>]*)>banking professional, free</div>\s*</a>'),
     rf'<a href="{MAP}"\1><div style="font-size:10px;color:rgba(200,164,74,0.7);font-weight:700;margin-bottom:4px;">📍 Denied?</div><div style="font-size:13px;font-weight:700;color:#fff;">The Denial Map</div><div\2>four steps, no prediction</div></a>'),
    # .cta sentences
    (re.compile(r"Ask Zai with your actual debts, (credit )?score,? and down payment for a precise answer\."), "The Denial Map: what a denial code means and what to ask a lender in writing. No prediction."),
    (re.compile(r"Ask Zai with your actual salary, overtime, and credit score\."), "Affordability is arithmetic; approval is a lender decision. The Denial Map shows what the record supports."),
    (re.compile(r"Ask Zai — free AI trained on 23 years of banking\. No SSN required\."), "The Denial Map: four steps after a denial, from the federal record. No prediction, no lender pick."),
    (re.compile(r"Ask Zai to analyze your situ[^<]*"), "Lender choice is the half of the answer this site measures; it never predicts a single file."),
    # buttons
    (re.compile(r'<a href="/frc-banker-ai\.html"([^>]*)>🏦 Ask Zai Free →</a>'), rf'<a href="{MAP}"\1>The Denial Map →</a>'),
    (re.compile(r'\s*<a href="/frc-banker-ai\.html"[^>]*>🏦 Ask Zai About This Market</a>'), ""),
    (re.compile(r'\s*<a href="/frc-banker-ai\.html"[^>]*>🏦 Ask Zai About [^<]*</a>'), ""),
    (re.compile(r'<a href="/frc-banker-ai\.html"([^>]*)>🏦 Ask Zai[^<]*</a>'), rf'<a href="{MAP}"\1>The Denial Map →</a>'),
    (re.compile(r'<a href="/frc-banker-ai\.html"([^>]*)>Talk to Zai — Free →</a>'), rf'<a href="{MAP}"\1>The Denial Map →</a>'),
    # link text
    (re.compile(r'<a href="/evidence-navigator\.html">Zai — File Analysis</a>'), '<a href="/evidence-navigator.html">Evidence Navigator</a>'),
    (re.compile(r"Free Tool · Zai AI"), "Free Tool"),
    (re.compile(r"Zai Routing"), "Evidence Navigator"),
    # any other link to the retired page
    (re.compile(r'href="/frc-banker-ai\.html"'), f'href="{MAP}"'),
    # second pass (2026-10-20, after the first sweep): link text and headings that survived
    (re.compile(r">🏦 Ask Zai Free →</a>"), ">The Denial Map →</a>"),
    (re.compile(r">🏦 Ask Zai — Free AI Banker</a>"), ">The Denial Map →</a>"),
    (re.compile(r">🏦 Ask Zai[^<]*</a>"), ">The Denial Map →</a>"),
    (re.compile(r">💬 Ask Zai →</a>"), ">The Denial Map →</a>"),
    (re.compile(r">Ask Zai →</a>"), ">The Denial Map →</a>"),
    (re.compile(r">(Route with Zai — free|Route Your File with Zai|Analyze a file with Zai|Try Zai routing|🔍 Decode with Zai) →</a>"), ">Evidence Navigator →</a>"),
    (re.compile(r"<h3>Ask Zai Your Specific Question</h3>\s*<p>Free AI trained on 23 years of banking\. No SSN, no sign-up(, no affiliate pressure)?\.</p>"),
     "<h3>After a denial</h3>\n    <p>Four steps from the federal record: the code, the written questions, the lender spread. No prediction, no lender pick.</p>"),
    (re.compile(r"Ask Zai with your income, credit score, and savings — get the optimal down payment for your situation\."), "Down payment is arithmetic; approval is a lender decision. The Denial Map shows what the record supports."),
    (re.compile(r"Ask Zai with your income and down payment — get a personalized city recommendation\."), "The figures are market averages; this site does not recommend a city or a lender for one file."),
    (re.compile(r"Ask Zai to run the affordability math for any company and city\."), "The affordability math above is arithmetic on public salary and price data."),
    (re.compile(r"Ask Zai — free AI banker trained on 23 years of real lending experience\. No[^<]*"), "The Denial Map: four steps after a denial, from the federal record."),
    (re.compile(r"Built Zai — a free AI mortgage advisor trained on real bank logic(, not affiliated with any lender)?\."), "Builds the lender-level FHA denial tables from the public HMDA record."),
    (re.compile(r"🔍 Decode My Denial — Zai Will Explain Everything"), "🔍 Decode My Denial"),
    (re.compile(r"Zai maps your full decision surface\."), "The conditional door map shows the measured surface; it predicts nothing for one file."),
    (re.compile(r"(💡 Zai\\?'s Insider Note|💡 Zai's Insight|✦ Zai\\?'s Note)"), "Note from the record"),
    (re.compile(r"Zai for Brokers — Unlimited File Analysiss?"), "Retired: Zai for Brokers (withdrawn 4 September 2026)"),
    (re.compile(r"Zai Lender Comparison"), "Lender comparison (historical aggregates)"),
]


def main():
    changed = 0
    for f in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True):
        rel = os.path.relpath(f, ROOT)
        if rel in KEEP or rel.startswith(("case-files/", "eval/", "fixtures/", "examples/")) or rel == "frc-banker-ai.html" or rel == "verdict.html" or rel == "partners.html":
            continue
        s = open(f, encoding="utf-8", errors="ignore").read()
        if "Zai" not in s and "frc-banker-ai" not in s:
            continue
        t = s
        for rx, rep in RULES:
            t = rx.sub(rep, t)
        if t != s:
            open(f, "w", encoding="utf-8").write(t); changed += 1
    print(f"pages rewritten: {changed}")
    left = [os.path.relpath(f, ROOT) for f in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True)
            if os.path.relpath(f, ROOT) not in KEEP and not os.path.relpath(f, ROOT).startswith(("case-files/", "eval/"))
            and "Zai" in open(f, encoding="utf-8", errors="ignore").read()]
    print(f"pages still mentioning Zai: {len(left)}")
    for p in left[:40]:
        print("  ", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
