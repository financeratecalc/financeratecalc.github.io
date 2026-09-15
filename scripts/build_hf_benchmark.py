#!/usr/bin/env python3
"""Build the Hugging Face package for FinanceRateCalc/denial-ai-benchmark
FROM the site's published JSON. Nothing numeric is typed here by hand.

Inputs (repo root):
  benchmark.json           instrument v1.2: 12 frozen questions + ground truths + July scores
  benchmark-2026-09.json   September 15 Verdict Day results (8 systems)
Outputs (--out DIR):
  denial_ai_benchmark_v1_3.csv, results_2026-07.csv, results_2026-09.csv, README.md
Upload: huggingface-cli upload FinanceRateCalc/denial-ai-benchmark DIR . --repo-type dataset
"""
import csv, json, sys, os, argparse

ap = argparse.ArgumentParser()
ap.add_argument("--root", default=".")
ap.add_argument("--out", default="hf-denial-ai-benchmark")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

B = json.load(open(os.path.join(a.root, "benchmark.json")))
S = json.load(open(os.path.join(a.root, "benchmark-2026-09.json")))
assert B["version"] in ("1.2", "1.3"), B["version"]
assert S["battery_version"] == "benchmark-v1.2", S["battery_version"]

# 1. instrument
with open(os.path.join(a.out, "denial_ai_benchmark_v1_3.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["id", "question", "ground_truth", "answer_type", "source"])
    for q in B["questions"]:
        w.writerow([q["id"], q["question"], q["ground_truth"], q.get("answer_type", ""), q.get("source", "")])

# 2. July administration (scores embedded per question)
with open(os.path.join(a.out, "results_2026-07.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["administration", "system", "question_id", "grade", "points"])
    for q in B["questions"]:
        for sysname, sc in q.get("scores", {}).items():
            w.writerow([B["administration"], sysname, q["id"], sc["grade"], sc["points"]])

# 3. September administration
with open(os.path.join(a.out, "results_2026-09.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["administration", "system", "condition", "question_id", "grade", "fidelity", "failure_codes", "note"])
    for sysname, r in S["results"].items():
        for qid, ans in r["answers"].items():
            w.writerow([S["administration"], sysname, r["condition"], qid, ans["grade"], ans.get("fidelity", ""), "|".join(ans.get("failure_codes", [])), ans.get("note", "")])

# 4. README (dataset card)
rub = "\n".join(f"- **{k}** ({v['points']} pts) — {v['criterion']}" for k, v in B["rubric"].items() if k != "note")
july = "\n".join(f"| {s['name']} | {s['total_points']}/{s['max_points']} | {s['score']:.3f} | {s['notes']} |" for s in B["systems_tested"])
sept = "\n".join(
    f"| {name} | {r['condition']} | {r['grade_points']}/{r['grade_max']} | {r['fidelity_points']}/{r['fidelity_max']} | {r['overall_score']} | {r['letter']} |"
    for name, r in S["summary"].items())
qs = "\n".join(f"| {q['id']} | {q['question']} | {q['ground_truth']} |" for q in B["questions"])
pe = S["publisher_error_found"]
ctrl = B["control_condition"]
findings = "\n".join(f"- {x}" for x in B["findings"])

README = f"""---
license: cc-by-4.0
language:
- en
tags:
- benchmark
- llm-evaluation
- finance
- mortgage
- fha
- hmda
- fair-lending
pretty_name: The Denial-AI Benchmark (v{B['version']})
size_categories:
- n<1K
configs:
- config_name: instrument
  data_files: denial_ai_benchmark_v1_3.csv
  default: true
- config_name: results_2026_07
  data_files: results_2026-07.csv
- config_name: results_2026_09
  data_files: results_2026-09.csv
---

# The Denial-AI Benchmark (v{B['version']}, frozen)

Twelve fixed questions about {B['domain']}, each with a ground truth computed from the complete 2025 federal HMDA record
(FHA credit decisions, reverse mortgages excluded; universe and filters at https://financeratecalc.com/methodology.html)
and a source where the figure is published and reproducible.

The questions are frozen; re-administration measures improvement or drift. Instrument license: {B['instrument_license']}.
Latest administration: **{S['administration']}** (Verdict Day, protocol {S['protocol_version']}). Live scorecard: https://financeratecalc.com/verdict-2026-09.html

**This card and every file in it are generated from the site's published JSON** (`benchmark.json`, `benchmark-2026-09.json`)
by `scripts/build_hf_benchmark.py`. If a figure here disagrees with the site, the site is canonical and this mirror is stale — please open a discussion.

## Files

| file | config | contents |
|---|---|---|
| `denial_ai_benchmark_v1_3.csv` | `instrument` | id, question, ground_truth, answer_type, source |
| `results_2026-07.csv` | `results_2026_07` | per-system, per-question grade and points, {B['administration']} administration |
| `results_2026-09.csv` | `results_2026_09` | per-system, per-question grade, fidelity and failure codes, {S['administration']} administration |

## Questions and ground truths

| id | question | ground truth |
|---|---|---|
{qs}

## Scoring rubric

{rub}

{B['rubric']['note']}

## Administration {B['administration']} (four systems, clean session)

| system | points | score | notes |
|---|---|---|---|
{july}

Control condition — {ctrl['name']}: {ctrl['correct']}/{ctrl['total']}. {ctrl['note']}

### Findings

{findings}

## Administration {S['administration']} (Verdict Day, eight systems)

{S['scope_note']}

| system | condition | grade points | fidelity | overall | letter |
|---|---|---|---|---|---|
{sept}

Batched-context rows are not comparable with clean-session rows and are never averaged with them.

**Publisher error found during this run.** {pe['what']} How found: {pe['how_found']} Grading consequence: {pe['grading_consequence']} Fixed: {pe['fixed']}

## Intended use

Evaluate factual accuracy of LLMs and assistants on *observed* lending behaviour (as opposed to regulatory rule text).
Models that learn the public record will pass — that is the point. Not for individual approval predictions, lender recommendations, or any conduct or discrimination conclusion.

## Provenance

- Ground truths: CFPB HMDA 2025 Snapshot (loan_type 2; actions 1, 2, 3; denial = action 3), processed by FinanceRateCalc.
- Data archive (DOI): https://doi.org/10.5281/zenodo.21575105
- Corrections log: https://financeratecalc.com/corrections.html
- How to reproduce any figure: https://financeratecalc.com/reconciliation.html
- Machine access: https://financeratecalc.com/mcp-server.html (MCP, 12 tools) and https://financeratecalc.com/llms.txt

## Citation

Benchmark paper:

```bibtex
@article{{yetis2026benchmark,
  author  = {{Yeti{{\\c{{s}}}}, Ziya}},
  title   = {{A Public Benchmark for Consumer Mortgage AI Accuracy: Frozen Questions, Federal Ground Truth, and a Seven-System Failure Taxonomy}},
  journal = {{SSRN Working Paper}},
  year    = {{2026}},
  doi     = {{10.2139/ssrn.7156938}},
  url     = {{https://doi.org/10.2139/ssrn.7156938}}
}}
```

Dataset:

```bibtex
@dataset{{financeratecalc2026denialai,
  author    = {{Yeti{{\\c{{s}}}}, Ziya}},
  title     = {{The Denial-AI Benchmark v{B['version']}}},
  year      = {{2026}},
  publisher = {{FinanceRateCalc}},
  doi       = {{10.5281/zenodo.21575105}},
  url       = {{https://huggingface.co/datasets/FinanceRateCalc/denial-ai-benchmark}},
  note      = {{CC BY 4.0}}
}}
```

Related FinanceRateCalc papers: doi:10.2139/ssrn.7309319 (The Door Effect), doi:10.2139/ssrn.7341481 (Persistent Doors), doi:10.2139/ssrn.7423798 (What Denial Rates Cannot See).

The Denial-AI Benchmark™ is a FinanceRateCalc framework. Not affiliated with any AI vendor; no lender or AI vendor funds or previews this work.
"""
open(os.path.join(a.out, "README.md"), "w").write(README)
print("wrote", a.out, os.listdir(a.out))
