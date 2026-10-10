#!/usr/bin/env python3
"""Embed schema.org Claim JSON-LD, generated from claims/*.json and *.contract.json, into the pages that
carry those figures. The contract becomes structured data an AI engine can read: value, universe, period,
what the figure does not establish, provenance, licence, receipt verification URL.

Idempotent: replaces the <script id="frc-claims-jsonld"> block if present, inserts before </head> otherwise.
Mapping is explicit (PAGES) so a figure is only declared on a page that actually shows it.
"""
import json
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PAGES = {
    "index.html": ["national-fha-denial-rate-2025", "major-lender-span-2025", "door-effect-38pct-2026"],
    "denial-code-lookup.html": ["major-lender-span-2025"],
    "why-was-my-mortgage-denied.html": ["national-fha-denial-rate-2025"],
    "data.html": ["national-fha-denial-rate-2025", "major-lender-span-2025", "door-effect-38pct-2026"],
    "door-effect.html": ["door-effect-38pct-2026"],
    "how-often-are-fha-loans-denied.html": ["national-fha-denial-rate-2025"],
    "fha-denial-rates-top-100.html": ["major-lender-span-2025"],
    "national-vs-local.html": ["national-vs-local-fha-2025"],
    "verdict-automated.html": ["national-fha-denial-rate-2025"],
}


def claim_ld(slug: str) -> dict | None:
    cp = os.path.join(ROOT, "claims", f"{slug}.json")
    kp = os.path.join(ROOT, "claims", f"{slug}.contract.json")
    if not os.path.exists(cp):
        return None
    with open(cp, encoding="utf-8") as fh:
        c = json.load(fh)
    k = {}
    if os.path.exists(kp):
        with open(kp, encoding="utf-8") as fh:
            k = json.load(fh)
    cl = c.get("claim", {})
    value = cl.get("value")
    vtxt = f"{value*100:.1f}%" if isinstance(value, float) and value <= 1 else str(value)
    template = (k.get("canonical_claim") or {}).get("template")
    text = template.replace("{value}", vtxt) if template else f"{cl.get('metric')}: {vtxt} ({cl.get('subject')}, {cl.get('period')})"
    quals = k.get("required_qualifiers") or {}
    out = {
        "@type": "Claim",
        "@id": c.get("canonical_url"),
        "name": cl.get("metric"),
        "text": text,
        "url": c.get("canonical_url"),
        "datePublished": (c.get("issued_at") or "")[:10],
        "author": {"@type": "Organization", "name": "FinanceRateCalc", "url": "https://financeratecalc.com"},
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "isBasedOn": "https://ffiec.cfpb.gov/data-publication/snapshot-national-loan-level-dataset/2025",
        "temporalCoverage": str(cl.get("period", "")),
        "spatialCoverage": "United States",
        "identifier": [{"@type": "PropertyValue", "propertyID": "frc_passport_id", "value": c.get("passport_id")},
                       {"@type": "PropertyValue", "propertyID": "sha256", "value": c.get("sha256")}],
        "additionalProperty": [{"@type": "PropertyValue", "name": f"required_qualifier:{q}", "value": v} for q, v in quals.items()]
        + [{"@type": "PropertyValue", "name": "does_not_establish", "value": d} for d in (k.get("does_not_establish") or [])]
        + [{"@type": "PropertyValue", "name": "definition", "value": cl.get("definition")},
           {"@type": "PropertyValue", "name": "unit", "value": cl.get("unit")},
           {"@type": "PropertyValue", "name": "receipt_verification", "value": "https://financeratecalc.com/verify.html"},
           {"@type": "PropertyValue", "name": "contract", "value": c.get("canonical_url", "").replace(".json", ".contract.json")}],
    }
    return out


def inject(page: str, slugs: list[str]) -> bool:
    p = os.path.join(ROOT, page)
    if not os.path.exists(p):
        return False
    items = [x for x in (claim_ld(s) for s in slugs) if x]
    if not items:
        return False
    block = ('<script type="application/ld+json" id="frc-claims-jsonld">'
             + json.dumps({"@context": "https://schema.org", "@graph": items}, ensure_ascii=False, separators=(",", ":"))
             + "</script>")
    with open(p, encoding="utf-8") as fh:
        t = fh.read()
    if 'id="frc-claims-jsonld"' in t:
        t2 = re.sub(r'<script type="application/ld\+json" id="frc-claims-jsonld">.*?</script>', lambda m: block, t, count=1, flags=re.DOTALL)
    else:
        t2 = t.replace("</head>", block + "\n</head>", 1)
    if t2 != t:
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(t2)
        return True
    return False


if __name__ == "__main__":
    changed = [pg for pg, s in PAGES.items() if inject(pg, s)]
    print("updated:", changed)
