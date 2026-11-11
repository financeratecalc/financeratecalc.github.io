#!/usr/bin/env python3
"""data/revisions.json: every figure an official publisher changed in a later edition without marking it, read from
data/official/*.json (the prior-edition check of scripts/official_restate.py). One entry per revised figure, newest
first, with both receipts' context. Nothing is computed beyond the difference of two printed numbers."""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://financeratecalc.com"


def main():
    items, checked = [], 0
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "official", "*.json"))):
        if os.path.basename(f) == "index.json":
            continue
        d = json.load(open(f, encoding="utf-8"))
        checked += len(d.get("prior_edition_check", {}).get("revisions", []))
        for fid, x in d["figures"].items():
            if x.get("revised_to") is None:
                continue
            cid = f"official-{d['source_id']}-{d['period']}-{fid}"
            c = json.load(open(os.path.join(ROOT, "claims", cid + ".json"), encoding="utf-8"))
            items.append({"source": d["document"]["title"], "publisher": d["document"]["publisher"], "figure": fid, "description": x["description"],
                          "period": x["period"], "first_printed": x["value"], "first_printed_in": d["document"]["edition"], "first_document_sha256": d["document"]["sha256"],
                          "restated_as": x["revised_to"], "restated_in": x.get("revised_in"), "difference": round(x["revised_to"] - x["value"], 6),
                          "marked_as_revised_by_publisher": False, "receipt_of_first_printing": c["receipt"], "claim_url": f"{BASE}/claims/{cid}.json",
                          "where": f"{x['table']} · {x['row_label']}"})
    items.sort(key=lambda i: (i["period"], i["figure"]), reverse=True)
    eds = sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(ROOT, "data", "official", "*.json")) if os.path.basename(f) != "index.json")
    out = {"title": "Revision watch: figures an official publisher changed in a later edition",
           "what": "Each entry is a figure printed in one edition of an official report and restated with a different value in the next. The reports do not mark these changes; they are found by comparing editions. Differences only, nothing estimated.",
           "editions_compared": eds, "figures_compared": checked, "revisions_found": len(items), "items": items,
           "page": f"{BASE}/official-figures.html", "license": "CC BY 4.0 (the figures themselves are US federal publications, public domain)"}
    p = os.path.join(ROOT, "data", "revisions.json")
    old = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
    if old != out:
        json.dump(out, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"revisions feed: {len(items)} revisions out of {checked} figures compared across {len(eds)} editions")


if __name__ == "__main__":
    main()
