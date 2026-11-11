#!/usr/bin/env python3
"""revision-ledger.html: every official figure this site has seen change between two editions of the same report,
and how many were compared and found unchanged. Generated from data/official/*.json; --check exits 1 when stale.
Nothing is estimated: both numbers of every entry are printed by the publisher, in two documents whose hashes are kept.
The page says what was observed (the number differs; the later edition carries no revision mark for it) and nothing
about why."""
import glob
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "revision-ledger.html")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_official_page import shell  # noqa: E402  (same look as the other generated pages)

E = html.escape


def fmt(v):
    return f"{v:,}" if isinstance(v, (int, float)) else str(v)


def main():
    style, nav = shell()
    feed = json.load(open(os.path.join(ROOT, "data", "revisions.json"), encoding="utf-8"))
    per = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "official", "*.json"))):
        if os.path.basename(f) == "index.json":
            continue
        d = json.load(open(f, encoding="utf-8"))
        s = per.setdefault(d["source_id"], {"title": d["document"]["title"], "publisher": d["document"]["publisher"].split(",")[0], "editions": [], "compared": 0, "revised": 0})
        s["editions"].append(d["document"]["edition"])
        rv = d.get("prior_edition_check", {}).get("revisions", [])
        s["compared"] += len(rv); s["revised"] += sum(1 for r in rv if r.get("revised"))
    src_rows = "".join(f'<tr><td><b>{E(s["title"])}</b><br><span class="small">{E(s["publisher"])}</span></td><td class=n>{len(s["editions"])}</td>'
                       f'<td class=n>{s["compared"]}</td><td class=n><b>{s["revised"]}</b></td></tr>' for s in per.values())
    rows = ""
    for i in feed["items"]:
        rc = (f'<a href="{E(i["claim_url"].replace("https://financeratecalc.com", ""))}">{E(i["receipt_of_first_printing"])}</a>' if i.get("claim_url") else "no receipt issued for this month")
        rows += (f'<tr><td>{E(i["source"])}<br><span class="small">{E(i["description"])}</span></td><td>{E(i["period"])}</td>'
                 f'<td class=n>{fmt(i["first_printed"])}<br><span class="small">{E(i["first_printed_in"])}</span></td>'
                 f'<td class=n><b>{fmt(i["restated_as"])}</b><br><span class="small">{E(str(i["restated_in"]))}</span></td>'
                 f'<td class=n>{i["difference"]:+,}</td><td class="r small">{rc}</td></tr>')
    if not rows:
        rows = '<tr><td colspan="6">No changed figure found so far.</td></tr>'
    total_c = sum(s["compared"] for s in per.values()); total_r = sum(s["revised"] for s in per.values())
    page = (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>Revision ledger: official figures that changed between editions | FinanceRateCalc</title>\n'
        f'<meta name="description" content="A public record of figures that an official report printed in one edition and printed differently in the next, without a revision mark. {total_c} figures compared across editions so far, {total_r} changed. Both numbers of every entry are the publisher\'s own; nothing is estimated.">\n'
        '<link rel="canonical" href="https://financeratecalc.com/revision-ledger.html">\n'
        '<link rel="license" type="application/rsl+xml" href="https://financeratecalc.com/rsl.xml">\n'
        f'{style}\n<body>\n{nav}\n<div class="wrap">\n'
        '<div class="kicker">FinanceRateCalc &middot; revision ledger &middot; generated from the restated editions</div>\n'
        '<h1>Revision ledger: official figures that changed between editions</h1>\n'
        f'<p><b>What this is.</b> Monthly official reports restate earlier months. When the restated number differs from the one first printed, and the later edition does not mark it as revised, the change is easy to miss: a person or an AI system that read the first edition keeps quoting a number the publisher no longer prints. This page lists every such change found by comparing editions: <b>{total_r}</b> changed out of <b>{total_c}</b> figures compared so far.</p>\n'
        '<p class="small"><b>What it does not say.</b> Revising a figure is ordinary statistical practice; late records arrive and counts are updated. An entry here records only that two editions print different numbers for the same month and that the later one carries no revision mark for it. It says nothing about why, and it is not a finding of error. Figures compared and found unchanged are counted too, so the share that changes is visible.</p>\n'
        '<h2>Sources compared</h2>\n'
        f'<table><thead><tr><th>Report</th><th>Editions on file</th><th>Figures compared with an earlier edition</th><th>Changed</th></tr></thead><tbody>{src_rows}</tbody></table>\n'
        '<h2>Changed figures</h2>\n'
        f'<table><thead><tr><th>Figure</th><th>Month</th><th>First printed</th><th>Later printed</th><th>Difference</th><th>Receipt of the first printing</th></tr></thead><tbody>{rows}</tbody></table>\n'
        '<h2>How to use it</h2>\n'
        '<ul class="small"><li><b>Quoting a figure:</b> name the edition. &ldquo;65,328 (July 2026 report; restated as 65,327 in the August 2026 report)&rdquo; is complete; either number alone is not.</li>\n'
        '<li><b>Checking a receipt:</b> <a href="/verify.html">verify.html</a> returns the publisher&rsquo;s later value with any receipt whose figure was restated.</li>\n'
        '<li><b>Machine-readable:</b> <a href="/data/revisions.json">data/revisions.json</a> (this ledger), <a href="/data/official/index.json">data/official/</a> (every edition as restated, with document hashes). Method: <code>scripts/official_restate.py</code>.</li>\n'
        '<li><b>All restated figures:</b> <a href="/official-figures.html">official-figures.html</a>.</li></ul>\n'
        '<p class="small">The figures are US federal publications (public domain); this ledger is CC BY 4.0. Historical aggregates; not advice about any loan.</p>\n'
        '</div>\n</body></html>\n')
    if "--check" in sys.argv:
        cur = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else None
        print("revision ledger:", "current" if cur == page else "STALE"); sys.exit(0 if cur == page else 1)
    open(OUT, "w", encoding="utf-8").write(page)
    print(f"wrote revision-ledger.html: {total_r} changed of {total_c} compared, {len(per)} sources")


if __name__ == "__main__":
    main()
