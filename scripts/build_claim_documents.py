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
import datetime, glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "rl-env"))
from frc_citation.verify_offline import Verifier, sha8  # noqa: E402

BASE = "https://financeratecalc.com"
VERIFY = "https://frc-mcp.ziyetis.workers.dev/verify?r="
SOURCE = {"va": "CFPB/FFIEC HMDA public record 2025; data/programs/va-2025.json (VA, loan_type 3)", "usda": "CFPB/FFIEC HMDA public record 2025; data/programs/usda-2025.json (USDA, loan_type 4)", "conv": "CFPB/FFIEC HMDA public record 2025; data/programs/conv-2025.json (conventional closed-end, loan_type 1)",
          "outcome-va": "CFPB/FFIEC HMDA public record 2025; data/programs/va-2025.json (applications acted on = actions 1-5)", "outcome-usda": "CFPB/FFIEC HMDA public record 2025; data/programs/usda-2025.json", "outcome-conv": "CFPB/FFIEC HMDA public record 2025; data/programs/conv-2025.json",
          "official": "an official publication, restated as printed (Level 2); see claim.source_document and source_sha256",
          "outcome": "CFPB/FFIEC HMDA public record 2025; data/application-outcomes-2025.json (applications acted on = actions 1-5)", "lender": "CFPB/FFIEC HMDA public record 2025; api/lender/<slug>.json", "state": "CFPB/FFIEC HMDA public record 2025; api/state/<st>.json",
          "small-loan": "CFPB/FFIEC HMDA public record 2025; api/small-loan-penalty.json", "door": "data/door-effect-2025.json", "denial": "api/denial-reasons-top100.json"}


def receipt_ids():
    ids = ["national-fha-denial-rate-2025", "door-effect-38pct-2026", "small-loan-penalty-range-2025", "denial-reason-shares-top100-2025"]
    ids += [f"lender-{os.path.basename(f)[:-5]}-2025" for f in sorted(glob.glob(os.path.join(ROOT, "api/lender/*.json")))]
    ids += [f"state-{os.path.basename(f)[:-5]}-2025" for f in sorted(glob.glob(os.path.join(ROOT, "api/state/*.json")))]
    ids += [os.path.basename(f)[:-5] for f in sorted(glob.glob(os.path.join(ROOT, "claims/metro-gap-*.json"))) if not f.endswith(".contract.json")]
    d = json.load(open(os.path.join(ROOT, "api/small-loan-penalty.json")))
    ids += [f"small-loan-penalty-{r['state'].lower()}-2025" for r in d["ranked"]]
    op = os.path.join(ROOT, "data/application-outcomes-2025.json")
    if os.path.exists(op):
        ids += [f"outcome-{k}-2025" for k in ("originated", "approved-not-accepted", "denied", "withdrawn", "closed-incomplete", "ana-share")]
        ids += [f"outcome-{l['slug']}-2025" for l in json.load(open(op))["lenders"] if l.get("slug")]
    for f in sorted(glob.glob(os.path.join(ROOT, "data/programs/*-2025.json"))):
        d = json.load(open(f, encoding="utf-8")); prog = os.path.basename(f)[:-10]
        ids += [f"{prog}-national-denial-rate-2025"] + [f"{prog}-state-{s['state'].lower()}-denial-rate-2025" for s in d["states"]]
        ids += [f"outcome-{prog}-{k}-2025" for k in ("originated", "approved-not-accepted", "denied", "withdrawn", "closed-incomplete")]
    for f in sorted(glob.glob(os.path.join(ROOT, "data/purpose/*-2025.json"))):
        prog = os.path.basename(f)[:-10]
        ids += [f"purpose-{prog}-purchase-denial-rate-2025", f"purpose-{prog}-refinance-denial-rate-2025"]
    for f in sorted(glob.glob(os.path.join(ROOT, "data/official/*.json"))):
        if os.path.basename(f) == "index.json":
            continue
        d = json.load(open(f, encoding="utf-8"))
        ids += [f"official-{d['source_id']}-{d['period']}-{fid}" for fid in d["figures"]]
    return ids


DB = "https://ffiec.cfpb.gov/v2/data-browser-api/view"
FILTERS = "Keep loan_type=2 (FHA), action_taken in (1,2,3) as decisioned, reverse_mortgage != 1; denial = action_taken 3. The API has no reverse-mortgage filter: drop those rows yourself."


def reproduce_block(cid, obj, v):
    """A keyless CFPB Data Browser query that returns the rows behind the figure (2026-11-06). The URL is the
    publisher-independent route to the number: run it, apply FILTERS, compare. Not hashed (top-level field)."""
    base = {"api": "CFPB/FFIEC HMDA Data Browser API, no key", "filters": FILTERS, "docs": "https://ffiec.cfpb.gov/documentation/api/data-browser/"}
    NATIONAL_OUTCOMES = {"originated", "approved-not-accepted", "denied", "withdrawn", "closed-incomplete", "ana-share"}
    if cid == "national-fha-denial-rate-2025" or (cid.startswith("outcome-") and cid[8:-5] in NATIONAL_OUTCOMES):
        return {**base, "query_url": f"{DB}/nationwide/csv?years=2025&loan_types=2", "note": "outcome shares use action_taken 1-5 as the base; the denial rate uses 1-3"}
    if cid.startswith("state-"):
        return {**base, "query_url": f"{DB}/csv?years=2025&states={cid[6:8].upper()}&loan_types=2"}
    if cid.startswith("small-loan-penalty-") and cid != "small-loan-penalty-range-2025":
        return {**base, "query_url": f"{DB}/csv?years=2025&states={cid[19:21].upper()}&loan_types=2", "note": "small = loan_amount < 150000; big = loan_amount > 250000; penalty = small-loan denial rate / big-loan denial rate"}
    um = re.match(r"purpose-(fha|va|usda|conv)-(purchase|refinance)-", cid)
    if um:
        LT = {"fha": "2", "va": "3", "usda": "4", "conv": "1"}[um.group(1)]; lp = "1" if um.group(2) == "purchase" else "31,32"
        return {**base, "filters": FILTERS.replace("loan_type=2 (FHA)", f"loan_type={LT} ({obj.get('program')})") + f" Keep loan_purpose in ({lp})." + (" Also drop open_end_line_of_credit=1." if um.group(1) == "conv" else ""),
                "query_url": f"{DB}/nationwide/csv?years=2025&loan_types={LT}&loan_purposes={lp}", "note": "the all-purpose total of the same run equals the program's published decisioned count; see data/purpose/"}
    pm = re.match(r"(?:outcome-)?(va|usda|conv)-(national|state-([a-z]{2}))?", cid)
    if pm and pm.group(1):
        LT = {"va": "3", "usda": "4", "conv": "1"}[pm.group(1)]
        q = f"{DB}/nationwide/csv?years=2025&loan_types={LT}" if not pm.group(3) else f"{DB}/csv?years=2025&loan_types={LT}&states={pm.group(3).upper()}"
        return {**base, "filters": FILTERS.replace("loan_type=2 (FHA)", f"loan_type={LT} ({obj.get('program')})") + (" Also drop open_end_line_of_credit=1 (closed-end universe)." if pm.group(1) == "conv" else ""), "query_url": q,
                "note": "outcome shares use action_taken 1-5 as the base; the denial rate uses 1-3" if cid.startswith("outcome-") else None}
    if cid.startswith("official-"):
        return {"how": "open the source document (url in data/official/<source>-<period>.json; sha256 in claim.source_sha256), find the table and row named in the claim, read the column for the period", "note": "nothing to compute: the receipt attests that this figure appears in that document"}
    if cid.startswith("lender-") or cid.startswith("outcome-"):
        slug = cid[7:-5] if cid.startswith("lender-") else cid[8:-5]
        try:
            lei = v._json(f"/api/lender/{slug}.json")["lei"]
            return {**base, "query_url": f"{DB}/csv?years=2025&leis={lei}&loan_types=2"}
        except Exception:
            return base
    if cid.startswith("metro-gap-"):
        subj = str(obj.get("subject", ""))
        m = re.search(r"MSA (\d{5})", subj)
        if m:
            return {**base, "query_url": f"{DB}/csv?years=2025&msamds={m.group(1)}&loan_types=2", "note": "lenders with >= 100 decisioned applications in the metro; gap = highest minus lowest observed denial rate"}
        return base
    return base


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
        pm = re.match(r"(?:outcome-)?(va|usda|conv)-", cid)
        if pm and "claim" not in doc:
            prog = pm.group(1); LT = {"va": "3", "usda": "4", "conv": "1"}[prog]
            doc["provenance"]["dataset"] = f"loan_type={LT} ({obj.get('program')}); action_taken in {{1,2,3}} = decisioned; reverse mortgages excluded" + ("; open-end lines of credit excluded" if prog == "conv" else "") + f"; universe {obj.get('universe_id')} (provenance/universe-expansion-2025.md)"
            doc["attribution"]["required_text"] = f"Source: FinanceRateCalc analysis of the public CFPB HMDA 2025 record ({obj.get('program')} loans); historical aggregate only."
        um = re.match(r"purpose-(fha|va|usda|conv)-(purchase|refinance)-", cid)
        if um and "claim" not in doc:
            LT = {"fha": "2", "va": "3", "usda": "4", "conv": "1"}[um.group(1)]
            doc["provenance"]["primary_source"] = f"CFPB/FFIEC HMDA public record 2025; data/purpose/{um.group(1)}-2025.json"
            doc["provenance"]["dataset"] = f"loan_type={LT} ({obj.get('program')}); {obj.get('loan_purpose')}; action_taken in {{1,2,3}} = decisioned; reverse mortgages excluded; universe {obj.get('universe_id')} (provenance/universe-purpose-split-2025.md)"
            doc["attribution"]["required_text"] = f"Source: FinanceRateCalc analysis of the public CFPB HMDA 2025 record ({obj.get('program')} loans); historical aggregate only."
        if cid.startswith("official-") and "claim" not in doc:
            doc["provenance"] = {"primary_source": obj["source_document"] + " — " + obj["edition"], "dataset": "official publication; figure copied as printed, not computed; " + obj["exclusions"],
                                 "source_sha256": obj["source_sha256"], "code_history": "https://github.com/financeratecalc/financeratecalc.github.io"}
            doc["attribution"] = {"required_text": f"Source: {obj['source_document']}, {obj['edition']} (restated with receipt by FinanceRateCalc).", "license": "public domain (US federal publication); receipt CC BY 4.0"}
        h = sha8(obj)
        new = dict(doc)
        new["claim"] = obj
        new.update({"receipt_document": "1.0", "id": cid, "display_value": cur, "hash_rule": "jcs-sha256-8", "hash8": h,
                    "receipt": f"⟦FRC:{cid}:{cur}:{h}⟧", "verify_url": VERIFY + f"%E2%9F%A6FRC:{cid}:{cur}:{h}%E2%9F%A7",
                    "corrections_url": f"{BASE}/corrections.json", "spec": f"{BASE}/spec/receipt-1.0.md"})
        new["reproduce"] = {**(doc.get("reproduce") or {}), **reproduce_block(cid, obj, v)}
        if cid.startswith("official-"):
            # revision status lives outside the hashed claim: the receipt attests the figure as printed in its edition
            m = re.match(r"official-([a-z0-9]+(?:-[a-z0-9]+)*?)-(\d{4}-\d{2})-([a-z0-9-]+)$", cid)
            f = json.load(open(os.path.join(ROOT, "data", "official", f"{m.group(1)}-{m.group(2)}.json"), encoding="utf-8"))["figures"][m.group(3)]
            new["revision_status"] = {k: f[k] for k in ("revision", "revised_in", "revised_to") if k in f}
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
    try:
        sys.exit(main())
    except Exception:
        import traceback
        tb = traceback.format_exc().strip().splitlines()
        print(("::error::" if os.environ.get("GITHUB_ACTIONS") == "true" else "") + "crash: " + " | ".join(tb[-3:])[:600])
        sys.exit(2)
