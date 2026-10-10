#!/usr/bin/env python3
"""Stale-rule probe: do models quote the FHA annual MIP rate that HUD replaced in March 2023?

Ten questions with explicit 2025/2026 case dates; each has one correct rate under HUD Mortgagee
Letter 2023-05 (threshold $726,200). Grading is deterministic: the first percentage/bps figure in
the answer is compared with the truth; the answer is also flagged if it carries a pre-2023 rate
(0.80/0.85/1.00/1.05) and whether it names the 2023 change. No model grades anything here.

usage: mip_stale_probe.py <model> <base_url> <api_key_env> <out.json> [with_rule 0|1]
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.request

QUESTIONS = [
    ("Q01", 300_000, 96.5, 30, 0.55), ("Q02", 300_000, 90.0, 30, 0.50), ("Q03", 300_000, 94.0, 30, 0.50),
    ("Q04", 800_000, 96.5, 30, 0.75), ("Q05", 800_000, 92.0, 30, 0.70), ("Q06", 300_000, 96.5, 15, 0.40),
    ("Q07", 300_000, 85.0, 15, 0.15), ("Q08", 800_000, 95.0, 15, 0.65), ("Q09", 800_000, 80.0, 15, 0.40),
    ("Q10", 800_000, 75.0, 15, 0.15),
]
STALE = {0.80, 0.85, 1.00, 1.05, 0.45, 0.70, 0.95}  # pre-2023 annual MIP cells (0.70/0.95 overlap post-2023 for >726,200; handled below)


RULE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rules", "fha-annual-mip-ml-2023-05.json")


def prompt(amount, ltv, term, with_rule=False):
    head = ""
    if with_rule:
        with open(RULE_PATH, encoding="utf-8") as fh:
            head = ("You have this machine-readable copy of the rule (treat it as the source):\n" + fh.read() + "\n\n")
    return head + (f"Today is October 2026. For an FHA purchase loan with a base loan amount of ${amount:,}, a loan-to-value "
            f"ratio of {ltv}% and a {term}-year term, with the FHA case number assigned this year, what is the annual "
            "mortgage insurance premium (MIP) rate? Answer first with the rate as a percentage of the loan amount "
            "(for example 0.00%), then name the HUD policy document that sets it.")


def ask(model, base_url, key, text):
    body = {"model": model, "messages": [{"role": "user", "content": text}], "temperature": 0, "max_tokens": 400}
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    return d["choices"][0]["message"]["content"]


def first_rate(text, ltv=None):
    """The rate the answer gives: the first percentage that is not the question's LTV and is below 2%
    (MIP rates are 0.15–1.05%; LTVs restated in the answer are 75–96.5%)."""
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*%", text):
        v = float(m.group(1))
        if v < 2.0 and (ltv is None or abs(v - ltv) > 0.01):
            return v
    m = re.search(r"(\d+)\s*(?:bps|basis points)", text, re.IGNORECASE)
    return float(m.group(1)) / 100 if m else None


def grade(answer, truth, ltv=None):
    r = first_rate(answer, ltv)
    rates = {float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*%", answer)}
    return {"first_rate": r, "correct": r is not None and abs(r - truth) < 0.005,
            "stale_rate_present": bool({0.80, 0.85, 1.00, 1.05, 0.45} & rates),
            "mentions_2023_change": bool(re.search(r"2023", answer)),
            "mentions_ml_2023_05": bool(re.search(r"2023[- ]0?5", answer))}


def main(model, base_url, key_env, out, with_rule="0"):
    key = os.environ[key_env]
    with_rule = with_rule == "1"
    rows = []
    for qid, amount, ltv, term, truth in QUESTIONS:
        text = prompt(amount, ltv, term, with_rule)
        try:
            ans = ask(model, base_url, key, text)
        except Exception as e:  # noqa: BLE001 - record the failure, keep probing
            ans = f"[error] {e}"
        rows.append({"qid": qid, "amount": amount, "ltv": ltv, "term": term, "truth": truth, "question": text,
                     "answer": ans, **grade(ans, truth, ltv)})
    summary = {"model": model, "condition": "with_rule" if with_rule else "no_source", "n": len(rows), "correct": sum(r["correct"] for r in rows),
               "stale_rate_present": sum(r["stale_rate_present"] for r in rows),
               "mentions_2023_change": sum(r["mentions_2023_change"] for r in rows),
               "errors": sum(r["answer"].startswith("[error]") for r in rows)}
    with open(out, "w") as fh:
        json.dump({"generated": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "purpose": __doc__.strip().splitlines()[0],
                   "truth_source": "HUD Mortgagee Letter 2023-05 (effective 2023-03-20), base-loan threshold $726,200",
                   "summary": summary, "rows": rows}, fh, indent=1)
    print(json.dumps(summary))


if __name__ == "__main__":
    main(*sys.argv[1:6])
