#!/usr/bin/env python3
"""Regenerate the 'Why <lender> says no' paragraph and the reason-share basis sentence on every lender page from
api/lender/<slug>.json (share-of-denials-citing basis), and refresh the modified date.

    python3 scripts/build_lender_reason_sections.py [--check]

The lender pages were written in July on the superseded share-of-citations basis (corrections 2026-11-07 and
2026-11-09). Rates on these pages are already checked by check_page_values.py; this script brings the reason
section under the same rule: generated from the receipts' source files, never typed. --check exits 1 if any page
would change.
"""
import datetime as dt
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABEL = {"dti": "debt-to-income", "credit_history": "credit history", "collateral": "collateral", "insufficient_cash": "insufficient cash",
         "incomplete": "incomplete application", "unverifiable_info": "unverifiable information", "employment": "employment",
         "mortgage_insurance_denied": "mortgage insurance denied", "other": "other"}
OLD_LEGAL = re.compile(r"Reason shares over all cited reasons \(lenders &ge;500 apps &amp; &ge;100 denials\);")
NEW_LEGAL = "Reason shares = share of the lender&rsquo;s denials whose stated reasons (up to four) include the reason, each reason once per denial, for lenders with &ge;50 stated-reason denials; basis changed from share-of-citations on 2026-11-09 (corrections log);"
SAYS_NO = re.compile(r"(<h2>Why [^<]* says no</h2>)<p>.*?</p>", re.S)


def paragraph(L):
    sh = L.get("denial_reason_shares_pct")
    name = L["lender"]
    if not sh:
        return (f'<p>Fewer than 50 of {name}&rsquo;s 2025 FHA denials carried a stated reason, so no reason fingerprint is published for it. '
                f'Context: <a href="/fha-denial-reasons-by-lender.html" style="color:#C8A84B">the reason fingerprint</a>.</p>')
    top = sorted(sh.items(), key=lambda kv: -kv[1])[:3]
    parts = ", ".join(f"{LABEL.get(k, k)} ({v}%)" for k, v in top)
    return (f'<p>Most-cited reasons on {name}&rsquo;s denied FHA files in 2025: <b style="color:#fff">{parts}</b> '
            f'(share of denials citing each reason; a denial may carry up to four reasons, so shares need not sum to 100). '
            f'Reason codes record outcomes, not causes, and partly reflect applicant and channel mix &mdash; context: '
            f'<a href="/fha-denial-reasons-by-lender.html" style="color:#C8A84B">the reason fingerprint</a>.</p>')


def main():
    check = "--check" in sys.argv
    today = dt.date.today().isoformat()
    changed, missing = [], []
    for page in sorted(glob.glob(os.path.join(ROOT, "*-fha-denial-rate.html"))):
        slug = os.path.basename(page)[: -len("-fha-denial-rate.html")]
        api = os.path.join(ROOT, "api", "lender", slug + ".json")
        if not os.path.exists(api):
            missing.append(slug); continue
        L = json.load(open(api, encoding="utf-8"))
        s = open(page, encoding="utf-8").read()
        new = SAYS_NO.sub(lambda m: m.group(1) + paragraph(L), s, count=1) if SAYS_NO.search(s) else s
        new = OLD_LEGAL.sub(NEW_LEGAL, new)
        new = new.replace("Odds and price for all 60 largest doors:", "Rate and denial rate for the 60 largest lenders:")
        if new != s:
            new = re.sub(r'<meta property="article:modified_time" content="[^"]*">', f'<meta property="article:modified_time" content="{today}T00:00:00Z">', new, count=1)
            new = new.replace("Direct answer &middot; updated 2026-07-19", f"Direct answer &middot; reason section rebuilt from the receipts {today}")
            changed.append(slug)
            if not check:
                open(page, "w", encoding="utf-8").write(new)
    if check:
        print("lender reason sections:", "current" if not changed else f"STALE ({len(changed)}: {changed[:5]}…)")
        sys.exit(1 if changed else 0)
    print(f"rewrote reason sections on {len(changed)} lender pages; {len(missing)} pages without an api file skipped: {missing[:6]}")


if __name__ == "__main__":
    main()
