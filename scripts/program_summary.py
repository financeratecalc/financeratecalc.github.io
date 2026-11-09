#!/usr/bin/env python3
"""First-release summary for a non-FHA program (VA, USDA, conventional): national and state figures plus the
application-outcomes shares, from the reference implementation's rebuild file and the outcomes file, written to
data/programs/<program>-2025.json, and the declared universe's count filled in universes.json.

    python3 scripts/program_summary.py <frc_rebuild.json> <application-outcomes.json> --sha256 <input sha> --url <source url>

No lender figures here: per provenance/universe-expansion-2025.md, lender tables for a new program follow only after
the national and state figures have passed the dry-run discipline. No page is written; this is data, with its universe.
"""
import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIVERSE = {"1": "U-CONV-2025-DECISIONED", "3": "U-VA-2025-DECISIONED", "4": "U-USDA-2025-DECISIONED"}
SLUG = {"1": "conv", "3": "va", "4": "usda"}


def main():
    rb = json.load(open(sys.argv[1], encoding="utf-8"))
    oc = json.load(open(sys.argv[2], encoding="utf-8"))
    a = sys.argv[3:]
    sha = a[a.index("--sha256") + 1] if "--sha256" in a else None
    url = a[a.index("--url") + 1] if "--url" in a else None
    lt = str(rb.get("loan_type"))
    if lt not in UNIVERSE:
        sys.exit(f"program_summary is for loan types {sorted(UNIVERSE)}; got {lt} (FHA keeps its own pipeline)")
    uid, slug = UNIVERSE[lt], SLUG[lt]
    nat = rb["national"]
    out = {
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "program": rb["program"], "loan_type": lt, "universe_id": uid, "closed_end_only": rb.get("closed_end_only", False),
        "declaration": "provenance/universe-expansion-2025.md",
        "input": {"url": url, "sha256": sha}, "code_commit": os.environ.get("GITHUB_SHA"),
        "national": {"decisioned_applications": nat["apps"], "denials": nat["denials"], "denial_rate_pct": nat["rate_pct"],
                     "reverse_mortgage_excluded": nat.get("hecm_excluded"), "open_end_rows_seen": rb.get("open_end_rows")},
        "outcomes_national": oc["national"],
        "states": [{"state": s["state"], "decisioned_applications": s["apps"], "denials": s["denials"], "denial_rate_pct": s["denial_rate_pct"]}
                   for s in sorted(rb["states"], key=lambda x: -x["apps"])],
        "status": "first release: national and state figures and outcome shares; no lender table yet; no page yet; receipts to follow once claim documents are built for this family",
        "contract_note": "Not comparable with other programs' rates as a judgement of programs or lenders: applicant populations differ by eligibility and composition.",
        "license": "CC BY 4.0",
    }
    os.makedirs(os.path.join(ROOT, "data", "programs"), exist_ok=True)
    p = os.path.join(ROOT, "data", "programs", f"{slug}-2025.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    up = os.path.join(ROOT, "universes.json")
    U = json.load(open(up, encoding="utf-8"))
    u = U["universes"][uid]
    u["count"] = nat["apps"]
    u["status"] = f"declared 2026-11-09; count filled by the pipeline on {out['generated'][:10]} (data/programs/{slug}-2025.json)"
    U["generated"] = out["generated"][:10]
    json.dump(U, open(up, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{rb['program']}: {nat['apps']:,} decisioned, {nat['denials']:,} denials, {nat['rate_pct']}%; {len(out['states'])} states; open-end rows seen {rb.get('open_end_rows')}; -> {os.path.relpath(p, ROOT)}; universes.json {uid} count set")


if __name__ == "__main__":
    main()
