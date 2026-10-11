#!/usr/bin/env python3
"""Stale Rule Index probe: dated questions about regulatory numbers, graded deterministically against
machine-readable rule files in rules/. Two conditions: no source (what the model carries) and with-rule
(the rule file in the prompt). No model grades anything.

usage: stale_rule_probe.py <model> <base_url> <api_key_env> <out.json> [with_rule 0|1]
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(HERE, "..", "rules")
PRE = "Today is October 2026. "
QUESTIONS = [
    # rule, qid, question, truth, kind
    ("fhfa-conforming-loan-limits-2026", "CL1", "What is the 2026 baseline conforming loan limit for a one-unit property in most of the United States? Answer with the dollar amount first.", 832750, "usd"),
    ("fhfa-conforming-loan-limits-2026", "CL2", "What is the 2026 conforming loan limit ceiling for a one-unit property in high-cost areas of the contiguous US? Dollar amount first.", 1249125, "usd"),
    ("fhfa-conforming-loan-limits-2026", "CL3", "What is the 2026 baseline conforming loan limit for a one-unit property in Alaska? Dollar amount first.", 1249125, "usd"),
    ("fhfa-conforming-loan-limits-2026", "CL4", "What is the 2026 conforming loan limit ceiling for a one-unit property in Hawaii's high-cost areas? Dollar amount first.", 1873675, "usd"),
    ("fhfa-conforming-loan-limits-2026", "CL5", "What was the 2025 baseline conforming loan limit for a one-unit property (the prior year's value)? Dollar amount first.", 806500, "usd"),
    ("fha-forward-loan-limits-2026", "FL1", "For an FHA case number assigned in 2026, what is the one-unit loan limit floor (low-cost areas)? Dollar amount first.", 541287, "usd"),
    ("fha-forward-loan-limits-2026", "FL2", "For an FHA case number assigned in 2026, what is the one-unit loan limit ceiling (high-cost areas)? Dollar amount first.", 1249125, "usd"),
    ("fha-forward-loan-limits-2026", "FL3", "For an FHA case number assigned in 2026, what is the two-unit loan limit floor? Dollar amount first.", 693050, "usd"),
    ("fha-forward-loan-limits-2026", "FL4", "For an FHA case number assigned in 2026, what is the four-unit loan limit ceiling? Dollar amount first.", 2402625, "usd"),
    ("fha-forward-loan-limits-2026", "FL5", "What is the 2026 HECM (FHA reverse mortgage) maximum claim amount? Dollar amount first.", 1249125, "usd"),
    ("cfpb-hoepa-qm-thresholds-2026", "HQ1", "For a loan consummated in 2026, what is the HOEPA total loan amount threshold below which the points-and-fees dollar trigger applies? Dollar amount first.", 27592, "usd"),
    ("cfpb-hoepa-qm-thresholds-2026", "HQ2", "For a loan consummated in 2026, what is the HOEPA points-and-fees dollar trigger? Dollar amount first.", 1380, "usd"),
    ("cfpb-hoepa-qm-thresholds-2026", "HQ3", "For a qualified mortgage consummated in 2026 with a total loan amount of $100,000, what is the maximum points and fees in dollars? Dollar amount first.", 4139, "usd"),
    ("cfpb-hoepa-qm-thresholds-2026", "HQ4", "For a qualified mortgage consummated in 2026 with a total loan amount of $200,000, what is the points-and-fees limit as a percentage of the loan amount? Percentage first.", 3.0, "pct"),
    ("cfpb-hoepa-qm-thresholds-2026", "HQ5", "For a qualified mortgage consummated in 2026 with a total loan amount of $50,000, what is the points-and-fees limit as a percentage of the loan amount? Percentage first.", 5.0, "pct"),
    ("va-funding-fee-2023-04-07", "VA1", "A veteran uses the VA home loan benefit for the first time to buy a home with no down payment, closing in 2026 and not exempt. What is the funding fee percentage? Percentage first.", 2.15, "pct"),
    ("va-funding-fee-2023-04-07", "VA2", "A veteran uses the VA home loan benefit for the second time to buy a home with no down payment, closing in 2026 and not exempt. What is the funding fee percentage? Percentage first.", 3.30, "pct"),
    ("va-funding-fee-2023-04-07", "VA3", "First-use VA purchase loan with a 10% down payment, closing in 2026, not exempt: what is the funding fee percentage? Percentage first.", 1.25, "pct"),
    ("va-funding-fee-2023-04-07", "VA4", "First-use VA purchase loan with a 5% down payment, closing in 2026, not exempt: what is the funding fee percentage? Percentage first.", 1.50, "pct"),
    ("va-funding-fee-2023-04-07", "VA5", "What is the VA funding fee percentage on an Interest Rate Reduction Refinance Loan (IRRRL) closing in 2026 for a non-exempt borrower? Percentage first.", 0.50, "pct"),
    ("fha-annual-mip-ml-2023-05", "MP1", "For an FHA purchase loan with a base loan amount of $300,000, LTV 96.5%, 30-year term, case number assigned this year, what is the annual MIP rate? Percentage first.", 0.55, "pct"),
    ("fha-annual-mip-ml-2023-05", "MP2", "For an FHA purchase loan with a base loan amount of $800,000, LTV 96.5%, 30-year term, case number assigned this year, what is the annual MIP rate? Percentage first.", 0.75, "pct"),
    ("fha-annual-mip-ml-2023-05", "MP3", "For an FHA purchase loan with a base loan amount of $300,000, LTV 85%, 15-year term, case number assigned this year, what is the annual MIP rate? Percentage first.", 0.15, "pct"),
    ("fha-annual-mip-ml-2023-05", "MP4", "For an FHA purchase loan with a base loan amount of $800,000, LTV 95%, 15-year term, case number assigned this year, what is the annual MIP rate? Percentage first.", 0.65, "pct"),
    ("fha-annual-mip-ml-2023-05", "MP5", "What is the FHA upfront mortgage insurance premium rate for a forward purchase loan with a case number assigned this year? Percentage first.", 1.75, "pct"),
]


def ask(model, base_url, key, text):
    body = {"model": model, "messages": [{"role": "user", "content": text}], "temperature": 0, "max_tokens": 400}
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def extract(text, kind, question=""):
    """First dollar amount, or the first percentage under 10% that does not merely restate a percentage
    from the question (down payment, LTV)."""
    if kind == "usd":
        m = re.search(r"\$\s?(\d{1,3}(?:,\d{3})+|\d{4,})", text)
        return float(m.group(1).replace(",", "")) if m else None
    asked = {float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*%", question)}
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*%", text):
        v = float(m.group(1))
        if v < 10 and v not in asked:
            return v
    return None


def grade(answer, truth, kind, question=""):
    v = extract(answer, kind, question)
    tol = 1.0 if kind == "usd" else 0.005
    return {"extracted": v, "correct": v is not None and abs(v - truth) <= tol}


def main(model, base_url, key_env, out, with_rule="0"):
    key = os.environ[key_env]
    with_rule = with_rule == "1"
    rows = []
    for rule, qid, q, truth, kind in QUESTIONS:
        head = ""
        if with_rule:
            with open(os.path.join(RULES, f"{rule}.json"), encoding="utf-8") as fh:
                head = "You have this machine-readable copy of the rule (treat it as the source):\n" + fh.read() + "\n\n"
        text = head + PRE + q
        try:
            ans = ask(model, base_url, key, text)
        except Exception as e:  # noqa: BLE001
            ans = f"[error] {e}"
        rows.append({"rule": rule, "qid": qid, "question": q, "truth": truth, "kind": kind, "answer": ans, **grade(ans, truth, kind, q)})
    by_rule = {}
    for r in rows:
        by_rule.setdefault(r["rule"], [0, 0]); by_rule[r["rule"]][1] += 1; by_rule[r["rule"]][0] += int(r["correct"])
    summary = {"model": model, "condition": "with_rule" if with_rule else "no_source", "n": len(rows),
               "correct": sum(r["correct"] for r in rows), "errors": sum(r["answer"].startswith("[error]") for r in rows),
               "by_rule": {k: f"{a}/{b}" for k, (a, b) in by_rule.items()}}
    with open(out, "w") as fh:
        json.dump({"generated": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "summary": summary, "rows": rows}, fh, indent=1)
    print(json.dumps(summary))


if __name__ == "__main__":
    main(*sys.argv[1:6])
