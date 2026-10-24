#!/usr/bin/env python3
"""One claim document per receipted figure (Receipt 1.0, spec/receipt-1.0.md).

Every claim id that this publisher issues receipts for must resolve to /claims/<id>.json, so that a
verifier can fetch the document, canonicalise its `claim` block (RFC 8785) and recompute the hash in
the receipt without asking this publisher. Until 2026-10-21 half of the ids (lender, state,
small-loan, door-effect, denial-reason) had no document: the worker built the hashed object on the
fly from api/*.json. This script writes those documents from the same constructor
(rl-env/frc_citation/verify_offline.py, Verifier.claim_object), so the hash is the same, and adds
the Receipt 1.0 fields to the documents that already existed (metro gaps, national).

Fields added at top level (never inside `claim`, which is the hashed block):
  receipt_document, display_value, hash_rule, hash8, receipt, verify_url, corrections_url

--check: exit 1 if any document's claim block or display value differs from the data files.
"""
import datetime, glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "rl-env"))
from frc_citation.verify_offline import Verifier, sha8  # noqa: E402

BASE = "https://financeratecalc.com"
VERIFY = "https://frc-mcp.ziyetis.workers.dev/verify?r="
SOURCE = {"lender": "CFPB/FFIEC HMDA public record 2025; api/lender/<slug>.json", "state": "CFPB/FFIEC HMDA public record 2025; api/state/<st>.json",
          "small-loan": "CFPB/FFIEC HMDA public record 2025; api/small-loan-penalty.json", "door": "data/door-effect-2025.json", "denial": "api/denial-reasons-top100.json"}


def receipt_ids():
    ids = ["national-fha-denial-rate-2025", "door-effect-38pct-2026", "small-loan-penalty-range-2025", "denial-reason-shares-top100-2025"]
    ids += [f"lender-{os.path.basename(f)[:-5]}-2025" for f in sorted(glob.glob(os.path.join(ROOT, "api/lender/*.json")))]
    ids += [f"state-{os.path.basename(f)[:-5]}-2025" for f in sorted(glob.glob(os.path.join(ROOT, "api/state/*.json")))]
    ids += [os.path.basename(f)[:-5] for f in sorted(glob.glob(os.path.join(ROOT, "claims/metro-gap-*.json"))) if not f.endswith(".contract.json")]
    d = json.load(open(os.path.join(ROOT, "api/small-loan-penalty.json")))
    ids += [f"small-loan-penalty-{r['state'].lower()}-2025" for r in d["ranked"]]
    return ids


def main():
    check = "--check" in sys.argv
    v = Verifier(ROOT)
    today = datetime.date.today().isoformat()
    written = unchanged = drift = 0
    for cid in receipt_ids():
        try:
            cur, obj = v.claim_object(cid)
        except Exception as e:
            print("unresolved", cid, e); continue
        path = os.path.join(ROOT, "claims", cid + ".json")
        doc = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {
            "passport_version": "0.1", "issuer": "FinanceRateCalc", "issued_at": today + "T00:00:00Z",
            "provenance": {"primary_source": next(v for k, v in SOURCE.items() if cid.startswith(k)) if any(cid.startswith(k) for k in SOURCE) else "CFPB/FFIEC HMDA public record 2025",
                           "dataset": "loan_type=2 (FHA); action_taken in {1,2,3} = decisioned; reverse mortgages excluded",
                           "code_history": "https://github.com/financeratecalc/financeratecalc.github.io"},
            "use_boundary": {"allowed": ["historical aggregate comparison", "journalism", "market analysis", "research"],
                             "prohibited": ["individual approval prediction", "borrower profiling", "personalized lender recommendation"], "minimum_cell_size": 100},
            "attribution": {"required_text": "Source: FinanceRateCalc analysis of the public CFPB HMDA 2025 record; historical aggregate only.", "license": "CC BY 4.0"},
            "passport_id": "frc:claim:" + cid, "canonical_url": f"{BASE}/claims/{cid}.json"}
        h = sha8(obj)
        new = dict(doc)
        new["claim"] = obj
        new.update({"receipt_document": "1.0", "id": cid, "display_value": cur, "hash_rule": "jcs-sha256-8", "hash8": h,
                    "receipt": f"⟦FRC:{cid}:{cur}:{h}⟧", "verify_url": VERIFY + f"%E2%9F%A6FRC:{cid}:{cur}:{h}%E2%9F%A7",
                    "corrections_url": f"{BASE}/corrections.json", "spec": f"{BASE}/spec/receipt-1.0.md"})
        if new == doc:
            unchanged += 1; continue
        if check:
            drift += 1
            diff = [k for k in set(new) | set(doc) if new.get(k) != doc.get(k)]
            msg = f"drift {cid}: fields {sorted(diff)}; " + "; ".join(f"{k}: doc={str(doc.get(k))[:80]!r} data={str(new.get(k))[:80]!r}" for k in sorted(diff)[:3])
            print(("::error::" if os.environ.get("GITHUB_ACTIONS") == "true" else "") + msg)
            continue
        json.dump(new, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False); written += 1
    if check:
        print(f"checked; drift: {drift}")
        return 1 if drift else 0
    print(f"written {written}, unchanged {unchanged}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
