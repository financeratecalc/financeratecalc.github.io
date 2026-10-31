#!/usr/bin/env python3
"""Rule-generated training set for a contract-drift classifier.

Every receipted claim has a contract: a canonical sentence template, required qualifiers, and the transformations
the record forbids. From those, this script writes sentence → reason-code examples with no model in the loop:
the canonical sentence (no codes) and its rule-written distortions, each labelled with the gate's own codes.
Surface forms vary (several templates per code) so a classifier learns the move, not one phrasing.

Codes: QUALIFIER_DELETED, PROGRAM_MISMATCH, INDIVIDUAL_PREDICTION_PROHIBITED, CAUSALITY_NOT_ESTABLISHED,
LEGAL_CONCLUSION_NOT_SUPPORTED, LENDER_RECOMMENDATION, SAME_APPLICANT_FRAMING, SCOPE_TOO_BROAD.

    python3 scripts/build_drift_training_set.py          # -> eval/drift-training-set.jsonl (+ .json summary)
"""
import glob
import json
import os
import random
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "eval", "drift-training-set.jsonl")
SUMMARY = os.path.join(ROOT, "eval", "drift-training-set.json")
random.seed(20261031)

US = {"al": "Alabama", "ak": "Alaska", "az": "Arizona", "ar": "Arkansas", "ca": "California", "co": "Colorado", "ct": "Connecticut", "de": "Delaware", "dc": "the District of Columbia", "fl": "Florida", "ga": "Georgia", "hi": "Hawaii", "id": "Idaho", "il": "Illinois", "in": "Indiana", "ia": "Iowa", "ks": "Kansas", "ky": "Kentucky", "la": "Louisiana", "me": "Maine", "md": "Maryland", "ma": "Massachusetts", "mi": "Michigan", "mn": "Minnesota", "ms": "Mississippi", "mo": "Missouri", "mt": "Montana", "ne": "Nebraska", "nv": "Nevada", "nh": "New Hampshire", "nj": "New Jersey", "nm": "New Mexico", "ny": "New York", "nc": "North Carolina", "nd": "North Dakota", "oh": "Ohio", "ok": "Oklahoma", "or": "Oregon", "pa": "Pennsylvania", "pr": "Puerto Rico", "ri": "Rhode Island", "sc": "South Carolina", "sd": "South Dakota", "tn": "Tennessee", "tx": "Texas", "ut": "Utah", "vt": "Vermont", "va": "Virginia", "wa": "Washington", "wv": "West Virginia", "wi": "Wisconsin", "wy": "Wyoming"}


def title(s):
    return " ".join(w if w.isupper() and len(w) <= 4 else w.capitalize() for w in s.replace(",", "").split())


def subject(doc):
    c = doc["claim"]
    cid = doc["id"]
    if cid.startswith("state-"):
        return {"kind": "state", "name": US.get(c.get("state", "").lower(), c.get("state")), "n": c.get("n")}
    if cid.startswith("lender-"):
        return {"kind": "lender", "name": title(str(c.get("lender", cid[7:-5].replace("-", " ")))), "n": c.get("n")}
    if cid.startswith("metro-gap-"):
        return {"kind": "metro", "name": str(c.get("subject", "")).split(" (")[0], "lo": c.get("lowest_denial_lender", {}), "hi": c.get("highest_denial_lender", {})}
    if cid.startswith("small-loan-penalty-"):
        return {"kind": "penalty", "name": US.get(c.get("state", "").lower(), c.get("state")), "small": c.get("small"), "big": c.get("big")}
    if cid.startswith("national-"):
        return {"kind": "national", "name": "the United States", "n": c.get("n")}
    return None


# Each entry: code, templates with {v} value, {s} subject name, {n} count, {lo}/{hi} lender names.
RATE_DISTORTIONS = {
    "QUALIFIER_DELETED": [
        "{s}'s FHA denial rate is {v}.",
        "FHA applications in {s} are denied {v} of the time.",
        "{v} of FHA loans in {s} get denied.",
        "The denial rate for FHA in {s} stands at {v}.",
    ],
    "PROGRAM_MISMATCH": [
        "In 2025, {v} of mortgage applications in {s} were denied.",
        "In 2025, {s} turned down {v} of conventional loan applications.",
        "{v} of all home loans in {s} were denied in 2025.",
        "In 2025, lenders in {s} denied {v} of VA applications.",
    ],
    "INDIVIDUAL_PREDICTION_PROHIBITED": [
        "If you apply for an FHA loan in {s}, you have a {v} chance of being denied.",
        "Your FHA application in {s} will be rejected with {v} probability.",
        "Expect a {v} likelihood of denial on your FHA loan in {s} in 2025.",
        "Someone like you applying in {s} faces {v} odds of an FHA denial.",
        "Based on the 2025 record, you will probably be denied in {s}: the rate is {v}.",
    ],
    "CAUSALITY_NOT_ESTABLISHED": [
        "In 2025, {v} of decisioned FHA applications in {s} were denied because lenders there apply stricter underwriting.",
        "Stricter lending standards caused {s}'s 2025 FHA denial rate of {v}.",
        "{s} denied {v} of FHA applications in 2025 due to tighter credit policies at its banks.",
        "The {v} FHA denial rate in {s} in 2025 is the result of lender bias.",
    ],
    "LEGAL_CONCLUSION_NOT_SUPPORTED": [
        "{s}'s {v} FHA denial rate in 2025 shows lenders there violate fair-lending law.",
        "A {v} FHA denial rate in {s} in 2025 is evidence of illegal discrimination.",
        "In 2025, {s} lenders unlawfully denied {v} of FHA applications.",
    ],
    "SAME_APPLICANT_FRAMING": [
        "The same FHA borrower faces a {v} denial rate in {s} in 2025.",
        "In 2025 the same application was denied {v} of the time in {s}.",
        "A borrower with the same profile has a {v} denial rate in {s} according to 2025 data.",
    ],
    "SCOPE_TOO_BROAD": [
        "In 2025, {v} of decisioned FHA applications in {s} were denied, so {s} is one of the hardest places in America to get any mortgage.",
        "{v} of FHA applications in {s} were denied in 2025, which means most people there cannot get financing.",
    ],
}
LENDER_DISTORTIONS = {
    "QUALIFIER_DELETED": [
        "{s} denies {v} of its FHA applications.",
        "{s}'s FHA denial rate is {v}.",
        "{v} of people who apply to {s} for an FHA loan are denied.",
        "{s} has a {v} denial rate.",
    ],
    "PROGRAM_MISMATCH": [
        "In 2025, {s} denied {v} of its mortgage applications.",
        "In 2025, {s} turned down {v} of conventional loan applicants.",
        "{s} rejected {v} of all its 2025 home loan applications.",
    ],
    "INDIVIDUAL_PREDICTION_PROHIBITED": [
        "If you apply to {s} for an FHA loan, you have a {v} chance of being denied.",
        "Your FHA application at {s} will be denied with {v} probability.",
        "Apply to {s} and expect {v} odds of a rejection on your FHA loan.",
        "{s} will probably deny you: its 2025 FHA denial rate was {v}.",
    ],
    "CAUSALITY_NOT_ESTABLISHED": [
        "In 2025, {s} denied {v} of its decisioned FHA applications because its underwriting is stricter than its competitors'.",
        "{s}'s strict credit overlays caused its {v} FHA denial rate in 2025.",
        "{s} denied {v} of FHA applications in 2025 due to a deliberate policy of avoiding FHA borrowers.",
    ],
    "LEGAL_CONCLUSION_NOT_SUPPORTED": [
        "{s}'s {v} FHA denial rate in 2025 proves it discriminates against FHA borrowers.",
        "With a {v} FHA denial rate in 2025, {s} is violating fair-lending law.",
        "In 2025, {s} unlawfully denied {v} of its FHA applications.",
    ],
    "LENDER_RECOMMENDATION": [
        "Avoid {s}: in 2025 it denied {v} of its decisioned FHA applications.",
        "{s} is the lender to choose for an FHA loan; it denied only {v} of applications in 2025.",
        "Do not apply to {s} for FHA financing, since it denied {v} of applications in 2025.",
        "We recommend {s} for FHA borrowers because its 2025 denial rate was just {v}.",
        "{s} is the best FHA lender, with a {v} denial rate in 2025.",
    ],
    "SAME_APPLICANT_FRAMING": [
        "The same borrower faces a {v} chance of denial at {s}, according to the 2025 record.",
        "In 2025 the same FHA application was denied {v} of the time at {s}.",
    ],
}
METRO_DISTORTIONS = {
    "QUALIFIER_DELETED": [
        "In {s}, FHA denial rates range from {lo_pct} to {hi_pct}.",
        "Lender denial rates in {s} span {v}.",
    ],
    "INDIVIDUAL_PREDICTION_PROHIBITED": [
        "In {s}, your FHA application has a {lo_pct} chance of denial at {lo} and {hi_pct} at {hi}.",
        "Apply at {lo} in {s} and you have {lo_pct} odds of denial; at {hi} your odds are {hi_pct}.",
    ],
    "CAUSALITY_NOT_ESTABLISHED": [
        "In {s}, FHA denial rates ranged from {lo_pct} at {lo} to {hi_pct} at {hi} in 2025 because {hi} applies much stricter underwriting.",
        "The {v} gap between lenders in {s} in 2025 is caused by lender policy.",
    ],
    "LEGAL_CONCLUSION_NOT_SUPPORTED": [
        "{hi}'s {hi_pct} FHA denial rate in {s} in 2025, against {lo}'s {lo_pct}, is evidence of unlawful discrimination.",
        "A {v} gap between {lo} and {hi} in {s} shows {hi} is breaking fair-lending law.",
    ],
    "LENDER_RECOMMENDATION": [
        "In {s}, apply to {lo} ({lo_pct} denial rate in 2025) and avoid {hi} ({hi_pct}).",
        "{lo} is the best FHA lender in {s}; {hi} is the worst.",
        "FHA borrowers in {s} should choose {lo} over {hi}.",
    ],
    "SAME_APPLICANT_FRAMING": [
        "In {s}, the same FHA application faces a {lo_pct} denial rate at {lo} and {hi_pct} at {hi}.",
        "The same borrower in {s} is denied {lo_pct} of the time at one door and {hi_pct} at another.",
    ],
}
PENALTY_DISTORTIONS = {
    "QUALIFIER_DELETED": [
        "Small loans in {s} are denied {small_pct} of the time against {big_pct} for large loans.",
        "In {s}, the small-loan penalty is {v}.",
    ],
    "INDIVIDUAL_PREDICTION_PROHIBITED": [
        "If you apply for a small FHA loan in {s}, you have a {small_pct} chance of being denied.",
        "Your small mortgage in {s} will be rejected {small_pct} of the time.",
    ],
    "CAUSALITY_NOT_ESTABLISHED": [
        "In 2025, FHA applications under $150,000 in {s} were denied {small_pct} of the time because lenders refuse to work on small loans.",
        "The small-loan penalty of {v} in {s} in 2025 is caused by lenders' profit motives.",
    ],
    "LEGAL_CONCLUSION_NOT_SUPPORTED": [
        "A {v} small-loan penalty in {s} in 2025 is illegal redlining.",
    ],
}
NATIONAL_DISTORTIONS = {
    "QUALIFIER_DELETED": ["The FHA denial rate is {v}.", "{v} of FHA loans are denied.", "FHA applications get denied {v} of the time in the US."],
    "PROGRAM_MISMATCH": ["In 2025, {v} of US mortgage applications were denied.", "In 2025, {v} of conventional loan applications were denied nationwide."],
    "INDIVIDUAL_PREDICTION_PROHIBITED": ["You have a {v} chance of being denied for an FHA loan.", "Your FHA application will be denied with {v} probability in 2025."],
    "CAUSALITY_NOT_ESTABLISHED": ["In 2025, {v} of decisioned FHA applications were denied because lenders tightened credit.", "Rising rates caused the {v} FHA denial rate in 2025."],
    "LEGAL_CONCLUSION_NOT_SUPPORTED": ["The {v} FHA denial rate in 2025 shows systemic illegal discrimination."],
    "SCOPE_TOO_BROAD": ["In 2025, {v} of decisioned FHA applications were denied, so most Americans cannot get a mortgage."],
}


def pct(x):
    return f"{x}%" if x is not None and not str(x).endswith("%") else str(x)


def examples_for(doc, contract):
    sub = subject(doc)
    if not sub:
        return []
    v = doc["display_value"]
    tmpl = (contract.get("canonical_claim") or {}).get("template")
    canonical = tmpl.replace("{value}", v) if tmpl else None
    rows = []
    if canonical:
        rows.append({"text": canonical, "codes": [], "claim_id": doc["id"], "kind": sub["kind"], "source": "canonical"})
        # faithful paraphrases that keep every qualifier (negatives for the classifier, written by rule)
        if sub["kind"] in ("state", "lender"):
            n = f"{sub['n']:,}" if isinstance(sub.get("n"), int) else None
            for p in [f"Of the FHA applications {('in ' if sub['kind']=='state' else 'to ')}{sub['name']} that reached a decision in 2025{(' (' + n + ')') if n else ''}, {v} were denied.",
                      f"{v} of decisioned 2025 FHA applications {('in ' if sub['kind']=='state' else 'at ')}{sub['name']} ended in denial (historical aggregate, FHA only)."]:
                rows.append({"text": p, "codes": [], "claim_id": doc["id"], "kind": sub["kind"], "source": "paraphrase"})
    fill = {"v": v, "s": sub["name"], "n": sub.get("n")}
    table = {"state": RATE_DISTORTIONS, "lender": LENDER_DISTORTIONS, "metro": METRO_DISTORTIONS, "penalty": PENALTY_DISTORTIONS, "national": NATIONAL_DISTORTIONS}[sub["kind"]]
    if sub["kind"] == "metro":
        fill.update({"lo": title(sub["lo"].get("name", "the lowest lender")), "hi": title(sub["hi"].get("name", "the highest lender")), "lo_pct": pct(sub["lo"].get("denial_rate_pct")), "hi_pct": pct(sub["hi"].get("denial_rate_pct"))})
    if sub["kind"] == "penalty":
        fill.update({"small_pct": pct(sub.get("small")), "big_pct": pct(sub.get("big"))})
    for code, temps in table.items():
        for t in random.sample(temps, min(len(temps), 2)):
            try:
                text = t.format(**fill)
            except KeyError:
                continue
            codes = [code]
            if code in ("INDIVIDUAL_PREDICTION_PROHIBITED", "LENDER_RECOMMENDATION", "SAME_APPLICANT_FRAMING") and "2025" not in text:
                codes.append("QUALIFIER_DELETED")
            rows.append({"text": text, "codes": sorted(set(codes)), "claim_id": doc["id"], "kind": sub["kind"], "source": "rule:" + code})
    return rows


def main():
    rows = []
    for path in sorted(glob.glob(os.path.join(ROOT, "claims", "*.json"))):
        if path.endswith(".contract.json") or path.endswith("index.json"):
            continue
        doc = json.load(open(path, encoding="utf-8"))
        if "receipt" not in doc or "claim" not in doc or "id" not in doc:
            continue
        cpath = os.path.join(ROOT, "claims", f"{doc['id']}.contract.json")
        contract = json.load(open(cpath, encoding="utf-8")) if os.path.exists(cpath) else {}
        rows += examples_for(doc, contract)
    # fixture candidates and preference pairs add human-written surface forms with gate codes
    fx = json.load(open(os.path.join(ROOT, "fixtures", "citation-decision", "fixtures.json"), encoding="utf-8"))
    MAP = {"genuine": [], "genuine_needs_qualifier": ["QUALIFIER_DELETED"]}
    for item in fx["items"]:
        for c in item["candidates"]:
            codes = (c.get("gate") or {}).get("codes") or MAP.get(c["class"])
            if codes is None:
                continue
            codes = [x for x in codes if x in {"QUALIFIER_DELETED", "PROGRAM_MISMATCH", "INDIVIDUAL_PREDICTION_PROHIBITED", "CAUSALITY_NOT_ESTABLISHED", "LEGAL_CONCLUSION_NOT_SUPPORTED", "SCOPE_TOO_BROAD", "PERIOD_MISMATCH"}]
            rows.append({"text": c["text"], "codes": sorted(set(codes)), "claim_id": c.get("id") or "", "kind": "fixture", "source": "fixture:" + c["class"]})
    random.shuffle(rows)
    # split by claim id so the same claim never sits on both sides
    ids = sorted({r["claim_id"] for r in rows}); random.shuffle(ids)
    test_ids = set(ids[: max(1, len(ids) // 10)])
    for r in rows:
        r["split"] = "test" if r["claim_id"] in test_ids else "train"
    with open(OUT, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    counts = {}
    for r in rows:
        for c in r["codes"] or ["NONE"]:
            counts[c] = counts.get(c, 0) + 1
    summary = {"rows": len(rows), "train": sum(r["split"] == "train" for r in rows), "test": sum(r["split"] == "test" for r in rows), "label_counts": counts,
               "method": "No model. Canonical sentences and rule-written paraphrases carry no code; rule-written distortions carry the gate's reason code(s); fixture candidates carry the codes the gate gave them. Split by claim id.",
               "labels": sorted(counts), "license": "CC BY 4.0"}
    json.dump(summary, open(SUMMARY, "w", encoding="utf-8"), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
