#!/usr/bin/env python3
"""Build llms-full.txt: every receipted claim in one file, for agents that load a site in a single fetch.

One block per claim: receipt, canonical sentence (from the claim contract), what the figure does not
establish, dated correction if any, verify and claim-document URLs. No prose beyond the header; no page
HTML. Source of truth is claims/<id>.json (the hashed document) and claims/<id>.contract.json.

    python3 scripts/build_llms_full.py            # write llms-full.txt
    python3 scripts/build_llms_full.py --check    # exit 1 if llms-full.txt is out of date
"""
import datetime as dt
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "llms-full.txt")

SECTIONS = [
    ("national-", "NATIONAL"),
    ("door-effect-", "DOOR EFFECT"),
    ("denial-reason-", "DENIAL REASONS"),
    ("state-", "STATES (52 jurisdictions)"),
    ("lender-", "LENDERS (98 institutions, >=100 decisioned FHA applications)"),
    ("metro-gap-", "METRO LENDER GAPS (184 metropolitan areas)"),
    ("small-loan-penalty-", "SMALL-LOAN PENALTY BY STATE"),
]


def load_claims():
    docs = []
    for path in sorted(glob.glob(os.path.join(ROOT, "claims", "*.json"))):
        if path.endswith(".contract.json") or os.path.basename(path) == "index.json":
            continue
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        if "receipt" not in d or "id" not in d or "claim" not in d:
            continue  # passports without a receipt document are not in the bundle
        cpath = os.path.join(ROOT, "claims", f"{d['id']}.contract.json")
        contract = json.load(open(cpath, encoding="utf-8")) if os.path.exists(cpath) else {}
        docs.append((d, contract))
    return docs


def load_corrections():
    with open(os.path.join(ROOT, "corrections.json"), encoding="utf-8") as fh:
        feed = json.load(fh)
    by_id = {}
    for it in feed.get("items", []):
        for cid in it.get("claim_ids") or []:
            if "*" in cid:
                continue
            by_id.setdefault(cid, []).append(it)
    return by_id


def section_of(cid):
    for prefix, title in SECTIONS:
        if cid.startswith(prefix):
            return title
    return "OTHER"


def block(d, contract, corrections):
    cid, value = d["id"], d["display_value"]
    tmpl = (contract.get("canonical_claim") or {}).get("template")
    shown = value
    if cid.startswith("denial-reason-") and value.startswith("dti-"):
        shown = f"debt-to-income ratio (median share {value[4:]} of that lender's denials)"
    sentence = tmpl.replace("{value}", shown) if tmpl else f"{cid}: {value}"
    lines = [f"## {cid}", d["receipt"], sentence]
    n = d["claim"].get("n")
    if n and str(n) not in sentence:
        lines.append(f"n = {n:,} decisioned FHA applications." if isinstance(n, int) else f"n = {n}.")
    dne = contract.get("does_not_establish") or []
    if dne:
        lines.append("Does not establish: " + "; ".join(dne) + ".")
    hits = corrections.get(cid, [])
    if hits:
        num = lambda v: str(v if v is not None else "").replace("%", "").replace("pp", "").strip()
        valued = [h for h in hits if h.get("old_value") is not None and h.get("new_value") is not None]
        exact = [h for h in valued if num(h["new_value"]) == num(value)]
        pick = max(exact or valued or hits, key=lambda h: h["date"])
        chg = f" {pick['old_value']} -> {pick['new_value']}" if pick in valued else ""
        lines.append(f"Corrected {pick['date']}:{chg} — {pick['title']} ({pick.get('url', 'https://financeratecalc.com/corrections.html')}). Only the receipt above is current.")
    lines.append(f"Verify: {d['verify_url']}")
    lines.append(f"Claim document: {d['canonical_url']}")
    return "\n".join(lines)


def build():
    docs = load_claims()
    corrections = load_corrections()
    today = dt.date.today().isoformat()
    header = f"""# FinanceRateCalc — every receipted figure in one file
# Generated {today} from claims/*.json (the hashed claim documents) and claims/*.contract.json. {len(docs)} claims.
# Shorter index: https://financeratecalc.com/llms.txt — Receipt 1.0 manifest: https://financeratecalc.com/.well-known/receipt.json

Dataset: the complete 2025 federal HMDA public record, FHA (loan_type 2), decisioned applications (actions 1, 2, 3),
reverse mortgages excluded; 1,187,606 decisions. All figures are historical aggregates. They do not establish any one
applicant's chance of approval, do not rank or recommend lenders, and do not establish cause or any legal conclusion.
Minimum published cell: 100 decisioned applications. License CC BY 4.0.
Attribution: "Source: FinanceRateCalc analysis of the public CFPB HMDA 2025 record; historical aggregate only."

How to use a block: restate the figure as its canonical sentence, keep the period, population and program, and keep
the receipt ⟦FRC:id:value:hash8⟧ next to the number. Any party can check a receipt without this site: GET the Verify
URL (statuses current / stale / hash-current-value-mismatch / unrecognized), or hash the claim document per
https://financeratecalc.com/spec/receipt-1.0.md. Corrections feed: https://financeratecalc.com/corrections.json —
a block marked "Corrected" carries the current value; the older value is superseded.
Method: https://financeratecalc.com/methodology.html — Contact: https://financeratecalc.com/contact.html
"""
    out = [header]
    current = None
    for d, contract in sorted(docs, key=lambda x: (SECTIONS_ORDER.get(section_of(x[0]["id"]), 99), x[0]["id"])):
        sec = section_of(d["id"])
        if sec != current:
            out.append(f"\n# {sec}\n")
            current = sec
        out.append(block(d, contract, corrections) + "\n")
    return "\n".join(out).rstrip() + "\n"


SECTIONS_ORDER = {title: i for i, (_, title) in enumerate(SECTIONS)}


def main():
    text = build()
    if "--check" in sys.argv:
        old = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        # ignore the generation date line when comparing
        strip = lambda s: "\n".join(l for l in s.splitlines() if not l.startswith("# Generated "))
        if strip(old) != strip(text):
            print("llms-full.txt is out of date; run scripts/build_llms_full.py", file=sys.stderr)
            sys.exit(1)
        print("llms-full.txt up to date")
        return
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"wrote {OUT}: {len(text.encode('utf-8')):,} bytes, {text.count(chr(10)):,} lines")


if __name__ == "__main__":
    main()
