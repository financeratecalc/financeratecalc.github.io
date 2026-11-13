#!/usr/bin/env python3
"""Edition-aware and denominator-aware question set, generated from the receipted figures.

    python3 scripts/build_edition_qa.py [--check] [--selftest]

Every item is a question whose correct answer depends on WHICH EDITION of an official report is meant, or on WHICH
DENOMINATOR a rate uses. The answers are not written here: each is read from data/official/*.json (figures as printed,
with the document's SHA-256) or data/purpose/*.json (one pass over the CFPB HMDA file), and every item carries the
receipt of the figure it tests. Items about an edition are born when the publisher releases that edition, so they
postdate any model trained before it.

Scoring is deterministic (score() below; no model): the stated number must match, the required context must be present,
and a superseded number given as current fails.

Output (also mirrored for Hugging Face / Kaggle): data/hf-mirrors/edition-aware-qa/{edition_aware_qa.jsonl,.csv,README.md}"""
import csv
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "hf-mirrors", "edition-aware-qa")
BASES = {"decisioned": "applications that reached a credit decision (originated, approved but not accepted, or denied)",
         "acted_on": "all applications acted on (including withdrawn and incomplete files)",
         "denied_plus_originated": "denied plus originated applications only"}
PURPOSE = {"all": "", "purchase": "home-purchase ", "refinance_all": "refinance (including cash-out) "}


def claim(cid):
    p = os.path.join(ROOT, "claims", cid + ".json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def fmt(v):
    return f"{v:,}" if isinstance(v, int) else (f"{v:,.2f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v))


def items():
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "official", "*.json"))):
        if os.path.basename(f) == "index.json":
            continue
        d = json.load(open(f, encoding="utf-8")); doc = d["document"]
        for fid, x in d["figures"].items():
            cid = f"official-{d['source_id']}-{d['period']}-{fid}"; c = claim(cid)
            if not c:
                continue
            base = {"source": doc["title"], "publisher": doc["publisher"].split(",")[0], "edition": doc["edition"], "document_sha256": doc["sha256"], "document_url": doc.get("url"),
                    "figure": x["description"], "period": x["period"], "unit": x["unit"], "receipt": c["receipt"], "claim_url": f"https://financeratecalc.com/claims/{cid}.json"}
            out.append({**base, "id": f"asprinted-{cid}", "kind": "as_printed",
                        "question": f"According to the {doc['title']}, {doc['edition']}, what was the figure for {x['description']} for {x['period']}?",
                        "answer": fmt(x["value"]), "accept_values": [x["value"]], "must_mention": [], "superseded_values": [],
                        "note": "The answer is the figure as printed in the named edition."})
            if x.get("revised_to") is not None:
                out.append({**base, "id": f"revised-{cid}", "kind": "revised_between_editions",
                            "question": f"What figure did the {doc['title']} print for {x['description']} for {x['period']}, and did a later edition print a different value?",
                            "answer": f"{fmt(x['value'])} in the {doc['edition']}; {fmt(x['revised_to'])} in the {x['revised_in']}.",
                            "accept_values": [x["value"], x["revised_to"]], "must_mention": ["both_values"], "superseded_values": [],
                            "note": "Both values must be given. Either number alone is incomplete."})
                out.append({**base, "id": f"current-{cid}", "kind": "latest_edition_value",
                            "question": f"What is the most recently published figure for {x['description']} for {x['period']} in the {doc['title']}?",
                            "answer": f"{fmt(x['revised_to'])} ({x['revised_in']}).", "accept_values": [x["revised_to"]], "must_mention": [], "superseded_values": [x["value"]],
                            "note": f"The first-printed value {fmt(x['value'])} was replaced in the {x['revised_in']}; giving it as current fails."})
            elif str(x.get("revision", "")).startswith("unchanged"):
                out.append({**base, "id": f"stable-{cid}", "kind": "unchanged_between_editions",
                            "question": f"The {doc['title']}, {doc['edition']}, printed {fmt(x['value'])} for {x['description']} for {x['period']}. Did the next edition on file print a different value?",
                            "answer": f"No. {x['revision'][0].upper() + x['revision'][1:]}.", "accept_values": [x["value"]], "must_mention": ["no_change"], "superseded_values": [],
                            "note": "The next edition restates the same value."})
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "purpose", "*-2025.json"))):
        d = json.load(open(f, encoding="utf-8")); P = d["program"]; pid = d["program_id"]
        sha = (d["input"].get("sha256") or "")
        for pk, pw in PURPOSE.items():
            c = d["cells"].get(pk + "|all")
            if not c:
                continue
            rc = claim({"all": "national-fha-denial-rate-2025" if pid == "fha" else f"{pid}-national-denial-rate-2025", "purchase": f"purpose-{pid}-purchase-denial-rate-2025", "refinance_all": f"purpose-{pid}-refinance-denial-rate-2025"}[pk])
            for bk, bw in BASES.items():
                v = c["rate_pct"][bk]
                out.append({"source": "CFPB HMDA 2025 public loan-level file", "publisher": "FinanceRateCalc (computed)", "edition": "2025 file", "document_sha256": sha, "document_url": d["input"].get("url"),
                            "figure": f"{P} {pw}denial rate, denominator: {bk}", "period": "2025", "unit": "percent", "receipt": rc["receipt"] if (rc and bk == "decisioned") else None,
                            "claim_url": f"https://financeratecalc.com/claims/{rc['id']}.json" if (rc and bk == "decisioned") else "https://financeratecalc.com/denominator-map.html",
                            "id": f"denominator-{pid}-{pk}-{bk}", "kind": "denominator_specified",
                            "question": f"In the 2025 HMDA data, what share of {P} {pw}mortgage applications were denied, counting as the denominator {bw}?",
                            "answer": f"{v:.1f}% ({c['denied']:,} denials).", "accept_values": [round(v, 1), v], "must_mention": [], "superseded_values": [],
                            "note": "Same denials, different denominator: the other two bases give different rates."})
        a = d["cells"]["all|all"]; pu = d["cells"]["purchase|all"]; rf = d["cells"]["refinance_all|all"]
        out.append({"source": "CFPB HMDA 2025 public loan-level file", "publisher": "FinanceRateCalc (computed)", "edition": "2025 file", "document_sha256": sha, "document_url": d["input"].get("url"),
                    "figure": f"{P} denial rate, underspecified", "period": "2025", "unit": "percent", "receipt": None, "claim_url": "https://financeratecalc.com/denominator-map.html",
                    "id": f"underspecified-{pid}", "kind": "underspecified_rate",
                    "question": f"What was the {P} mortgage denial rate in 2025?",
                    "answer": f"It depends on loan purpose and denominator: {a['rate_pct']['decisioned']:.1f}% of all decisioned applications, {pu['rate_pct']['decisioned']:.1f}% for home purchase, {rf['rate_pct']['decisioned']:.1f}% for refinance.",
                    "accept_values": [round(a["rate_pct"]["decisioned"], 1), round(pu["rate_pct"]["decisioned"], 1), round(rf["rate_pct"]["decisioned"], 1)], "must_mention": ["denominator_or_purpose"], "superseded_values": [],
                    "note": "A single number without its loan purpose or denominator is incomplete; any of the listed rates is acceptable only when its definition is stated."})
    return out


NUM = re.compile(r"(?<![\w.])\$?(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)")


def numbers(text):
    return [float(m.replace(",", "")) for m in NUM.findall(text)]


def has(text, v):
    tol = 0.051 if (isinstance(v, float) and v < 100) else max(0.5, abs(v) * 1e-9)
    return any(abs(n - float(v)) <= tol for n in numbers(text))


def score(answer_text, item):
    """Deterministic: 1.0 correct and complete, 0.5 right number but required context missing, 0.0 otherwise."""
    t = answer_text
    if item["superseded_values"] and any(has(t, v) for v in item["superseded_values"]) and not any(has(t, v) for v in item["accept_values"]):
        return 0.0
    mm = item["must_mention"]
    if "both_values" in mm:
        n = sum(1 for v in item["accept_values"] if has(t, v))
        return 1.0 if n == 2 else (0.5 if n == 1 else 0.0)
    if "no_change" in mm:
        return 1.0 if re.search(r"\b(no|not|unchanged|same|did not|didn't)\b", t, re.I) and not re.search(r"\b(yes|was revised|changed to|different value was)\b", t, re.I) else 0.0
    if not any(has(t, v) for v in item["accept_values"]):
        return 0.0
    if "denominator_or_purpose" in mm:
        return 1.0 if re.search(r"decision|acted on|purchase|refinanc|denominator|depends", t, re.I) else 0.5
    return 1.0


FIELDS = ["id", "kind", "question", "answer", "source", "publisher", "edition", "period", "figure", "unit", "accept_values", "must_mention", "superseded_values", "receipt", "claim_url", "document_url", "document_sha256", "note"]


def readme(its):
    from collections import Counter
    k = Counter(i["kind"] for i in its)
    return f"""---
license: cc-by-4.0
task_categories:
- question-answering
language:
- en
tags:
- evaluation
- grounding
- provenance
- official-statistics
- finance
pretty_name: Edition-Aware QA (receipted figures from US public records)
size_categories:
- n<1K
---

# Edition-Aware QA: questions whose answer depends on the edition or the denominator

{len(its)} questions generated from figures that carry verifiable receipts at financeratecalc.com. Two things make a number wrong without being invented: the publisher printed a different value in a later edition, or the rate was computed on a different denominator. Each item tests one of them.

| Kind | Items | What it tests |
|---|---|---|
| as_printed | {k['as_printed']} | the figure as printed in a named edition of an official report |
| revised_between_editions | {k['revised_between_editions']} | a figure two editions print differently; both values required |
| latest_edition_value | {k['latest_edition_value']} | the later value; the first-printed value given as current fails |
| unchanged_between_editions | {k['unchanged_between_editions']} | a figure the next edition restates unchanged |
| denominator_specified | {k['denominator_specified']} | one program and year, three denominators, three loan purposes |
| underspecified_rate | {k['underspecified_rate']} | "the denial rate" asked without a definition; a bare number is incomplete |

## Why it is hard to contaminate

Items about an official edition are generated when the publisher releases it (monthly), from the document itself. An item about the September report cannot be in the training data of a model trained before that report existed. The set grows with each edition; the generating script and every source file are public.

## Scoring

Deterministic, no model: `scripts/build_edition_qa.py::score(answer_text, item)` in the publisher's repository. 1.0 = correct and complete; 0.5 = right number, required context missing; 0.0 = wrong, or a superseded value given as current.

## Sources and limits

Official figures are copied as printed from HUD's FHA Single Family Production Report, Ginnie Mae's monthly Issuance Summary and SBA's 7(a) and 504 activity file (US federal publications, public domain), each bound to the SHA-256 of its document. Rates are computed from the public CFPB HMDA 2025 loan-level file. The set does not establish why a publisher changed a figure, and a revision is not an error. Nothing here predicts any individual application or ranks any lender.

Verify any receipt: https://financeratecalc.com/verify.html. Revision ledger: https://financeratecalc.com/revision-ledger.html. Denominator map: https://financeratecalc.com/denominator-map.html. Licence: CC BY 4.0 (the official figures themselves are public domain).
"""


def main():
    its = items()
    if "--selftest" in sys.argv:
        ok = all(score(i["answer"], i) == 1.0 for i in its)
        bad = [i["id"] for i in its if score(i["answer"], i) != 1.0]
        rev = [i for i in its if i["kind"] == "latest_edition_value"]
        stale = all(score(f"It was {fmt(i['superseded_values'][0])}.", i) == 0.0 for i in rev)
        und = [i for i in its if i["kind"] == "underspecified_rate"]
        half = all(score(f"The rate was {i['accept_values'][0]}%.", i) == 0.5 for i in und)
        print(f"selftest: reference answers score 1.0: {ok} {bad[:3]}; superseded value fails: {stale}; bare number on underspecified question scores 0.5: {half}")
        sys.exit(0 if ok and stale and half else 1)
    os.makedirs(OUT, exist_ok=True)
    jl = "\n".join(json.dumps({k: i.get(k) for k in FIELDS}, ensure_ascii=False) for i in its) + "\n"
    files = {"edition_aware_qa.jsonl": jl, "README.md": readme(its)}
    import io
    b = io.StringIO(); w = csv.writer(b, lineterminator="\n"); w.writerow(FIELDS)
    for i in its:
        w.writerow([json.dumps(i[k], ensure_ascii=False) if isinstance(i.get(k), list) else ("" if i.get(k) is None else i[k]) for k in FIELDS])
    files["edition_aware_qa.csv"] = b.getvalue()
    if "--check" in sys.argv:
        stale = [n for n, c in files.items() if not os.path.exists(os.path.join(OUT, n)) or open(os.path.join(OUT, n), encoding="utf-8").read() != c]
        print("edition QA:", "current" if not stale else f"STALE {stale}"); sys.exit(1 if stale else 0)
    for n, c in files.items():
        open(os.path.join(OUT, n), "w", encoding="utf-8").write(c)
    from collections import Counter
    print(f"wrote {len(its)} items: {dict(Counter(i['kind'] for i in its))}")


if __name__ == "__main__":
    main()
