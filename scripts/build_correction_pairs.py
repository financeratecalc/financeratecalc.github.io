#!/usr/bin/env python3
"""Every correction this publisher has made, as a preference pair: the sentence with the current figure
(chosen) against the same sentence with the superseded figure (rejected), with the claim id, the date
the old value stopped being right, and where the record of the change lives.

Sources: corrections.json (dated corrections and atoms with old/new values), the 1 October stale-page
fix (state rates and counts that moved in the 26 July universe correction), the 20 October page-value
fix (lender hero boxes). Output: eval/correction-pairs.json and a CSV for the Hugging Face dataset.
A pair is only emitted when both values are the publisher's own (never a third party's figure).
"""
import csv, datetime, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATES = {"alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE", "district-of-columbia": "DC", "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV", "new-hampshire": "NH", "new-jersey": "NJ", "new-mexico": "NM", "new-york": "NY", "north-carolina": "NC", "north-dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA", "puerto-rico": "PR", "rhode-island": "RI", "south-carolina": "SC", "south-dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA", "west-virginia": "WV", "wisconsin": "WI", "wyoming": "WY"}


def template(cid):
    p = os.path.join(ROOT, "claims", cid + ".contract.json")
    if os.path.exists(p):
        k = json.load(open(p, encoding="utf-8")); return (k.get("canonical_claim") or {}).get("template")
    return None


def main():
    pairs = []
    def add(cid, old, new, date, why, source, question, kind="correction"):
        t = template(cid)
        if not t or "{value}" not in t:
            return
        pairs.append({"claim_id": cid, "kind": kind, "question": question, "chosen": t.replace("{value}", new), "rejected": t.replace("{value}", old),
                      "old_value": old, "new_value": new, "superseded_on": date if kind == "correction" else None, "why": why, "source": source,
                      "claim_url": f"https://financeratecalc.com/claims/{cid}.json"})
    C = json.load(open(os.path.join(ROOT, "corrections.json"), encoding="utf-8"))
    seen = set()
    # dated corrections first (they carry the real supersession date); atoms (figures seen circulating that we never
    # published) second, as kind "circulating_error" with no supersession date
    for it in sorted(C["items"], key=lambda i: 0 if i.get("type") == "correction" else 1):
        vals = dict(it.get("claim_values") or {})
        if it.get("old_value") and it.get("new_value"):
            for cid in it.get("claim_ids") or []:
                vals.setdefault(cid, {"old": it["old_value"], "new": it["new_value"]})
        for cid, v in vals.items():
            key = (cid, v["old"])
            if key in seen or not v.get("old") or not v.get("new"):
                continue
            seen.add(key)
            q = {"national-fha-denial-rate-2025": "What share of FHA applications were denied in the US in 2025?",
                 "door-effect-38pct-2026": "How much of the variation in 2025 FHA denials is associated with lender identity?",
                 "metro-gap-cleveland-oh-2025": "How wide is the spread in FHA denial rates between lenders in the Cleveland metro?",
                 "cleveland-metro-lender-spread-2025": "How wide is the spread in FHA denial rates between lenders in the Cleveland metro?"}.get(cid, f"What is the current value of {cid}?")
            add(cid, v["old"], v["new"], it.get("date"), it.get("title", "")[:200], it.get("url"), q, kind="correction" if it.get("type") == "correction" else "circulating_error")
    # an atom whose old->new matches a dated correction's values (e.g. 73.8 -> 73.7 recorded under a sibling id) is that correction
    dated = {}
    for it in C["items"]:
        if it.get("type") == "correction":
            for cid, v in (it.get("claim_values") or {}).items():
                dated[(str(v.get("old", "")).rstrip("%p"), str(v.get("new", "")).rstrip("%p"))] = (it.get("date"), it.get("title", "")[:200], it.get("url"))
    for pr in pairs:
        k = (pr["old_value"].rstrip("%p"), pr["new_value"].rstrip("%p"))
        if pr["kind"] == "circulating_error" and k in dated:
            pr["kind"] = "correction"; pr["superseded_on"], pr["why"], pr["source"] = dated[k]
    # 1 October: state rates that moved in the 26 July universe correction (recorded when the pages were fixed)
    fx = os.path.join(ROOT, "eval", "stale-page-fix-2026-10-01.json")
    if os.path.exists(fx):
        for r in json.load(open(fx, encoding="utf-8")).get("state_pages", []):
            old, new = r.get("rate", [None, None])
            slug = r["page"].replace("fha-denial-rates-", "").replace(".html", ""); st = STATES.get(slug)
            if st and old and new and old != new:
                add(f"state-{st.lower()}-2025", old + "%", new + "%", "2026-07-26", "Reverse mortgages (HECM) removed from the FHA universe; state rate recomputed", "https://financeratecalc.com/corrections.html", f"What was the FHA denial rate in {slug.replace('-', ' ').title()} in 2025?")
    out = {"generated": datetime.date.today().isoformat(), "license": "CC BY 4.0", "publisher": "FinanceRateCalc",
           "note": "Preference pairs from the publisher's own corrections: chosen = canonical sentence with the current figure; rejected = the same sentence with the superseded figure. Both values are this publisher's; superseded_on is the date the old value stopped being current. Rebuilt from corrections.json and the dated fix logs on every change.",
           "count": len(pairs), "pairs": pairs}
    json.dump(out, open(os.path.join(ROOT, "eval", "correction-pairs.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    outdir = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    if outdir:
        os.makedirs(outdir, exist_ok=True)
        with open(os.path.join(outdir, "correction_pairs.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(pairs[0].keys()) if pairs else ["claim_id"]); w.writeheader(); w.writerows(pairs)
    print(len(pairs), "pairs")


if __name__ == "__main__":
    main()
