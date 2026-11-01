#!/usr/bin/env python3
"""A use contract for every receipted claim document that has none.

Until 2026-10-21 only the hand-written passports (national, metro gaps, five legacy claims) had a
companion .contract.json, so check_claim_contract answered "Unknown passport_id" for 200 of the 386
receipted ids (every lender, state and small-loan figure). This writes the missing contracts from
the claim block, with the same shape as the hand-written ones, plus `current_value` so the gate can
tell a sentence that quotes a different figure for the same subject. Idempotent; never overwrites a
contract that exists.
"""
import glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATES = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "the District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "PR": "Puerto Rico", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"}
FORBID = ["causal_attribution", "individual_prediction", "personalized_lender_recommendation", "legal_conclusion"]


def contract_for(cid, d):
    c, v = d["claim"], d["display_value"]
    if cid.startswith("lender-"):
        name = str(c.get("lender", "")).title()
        return {"canonical_claim": {"template": f"In 2025, {name} denied {{value}} of its {c.get('n', 0):,} decisioned FHA applications.", "required_fields": ["period", "population", "nature"]},
                "required_qualifiers": {"period": "2025", "population": f"{name} decisioned FHA applications (actions 1,2,3; loan_type 2; reverse mortgages excluded)", "program_scope": "FHA", "nature": "historical institutional aggregate, unadjusted for applicant mix"},
                "does_not_establish": [f"{name} will deny any specific future application with {v} probability", f"{name} is stricter or more lenient than another lender for a given applicant", f"{name} discriminates or violates law", f"{v} applies to {name}'s non-FHA lending"]}
    if cid.startswith("state-"):
        st = str(c.get("state", "")).upper(); name = STATES.get(st, st)
        return {"canonical_claim": {"template": f"In 2025, {{value}} of decisioned FHA applications in {name} were denied ({c.get('n', 0):,} applications reaching a decision).", "required_fields": ["period", "population", "nature"]},
                "required_qualifiers": {"period": "2025", "population": f"decisioned FHA applications in {name} (actions 1,2,3; loan_type 2)", "program_scope": "FHA", "nature": "historical aggregate"},
                "does_not_establish": [f"an applicant in {name} has a {v} chance of denial", f"{name}'s lenders are stricter than another state's for a given applicant", "any conclusion about non-FHA lending", "any legal conclusion"]}
    if cid.startswith("small-loan-penalty-") and cid != "small-loan-penalty-range-2025":
        st = str(c.get("state", "")).upper(); name = STATES.get(st, st)
        return {"canonical_claim": {"template": f"In 2025, FHA applications under $150,000 in {name} were denied {c.get('small')}% of the time against {c.get('big')}% for loans over $250,000, a small-loan penalty of {{value}}.", "required_fields": ["period", "population", "loan_size_bands"]},
                "required_qualifiers": {"period": "2025", "population": f"decisioned FHA applications in {name}", "program_scope": "FHA", "loan_size_bands": "under $150,000 vs over $250,000"},
                "does_not_establish": ["that loan size causes denial (applicant and property mix differ by loan size)", "any individual's chance of denial", "any legal conclusion"]}
    if cid == "small-loan-penalty-range-2025":
        return {"canonical_claim": {"template": "In 2025, across the US jurisdictions with a published loan-size split, the FHA small-loan penalty (under $150,000 vs over $250,000) ranged over {value}.", "required_fields": ["period", "population", "loan_size_bands"]},
                "required_qualifiers": {"period": "2025", "population": "decisioned FHA applications by state", "program_scope": "FHA", "loan_size_bands": "under $150,000 vs over $250,000"},
                "does_not_establish": ["causation", "any individual's chance of denial"]}
    if cid == "door-effect-38pct-2026":
        return {"canonical_claim": {"template": "In a decomposition of 2025 FHA credit decisions, lender identity was associated with about {value} of the explainable variation in denial outcomes.", "required_fields": ["period", "population", "nature"]},
                "required_qualifiers": {"period": "2025", "population": "decisioned FHA applications (actions 1,2,3; loan_type 2)", "program_scope": "FHA", "nature": "share of explained variation; association, not cause"},
                "does_not_establish": ["that lender choice causes denial", "that any lender is at fault", "any individual's chance of denial"]}
    if cid.startswith("outcome-"):
        base = "applications acted on (actions 1-5: originated, approved but not accepted, denied, withdrawn, closed for incompleteness; purchased loans and preapproval requests excluded; loan_type 2; reverse mortgages excluded)"
        if c.get("metric") == "fha_application_outcome_share":
            word = {"originated": "were originated", "approved_not_accepted": "were approved but not accepted by the applicant", "denied": "were denied", "withdrawn": "were withdrawn by the applicant", "closed_incomplete": "were closed for incompleteness"}[c["outcome"]]
            return {"canonical_claim": {"template": f"In 2025, {{value}} of the {c.get('n', 0):,} FHA applications that lenders acted on {word}.", "required_fields": ["period", "population", "denominator"]},
                    "required_qualifiers": {"period": "2025", "population": "US FHA " + base, "denominator": "applications acted on (actions 1-5), not decisioned applications (actions 1-3): the denied share of acted-on applications is lower than the published denial rate because withdrawn and incomplete files are in this denominator", "program_scope": "FHA"},
                    "does_not_establish": ["why any application ended where it did", "that applicants withdraw because of lender conduct, or that files are closed because of applicant conduct", "any individual applicant's outcome", "a comparison with the denial rate (22.1% of decisioned applications) without restating both denominators"]}
        if c.get("metric") == "fha_approved_not_accepted_share":
            return {"canonical_claim": {"template": f"In 2025, {{value}} of the {c.get('n', 0):,} FHA applications that lenders approved were not accepted by the applicant.", "required_fields": ["period", "population"]},
                    "required_qualifiers": {"period": "2025", "population": "US FHA applications approved by the lender (originated + approved but not accepted; loan_type 2; reverse mortgages excluded)", "program_scope": "FHA"},
                    "does_not_establish": ["why an approved applicant did not proceed (pricing, a competing offer, a withdrawn purchase and reporting practice are not separable here)", "any individual applicant's choice"]}
        name = str(c.get("lender", "")).title()
        return {"canonical_claim": {"template": f"In 2025, {{value}} of the {c.get('n', 0):,} FHA applications {name} acted on ended without a credit decision: {c.get('withdrawn_pct')}% withdrawn by the applicant and {c.get('closed_incomplete_pct')}% closed for incompleteness.", "required_fields": ["period", "population", "nature"]},
                "required_qualifiers": {"period": "2025", "population": f"{name} FHA " + base, "program_scope": "FHA", "nature": "historical institutional aggregate; process, market, applicant pool and reporting practice are not separable in the record"},
                "does_not_establish": [f"that {name}'s process causes applicants to withdraw, or that its applicants cause files to close", f"that {name} is better or worse than another lender for a given applicant", f"{name} discriminates or violates law", "any individual applicant's outcome"]}
    if cid == "denial-reason-shares-top100-2025":
        return {"canonical_claim": {"template": "Across the 100 largest FHA lenders reporting denial reasons in 2025, the reason with the highest median share was {value}.", "required_fields": ["period", "population"]},
                "required_qualifiers": {"period": "2025", "population": "denials by the 100 largest FHA lenders that report reasons", "program_scope": "FHA"},
                "does_not_establish": ["why any specific application was denied", "that a reason is more common at a specific lender without its own figure"]}
    return None


def main():
    written = skipped = 0
    for f in sorted(glob.glob(os.path.join(ROOT, "claims", "*.json"))):
        if f.endswith(".contract.json") or f.endswith("index.json"):
            continue
        d = json.load(open(f, encoding="utf-8"))
        if not d.get("receipt_document"):
            continue
        cid = d["id"]; cp = f[:-5] + ".contract.json"
        if os.path.exists(cp):
            # keep hand-written contracts; add current_value if missing so the gate can check values
            k = json.load(open(cp, encoding="utf-8"))
            if k.get("current_value") != d["display_value"]:
                k["current_value"] = d["display_value"]; json.dump(k, open(cp, "w", encoding="utf-8"), indent=1, ensure_ascii=False); written += 1
            else:
                skipped += 1
            continue
        body = contract_for(cid, d)
        if not body:
            skipped += 1; continue
        k = {"contract_version": "0.1", "passport_id": "frc:claim:" + cid, "current_value": d["display_value"], **body,
             "forbidden_transformations": FORBID, "rule": "Free text is the OUTPUT of evidence, not its input. Certify before you write.",
             "test_vectors": [{"id": "pass-canonical", "proposed_use": {"causal_assertion": False, "individual_prediction": False}, "expected_verdict": "pass"},
                              {"id": "fail-personal", "proposed_use": {"proposed_sentence": "This lender will likely reject YOUR application"}, "expected_verdict": "block", "reason_code": "INDIVIDUAL_PREDICTION_PROHIBITED"}],
             "generated_by": "scripts/build_claim_contracts.py (2026-10-21) from the claim block"}
        json.dump(k, open(cp, "w", encoding="utf-8"), indent=1, ensure_ascii=False); written += 1
    print(f"contracts written/updated {written}, left as they were {skipped}")


if __name__ == "__main__":
    sys.exit(main())
