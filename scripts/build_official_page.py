#!/usr/bin/env python3
"""official-figures.html: every Level-2 receipt (official publications restated as printed), generated from
data/official/*.json and the claim documents. --check exits 1 if the committed page differs. No number is typed here.
The page shell (style, nav) is read from build_outcomes_page.py so the two pages stay identical in look."""
import glob
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "official-figures.html")


def shell():
    src = open(os.path.join(ROOT, "scripts", "build_outcomes_page.py"), encoding="utf-8").read().splitlines()
    style = next(l for l in src if l.startswith("<style>")).replace("{{", "{").replace("}}", "}")
    nav = next(l for l in src if l.startswith("<nav data-frc-nav"))
    return style, nav


def main():
    style, nav = shell()
    files = sorted((f for f in glob.glob(os.path.join(ROOT, "data", "official", "*.json")) if os.path.basename(f) != "index.json"), reverse=True)
    editions = [json.load(open(f, encoding="utf-8")) for f in files]
    blocks = []
    n_receipts = 0
    for d in editions:
        doc = d["document"]
        rows = ""
        for fid, f in d["figures"].items():
            cid = f"official-{d['source_id']}-{d['period']}-{fid}"
            cp = os.path.join(ROOT, "claims", cid + ".json")
            if not os.path.exists(cp):
                continue
            c = json.load(open(cp, encoding="utf-8"))
            n_receipts += 1
            rows += (f'<tr><td>{html.escape(f["description"])}</td><td class=n><b>{html.escape(f["display"])}</b> {html.escape(f["unit"])}</td>'
                     f'<td>{html.escape(f["period"])}</td><td class="small">{html.escape(f["table"])} &middot; {html.escape(f["row_label"])}</td>'
                     f'<td class="small">{html.escape(f.get("revision", ""))}</td><td class="r"><a href="/claims/{cid}.json">{html.escape(c["receipt"])}</a></td></tr>')
        checks = d.get("prior_edition_check", {}).get("revisions", [])
        revised = [r for r in checks if r.get("revised")]
        pec = ""
        if checks:
            detail = ": " + "; ".join(f'{r["figure"]} {r["first_printed"]} &rarr; {r["restated_value"]}' for r in revised) if revised else ""
            pec = (f'<p class="small">Prior edition compared: <b>{html.escape(str(d["prior_edition_check"].get("edition_compared")))}</b> &mdash; '
                   f'{len(checks)} figures restated in this edition, {len(revised)} revised{detail}.</p>')
        url = doc.get("url") or ""
        blocks.append(
            f'<h2>{html.escape(doc["title"])} &mdash; {html.escape(doc["edition"])}</h2>\n'
            f'<p class="small">Publisher: {html.escape(doc["publisher"])}. Document: <a href="{html.escape(url)}">{html.escape(url or "(local file)")}</a>, '
            f'SHA-256 <code>{doc["sha256"][:16]}&hellip;</code>, retrieved {doc["retrieved_at"][:10]}. {html.escape(doc["exclusions"])}. '
            f'Not comparable with: {html.escape("; ".join(d["not_comparable_with"]))}.</p>\n{pec}\n'
            f'<table><thead><tr><th>Figure</th><th>Value</th><th>Period</th><th>Where in the document</th><th>Revision status</th><th>Receipt</th></tr></thead><tbody>{rows}</tbody></table>\n')
    gen = editions[0]["generated"][:10] if editions else ""
    body = "".join(blocks) if blocks else "<p>No edition restated yet.</p>"
    page = (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>Official figures, restated with receipts | FinanceRateCalc</title>\n'
        f'<meta name="description" content="Level-2 receipts: figures from official publications (first: HUD\'s monthly FHA Single Family Production Report) copied as printed, with the document\'s SHA-256, table and row, period, exclusions and revision status, so an AI system\'s restatement can be checked against the source. {n_receipts} receipted figures.">\n'
        '<link rel="canonical" href="https://financeratecalc.com/official-figures.html">\n'
        '<link rel="license" type="application/rsl+xml" href="https://financeratecalc.com/rsl.xml">\n'
        f'{style}\n<body>\n{nav}\n<div class="wrap">\n'
        f'<div class="kicker">FinanceRateCalc &middot; official figures &middot; Level-2 receipts &middot; generated {gen}</div>\n'
        '<h1>Official figures, restated as printed &mdash; with a receipt</h1>\n'
        '<p><b>What this is.</b> Nothing on this page was computed by FinanceRateCalc. Each figure is copied from an official publication exactly as printed, with the document&rsquo;s SHA-256, the table and row it sits in, its period, the publisher&rsquo;s own exclusion note, and whether a later edition revised it. The receipt <code>&#x27E6;FRC:official-&hellip;&#x27E7;</code> attests only that <i>this figure, with this definition and period, appears in that document with that hash</i>. Use contracts say what each figure is not: an endorsement is not an HMDA origination or application; none of these is a denial rate. Verify any receipt at <a href="/verify.html">verify.html</a>.</p>\n'
        '<p class="small">Why it exists: answer engines restate official figures with the wrong month, the wrong base or a superseded value. A receipt fixes the figure to its edition; a revision field says when the publisher changed it. Method: <code>scripts/official_restate.py</code>; data: <a href="/data/official/">data/official/</a>; spec: <a href="/spec/receipt-1.0.md">Receipt 1.0</a>.</p>\n'
        f'{body}\n'
        '<p class="small">Figures are US federal publications (public domain); the receipts and this page are CC BY 4.0. Historical aggregates; not advice about any loan.</p>\n'
        '</div>\n</body></html>\n')
    if "--check" in sys.argv:
        cur = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else None
        print("official-figures page:", "current" if cur == page else "STALE")
        sys.exit(0 if cur == page else 1)
    open(OUT, "w", encoding="utf-8").write(page)
    print(f"wrote official-figures.html: {len(editions)} editions, {n_receipts} receipts")


if __name__ == "__main__":
    main()
