#!/usr/bin/env python3
"""Build the Hugging Face package for FinanceRateCalc/negative-knowledge
FROM the site's published JSON. Nothing numeric is typed here by hand.

"Negative knowledge": what a publisher has found to be wrong (its own corrections and error
families), what is asserted about it that is not true (atoms), how AI systems misquoted it
(graded misquotes, correction-latency observations) and the grader's failure codes per
question from automated runs, including forged claim receipts.

Inputs (repo root):
  corrections.json                 corrections feed (corrections, error families, atoms)
  eval/misquotes-graded.json       misquote ledger, graded
  eval/correction-latency.json     which systems still carried a corrected value, and when
  eval/rubric-vectors.json         answers a grader must grade as C/P/I/A before its scores count
  eval/runs/*-denial_ai_fidelity*.json   automated runs with a summary block
Outputs (--out DIR): corrections.csv, misquotes.csv, correction_latency.csv, rubric_vectors.csv,
  model_failure_codes.csv, README.md
"""
import argparse
import csv
import glob
import json
import os

ap = argparse.ArgumentParser()
ap.add_argument("--root", default=".")
ap.add_argument("--out", default="hf-negative-knowledge")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
R = a.root


def load(p):
    with open(os.path.join(R, p), encoding="utf-8") as f:
        return json.load(f)


def out(name):
    return open(os.path.join(a.out, name), "w", newline="", encoding="utf-8")


# 1. corrections, error families, atoms
C = load("corrections.json")
with out("corrections.csv") as f:
    w = csv.writer(f)
    w.writerow(["id", "type", "date", "title", "summary", "old_value", "new_value", "claim_ids", "url"])
    for it in C["items"]:
        w.writerow([it.get("id", ""), it.get("type", ""), it.get("date") or "", it.get("title", ""), it.get("summary", ""),
                    it.get("old_value") or "", it.get("new_value") or "", "|".join(it.get("claim_ids") or []), it.get("url", "")])
n_corr = len(C["items"])

# 2. graded misquotes
M = load("eval/misquotes-graded.json")
with out("misquotes.csv") as f:
    w = csv.writer(f)
    w.writerow(["id", "system", "grade", "codes", "quote", "verdict", "found_by", "graded_on", "claim_universe"])
    for g in M["graded"]:
        w.writerow([g["id"], g["system"], g["grade"], "|".join(g.get("codes", [])), g.get("quote", ""), g["verdict"],
                    g.get("found_by", ""), g.get("graded_on", ""), g.get("claim_universe", "")])
n_mq = len(M["graded"])

# 3. correction latency observations
L = load("eval/correction-latency.json")
n_obs = 0
with out("correction_latency.csv") as f:
    w = csv.writer(f)
    w.writerow(["correction_id", "figure", "old", "new", "corrected_on", "system", "condition", "question", "observed", "codes", "note"])
    for c in L["corrections"]:
        for o in c.get("observations", []):
            n_obs += 1
            w.writerow([c["id"], c["figure"], c["old"], c["new"], c["corrected_on"], o["system"], o.get("condition", ""),
                        o.get("question", ""), o.get("observed", ""), "|".join(o.get("codes", [])), o.get("note", "")])

# 4. rubric vectors
V = load("eval/rubric-vectors.json")
with out("rubric_vectors.csv") as f:
    w = csv.writer(f)
    w.writerow(["id", "question", "ground_truth", "universe", "answer", "expected_grade", "why"])
    for v in V["vectors"]:
        w.writerow([v["id"], V["question"], V["ground_truth"], V["universe"], v["answer"], v["expected"], v["why"]])

# 5. failure codes per question from automated runs (summary blocks only)
n_runs = 0
forged = 0
with out("model_failure_codes.csv") as f:
    w = csv.writer(f)
    w.writerow(["run", "model", "grader", "condition", "design", "question_id", "grades", "value", "consistent", "codes"])
    for p in sorted(glob.glob(os.path.join(R, "eval/runs/*-denial_ai_fidelity*.json"))):
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        s = d.get("summary")
        if not s or "questions" not in s:
            continue
        n_runs += 1
        forged += int(str(s.get("code_frequency", {}).get("FABRICATED_RECEIPT", "0/0")).split("/")[0])
        for qid, q in s["questions"].items():
            w.writerow([s["run"], s["model"], s.get("grader", ""), s["condition"], s["design"], qid, "|".join(str(g) for g in q.get("grades", [])),
                        q.get("value", ""), q.get("consistent", ""), "|".join(str(c) for c in q.get("codes", []))])

README = f"""---
license: cc-by-4.0
language:
- en
tags:
- llm-evaluation
- hallucination
- finance
- mortgage
- corrections
pretty_name: FinanceRateCalc negative knowledge
---

# Negative knowledge: a publisher's own errors, the false claims made about it, and how AI systems misquote it

Most evaluation datasets hold what is true. This one holds what was found to be **wrong**, by whom, and with which code:

| file | rows | what |
|---|---|---|
| `corrections.csv` | {n_corr} | the publisher's complete corrections feed: `correction` (a figure changed), `error_family` (a class of error in the publishing pipeline, found and logged by the publisher), `atom` (a claim about the publisher that is **not** true, written down so answer engines can check it) |
| `misquotes.csv` | {n_mq} | real AI answers quoting the publisher, graded against the figure's claim contract with failure codes |
| `correction_latency.csv` | {n_obs} | after a published correction, which systems still carried the old value, when, and under which code |
| `rubric_vectors.csv` | {len(V["vectors"])} | five answers to one question that any grader must grade as C / P / I / A before its fidelity scores are comparable |
| `model_failure_codes.csv` | {n_runs} runs | per-question grades and failure codes from automated administrations of the Denial-AI benchmark (12 questions x 3 repeats), including `FABRICATED_RECEIPT` ({forged} answers across runs wrote a receipt-shaped string the tool never returned) |

The same failure codes grade the publisher and the models. The error families in `corrections.csv` are the publisher's; the codes in
`misquotes.csv` and `model_failure_codes.csv` are applied to AI systems; several entries show the same stale value on both sides on the same day.

## Why this exists
A grader that has only seen correct answers cannot tell a right number with a wrong denominator from a complete one, and cannot tell a
stale value from a current one. The `atom` rows are negative ground truth: "the claim that the national FHA denial rate is 21.7%" is a
sentence that is false now and was true before 2026-07-26; a system that asserts it is carrying a corrected value.

## Provenance
Built by `scripts/build_hf_negative_knowledge.py` in https://github.com/financeratecalc/financeratecalc.github.io from the site's
published JSON (`corrections.json`, `eval/misquotes-graded.json`, `eval/correction-latency.json`, `eval/rubric-vectors.json`,
`eval/runs/`). Human-readable: https://financeratecalc.com/corrections.html , https://financeratecalc.com/misquotes.html ,
https://financeratecalc.com/verdict-automated.html . Rubric and codes: https://financeratecalc.com/spec/claim-contract-1.0-draft.md .
Worked grading example: https://financeratecalc.com/samples/scoring-a-correct-number.html

## Limits
One publisher, one domain (US FHA mortgage statistics from the 2025 HMDA record), a handful of systems, 2026-07 to 2026-10. Grades in
`model_failure_codes.csv` are produced by a model grader calibrated on `rubric_vectors.csv`; grades in `misquotes.csv` are the
publisher's own. Rows are appended, never deleted. Nothing here is advice about any loan.

License CC BY 4.0. Publisher: FinanceRateCalc (Ziya Yetiş).
"""
with open(os.path.join(a.out, "README.md"), "w", encoding="utf-8") as f:
    f.write(README)
print("built:", sorted(os.listdir(a.out)), "corrections", n_corr, "misquotes", n_mq, "latency obs", n_obs, "runs", n_runs, "forged", forged)
