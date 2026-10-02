#!/usr/bin/env python3
"""Claim Contract Compiler, v0.1 (2026-10-02).

A publisher gives eight fields about one statistic. The compiler returns everything the
Claim Contract 1.0 standard needs so the figure survives machine restatement:

  1. safe_sentence            the one sentence a machine may quote verbatim
  2. passport                 what the number is and where it came from (hash included)
  3. contract                 how it may be restated: qualifiers, does-not-establish, forbidden transformations
  4. receipt                  ⟦<PUB>:<id>:<value>:<hash8>:<channel><YYMM>⟧
  5. forbidden_paraphrases    worked examples of the restatements the contract blocks, each with its reason code
  6. test_vectors             pass/block vectors derived from the contract (normative, re-derivable)
  7. jsonld                   schema.org Dataset block with the receipt as a PropertyValue identifier
  8. gold_record              the answer-key row an evaluator grades against (key tokens, rubric)
  9. verify_url               where any client checks the receipt

Input (JSON, stdin or file):
{
  "publisher": "FRC",                       # receipt prefix, letters/digits
  "id": "national-fha-denial-rate-2025",    # claim id, lowercase slug
  "metric": "fha_denial_rate",
  "value": 22.08, "display_value": "22.1%", # display_value is what appears in text
  "unit": "share_of_decisioned_applications",
  "subject": "United States, all reporting lenders",
  "period": "2025",
  "definition": "denials (action 3) / decisioned applications (actions 1,2,3), FHA (loan_type 2)",
  "population": "decisioned FHA applications",
  "program_scope": "FHA only, not all mortgages",
  "n": 1187606,
  "source": "CFPB/FFIEC HMDA public record, 2025",
  "canonical_url": "https://financeratecalc.com/claims/national-fha-denial-rate-2025.json",
  "verify_base": "https://frc-mcp.ziyetis.workers.dev/verify?r=",
  "template": "In {period}, {value} of {population} were denied.",   # optional
  "attribution": "FinanceRateCalc analysis of the public CFPB HMDA 2025 record",  # optional
  "corrections": [],                         # optional list of {date, from, to, reason}
  "channel": "p"                             # optional issue channel letter
}

Usage: python claimcompiler.py input.json > out.json
       python claimcompiler.py --demo        # compiles the national FHA figure
No network. Deterministic. CC BY 4.0.
"""
from __future__ import annotations
import datetime, hashlib, json, re, sys, urllib.parse

POLICY = {
    "causal_attribution": ("CAUSAL_ATTRIBUTION", "restates an observed association as a cause (\"because lenders are stricter\")"),
    "individual_prediction": ("INDIVIDUAL_PREDICTION_PROHIBITED", "turns an aggregate into a probability for a person (\"you have a 22% chance of denial\")"),
    "personalized_lender_recommendation": ("RECOMMENDATION_PROHIBITED", "turns a statistic into advice about where to apply (\"avoid lender X\")"),
    "legal_conclusion": ("LEGAL_CONCLUSION_PROHIBITED", "treats a rate as evidence of misconduct or a violation"),
}


def canon_hash(claim: dict) -> str:
    """SHA-256 of the claim object: keys sorted, no whitespace, nested keys filtered to the
    top-level key set (the JSON.stringify(obj, keys) convention used by the reference /verify)."""
    allowed = set(claim.keys())
    def filt(x):
        if isinstance(x, dict): return {k: filt(v) for k, v in x.items() if k in allowed}
        if isinstance(x, list): return [filt(v) for v in x]
        if isinstance(x, float) and x.is_integer(): return int(x)
        return x
    canon = json.dumps(filt(claim), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def compile_claim(inp: dict) -> dict:
    pub = re.sub(r"[^A-Z0-9]", "", str(inp.get("publisher", "PUB")).upper()) or "PUB"
    cid = re.sub(r"[^a-z0-9-]", "-", str(inp["id"]).lower()).strip("-")
    value = inp["value"]; disp = str(inp.get("display_value") or value)
    if ":" in disp: raise ValueError("display_value must not contain a colon (receipt delimiter)")
    period = str(inp["period"]); population = inp["population"]; scope = inp.get("program_scope", "")
    claim = {"metric": inp["metric"], "value": value, "unit": inp["unit"], "subject": inp["subject"], "period": period, "definition": inp["definition"]}
    if inp.get("n") is not None and inp.get("n_in_claim", True): claim["n"] = inp["n"]
    claim.update(inp.get("claim_extra") or {})  # extra fields that are part of the hashed claim (e.g. a note)
    full = canon_hash(claim); h8 = full[:8]
    now = datetime.datetime.utcnow(); ch = f"{(inp.get('channel') or 'p')[:1].lower()}{str(now.year)[2:]}{now.month:02d}"
    receipt = f"⟦{pub}:{cid}:{disp}:{h8}:{ch}⟧"
    attribution = inp.get("attribution") or f"{inp.get('publisher_name', pub)} analysis of {inp['source']}"
    template = inp.get("template") or "In {period}, {value} of {population} were counted under this definition."
    safe = template.format(period=period, value=disp, population=population) + f" Source: {attribution}; historical aggregate, not a prediction about any case."
    safe_with_receipt = safe.replace(disp, f"{disp} {receipt}", 1)

    # does_not_establish: each entry derives from a passport field or a policy clause
    dne = [
        {"statement": f"a figure for any population other than {population}", "derived_from": "claim.definition", "derivation_kind": "syntactic"},
        {"statement": f"a rate for any period other than {period}", "derived_from": "claim.period", "derivation_kind": "syntactic"},
        {"statement": f"a figure for {inp.get('subject')} broken down by any sub-group not in the definition", "derived_from": "claim.subject", "derivation_kind": "semantic"},
    ]
    if scope: dne.append({"statement": f"a figure outside its program scope ({scope})", "derived_from": "claim.definition", "derivation_kind": "semantic"})
    for k, (code, _) in POLICY.items():
        dne.append({"statement": {"causal_attribution": "any cause of the figure", "individual_prediction": "any individual's probability",
                                  "personalized_lender_recommendation": "any recommendation of where to apply", "legal_conclusion": "any legal conclusion about any party"}[k],
                    "derived_from": f"policy:{k}", "derivation_kind": "syntactic"})

    passport = {"passport_version": "1.0", "passport_id": f"{pub.lower()}:claim:{cid}", "issuer": inp.get("publisher_name", pub),
                "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "canonical_url": inp.get("canonical_url"), "sha256": full, "claim": claim,
                "provenance": {"primary_source": inp["source"], "dataset": inp.get("dataset", ""), "code_history": inp.get("code_history", "")},
                "use_boundary": {"allowed": ["historical aggregate comparison", "journalism", "research"], "prohibited": list(POLICY), "minimum_cell_size": inp.get("minimum_cell_size", 100)},
                "corrections": inp.get("corrections", []),
                "attribution": {"required_text": f"Source: {attribution}; historical aggregate only.", "license": inp.get("license", "CC BY 4.0")},
                "independent_reproduction_status": inp.get("independent_reproduction_status", "not yet independently reproduced")}
    contract = {"contract_version": "1.0", "passport_id": passport["passport_id"],
                "canonical_claim": {"template": template, "required_fields": ["period", "population"] + (["program_scope"] if scope else [])},
                "required_qualifiers": {k: v for k, v in {"period": period, "population": population, "program_scope": scope}.items() if v},
                "does_not_establish": dne, "forbidden_transformations": list(POLICY),
                "quotable_sentence": safe_with_receipt, "claim_receipt": receipt}
    vectors = [{"id": "pass-canonical", "proposed_use": {"population": population, "period": period, **{f: False for f in ("causal_assertion", "individual_prediction", "recommendation", "legal_conclusion")}}, "expected_verdict": "pass"},
               {"id": "needs-period", "proposed_use": {"population": population, "period_missing": True}, "expected_verdict": "needs_qualifier", "reason_code": "PERIOD_MISSING"},
               {"id": "fail-scope", "proposed_use": {"population": "all " + population.split()[-1] if population else "all"}, "expected_verdict": "block", "reason_code": "SCOPE_TOO_BROAD"},
               {"id": "fail-period", "proposed_use": {"period": str(int(period) + 1) if period.isdigit() else "other"}, "expected_verdict": "block", "reason_code": "STALE_VALUE"}]
    for k, (code, _) in POLICY.items():
        vectors.append({"id": f"fail-{k}", "proposed_use": {k: True}, "expected_verdict": "block", "reason_code": code})
    contract["test_vectors"] = vectors
    forbidden = [
        {"paraphrase": f"About {disp} of all applicants get rejected.", "reason_code": "SCOPE_TOO_BROAD", "why": f"population widened beyond {population}"},
        {"paraphrase": f"{disp} are denied every year.", "reason_code": "PERIOD_MISSING", "why": f"the figure is for {period} only"},
        {"paraphrase": f"You have a {disp} chance of being denied.", "reason_code": "INDIVIDUAL_PREDICTION_PROHIBITED", "why": "aggregate restated as an individual probability"},
        {"paraphrase": f"Denials run at {disp} because lenders are too strict.", "reason_code": "CAUSAL_ATTRIBUTION", "why": "association restated as a cause"},
        {"paraphrase": f"The {disp} figure shows lenders are breaking the rules.", "reason_code": "LEGAL_CONCLUSION_PROHIBITED", "why": "a rate is not evidence of a violation"},
    ]
    jsonld = {"@context": "https://schema.org", "@type": "Dataset", "name": f"{inp['metric']} {period} ({inp['subject']})", "description": safe,
              "license": "https://creativecommons.org/licenses/by/4.0/" if "CC BY" in passport["attribution"]["license"] else passport["attribution"]["license"],
              "creator": {"@type": "Organization", "name": passport["issuer"]}, "temporalCoverage": period, "url": inp.get("canonical_url"),
              "identifier": [{"@type": "PropertyValue", "propertyID": f"{pub} claim receipt", "value": receipt, "url": (inp.get("verify_base") or "") + urllib.parse.quote(receipt)}]}
    keys = sorted({disp} | ({f"{inp['n']:,}"} if isinstance(inp.get("n"), int) else set()))
    gold = {"id": cid, "question": inp.get("question") or f"What was the {inp['metric'].replace('_', ' ')} for {inp['subject']} in {period}?",
            "ground_truth": safe, "key_numbers": keys, "universe": inp.get("universe", ""), "claim_receipt": receipt,
            "fidelity_rubric": {"must_contain": list(contract["required_qualifiers"].values()) + [attribution.split(" analysis")[0]],
                                "must_not_assert": [d["statement"] for d in dne], "grades": "C full / P partial / I wrong-or-forbidden / A clean abstain / N leaky abstain"}}
    return {"compiler": "claim-contract-compiler/0.1", "safe_sentence": safe, "safe_sentence_with_receipt": safe_with_receipt,
            "receipt": receipt, "verify_url": (inp.get("verify_base") or "") + urllib.parse.quote(receipt),
            "passport": passport, "contract": contract, "forbidden_paraphrases": forbidden, "test_vectors": vectors, "jsonld": jsonld, "gold_record": gold,
            "transparency": "Sign the snapshot of {id: value, hash8} with Sigstore in CI and record it in Rekor so receipts verify without you; see spec 7c."}


DEMO = {"publisher": "FRC", "publisher_name": "FinanceRateCalc", "id": "national-fha-denial-rate-2025", "metric": "fha_denial_rate", "value": 0.221, "display_value": "22.1%",
        "unit": "share_of_decisioned_applications", "subject": "United States, all reporting lenders", "period": "2025",
        "definition": "denials (action 3) / decisioned applications (actions 1,2,3), FHA (loan_type 2)", "population": "decisioned FHA applications",
        "program_scope": "FHA only, not all mortgages", "n": 1187606, "source": "CFPB/FFIEC HMDA public record, 2025",
        "canonical_url": "https://financeratecalc.com/claims/national-fha-denial-rate-2025.json", "verify_base": "https://frc-mcp.ziyetis.workers.dev/verify?r=",
        "template": "In {period}, {value} of {population} were denied.", "attribution": "FinanceRateCalc analysis of the public CFPB HMDA 2025 record",
        "corrections": [{"date": "2026-07-26", "from": 0.217, "to": 0.221, "reason": "29,691 reverse-mortgage (HECM) records removed from the universe"}],
        "universe": "U-FHA-2025-DECISIONED", "question": "What percentage of FHA loan applications were denied in 2025?",
        # mirror the live passport's claim object exactly so the demo reproduces the live receipt hash (ebf6b00b)
        "n_in_claim": False, "claim_extra": {"note": "Purchase-only and refinance-only rates differ (\u224812.7% and \u224838.1%); the denominator you choose is the story you tell."}}

if __name__ == "__main__":
    if "--demo" in sys.argv:
        print(json.dumps(compile_claim(DEMO), indent=1, ensure_ascii=False))
    else:
        src = sys.argv[1] if len(sys.argv) > 1 else None
        data = json.load(open(src)) if src else json.load(sys.stdin)
        print(json.dumps(compile_claim(data), indent=1, ensure_ascii=False))
