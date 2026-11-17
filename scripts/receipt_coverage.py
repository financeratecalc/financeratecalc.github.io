#!/usr/bin/env python3
"""How many of the numbers printed on this site carry a receipt? Counted over every page, by section.

A rough count on purpose: every figure-like token in the visible text (a percentage, a dollar amount, a number of
three or more digits or with a decimal point; years excluded) against every receipt mark. One receipt covers one
figure, so the share is the part of the site's printed numbers that a reader or a machine can check in one step.
It overstates the gap where a receipted figure is repeated in a table of its own counts, and where a number is an
openly stated assumption; it is still the right direction to watch.

    python3 scripts/receipt_coverage.py            # writes eval/receipt-coverage.json
"""
import collections, datetime as dt, glob, html, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
NUM = re.compile(r"(?<![\w.])\$?\d[\d,]*\.?\d*%?")
REC = re.compile(r"⟦FRC:[^⟧]*⟧")


def group(f):
    if "/" in f:
        return f.split("/")[0] + "/"
    for p, g in [("mortgage-zip-", "mortgage-zip-*"), ("neighborhood-", "neighborhood-*"), ("blog-", "blog-*"), ("can-i-afford", "can-i-afford-*"), ("mortgage-", "mortgage-*")]:
        if f.startswith(p):
            return g
    if f.endswith("-fha-denial-rate.html") or f.endswith("-approval-rate.html"):
        return "lender pages"
    return "calculators" if "calculator" in f else "other root pages"


def main():
    tot = collections.defaultdict(lambda: [0, 0, 0])
    labelled = retired = 0
    for f in glob.glob("**/*.html", recursive=True):
        if f.startswith((".venv/", "node_modules/", "packages/")):
            continue
        s = open(f, encoding="utf-8", errors="ignore").read()
        if re.search(r"Retired \d{4}-\d{2}-\d{2};", s):   # a retirement notice prints no figure
            retired += 1; continue
        body = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<head[\s\S]*?</head>", " ", s)
        recs = len(REC.findall(body))
        t = html.unescape(re.sub(r"<[^>]+>", " ", REC.sub(" ", body)))
        nums = sum(1 for x in NUM.findall(t) if re.sub(r"\D", "", x) and not re.fullmatch(r"(19|20)\d\d", x) and ("%" in x or "$" in x or len(re.sub(r"\D", "", x)) >= 3 or "." in x))
        if 'data-frc-rebuilt="' in s:   # worked examples: every number is a named assumption or arithmetic on one, apart from the receipted figures
            labelled += nums
        g = tot[group(f)]; g[0] += 1; g[1] += nums; g[2] += recs
    rows = [{"section": k, "pages": p, "numbers": n, "receipts": r, "receipted_pct": round(100 * r / n, 1) if n else None} for k, (p, n, r) in sorted(tot.items(), key=lambda kv: -kv[1][1])]
    P, N, R = (sum(v[i] for v in tot.values()) for i in range(3))
    out = {"what": "Share of the figure-like numbers printed on this site that carry a receipt, by section. Rough count; see scripts/receipt_coverage.py for what it over- and under-counts.",
           "date": dt.date.today().isoformat(), "pages": P, "retired_notices_not_counted": retired, "numbers": N, "receipts": R, "receipted_pct": round(100 * R / N, 1),
           "named_assumption_or_its_arithmetic": labelled, "neither_pct": round(100 * (N - R - labelled) / N, 1), "sections": rows}
    json.dump(out, open("eval/receipt-coverage.json", "w", encoding="utf-8"), indent=1)
    print(f"{P} live pages ({retired} retirement notices not counted), {N} numbers: {R} receipted ({out['receipted_pct']}%), {labelled} named assumptions or arithmetic, {out['neither_pct']}% neither")


if __name__ == "__main__":
    main()
