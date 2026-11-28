#!/usr/bin/env python3
"""Remove wording that offers a reader their approval odds or a lender fit, found by the recorded errors watch's first
run (2026-11-27) and an outside review of its results (2026-11-28). Idempotent; reports what it changed.

- the "Wondering If You'll Qualify? / Run a Pre-Flight Check — See Your Approval Odds" box and the "Are You a Mortgage
  Broker? / Run a Pre-Flight Check on your files" box: leftovers of withdrawn products whose links were already removed
- "See if you qualify for a <city> home" above a button that only calculates a payment
- named sentences on the lender, metro and press pages

    python3 scripts/retire_approval_odds_wording.py [--check]
"""
import glob, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOX = re.compile(r'\n?<div style="background:linear-gradient\(135deg,[^"]*"[^>]*>\s*<div>\s*<div[^>]*>(?:Are You a Mortgage Broker\?|Wondering If You(?:\'|&#39;|&rsquo;|’)ll Qualify\?|Ready to Check Your File\?)</div>\s*<div[^>]*>[^<]*Pre-Flight Check[^<]*</div>\s*<div[^>]*>[^<]*</div>\s*</div>\s*</div>')
FIXED = [
    (re.compile(r"See if you qualify for an? ([^<]{1,40}) home"), r"Work out the monthly payment for a \1 home"),
    (re.compile(r"Calculate your DTI ratio instantly\. See if you qualify for conventional, FHA, or VA loans\."), "Calculate your DTI ratio and compare it with the limits each program publishes for conventional, FHA and VA loans."),
    (re.compile(r"Calculate your new mortgage payment and see if you qualify before you apply\."), "Calculate your new mortgage payment before you apply."),
    (re.compile(r"The practical use is routing: knowing which doors historically clear files like yours\."), "What the table supports is a question to ask: a lender&rsquo;s rate describes its applicant pool in 2025, not how it would decide one file."),
    (re.compile(r"Which of these 11 fits YOUR file\? Free routing, 60 seconds →"), "What a denial letter&rsquo;s reason means, and what the record can and cannot say about lenders →"),
    (re.compile(r"Which of these 11 fits YOUR file\? Free routing, 60 seconds (?:→|&rarr;)"), "What the record can and cannot say about lenders &rarr;"),
    (re.compile(r"&ldquo;Which door you knock on moves your odds more than any single thing in your file that the public record can see\.&rdquo;"), "&ldquo;A lender&rsquo;s denial rate describes its applicant pool, not any one applicant.&rdquo;"),
    (re.compile(r"The lender choice moves your odds more than the city does\."), "That gap inside one metro is wider than the range across all 319 metros."),
    (re.compile(r"“Which door you knock on moves your odds more than any single thing in your file that the public record can see\.”"), "“A lender&rsquo;s denial rate describes its applicant pool, not any one applicant.”"),
]
def main():
    check = "--check" in sys.argv; changed = {}
    for f in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True):
        rel = os.path.relpath(f, ROOT)
        if rel.startswith(("scripts/", "eval/", "readers/", "node_modules/")) or rel in ("corrections.html", "watch.html"):
            continue
        s = open(f, encoding="utf-8").read(); o = s
        s, n = BOX.subn("", s)
        for rx, rep in FIXED:
            s, m = rx.subn(rep, s); n += m
        if s != o:
            changed[rel] = n
            if not check: open(f, "w", encoding="utf-8").write(s)
    print(f"pages rewritten: {len(changed)}, edits: {sum(changed.values())}")
    return 1 if (check and changed) else 0
if __name__ == "__main__":
    sys.exit(main())
