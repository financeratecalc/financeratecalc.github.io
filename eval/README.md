# Denial-AI fidelity (Inspect AI)

Does a model restate a published statistic within its use contract? Twelve frozen questions about US FHA mortgage denials (2025 federal HMDA record, 1,187,606 decisions), answers generated from data and self-checked (12/12). Each answer is graded twice: **value** (every curated key token present; no model) and **fidelity** against the figure's [Claim Contract](https://financeratecalc.com/spec/claim-contract-1.0-draft.md) (model-graded with public [rubric vectors](rubric-vectors.json); grades C / P / I / A / N and 14 failure codes).

| task | condition |
|---|---|
| `denial_ai_fidelity` | A: no tools (parametric knowledge) |
| `denial_ai_fidelity_web` | B: web search |
| `denial_ai_fidelity_with_source` | C: the publisher's MCP server connected (figures with contracts and receipts) |
| `denial_ai_fidelity_with_receipts` | D: as C, client instructed that a figure is written with its claim receipt |
| `cliche_index` | 19 folk claims; stance vs. verdict against the record |

```bash
uv sync
inspect eval eval/denial_ai_fidelity.py@denial_ai_fidelity_with_source --model anthropic/claude-haiku-4-5-20251001 --epochs 3
# pinned assets: FRC_SITE=https://raw.githubusercontent.com/financeratecalc/financeratecalc.github.io/<sha>
# grader: FRC_GRADER_MODEL=<model>; optional second grader FRC_GRADER_B_MODEL=<model> (agreement recorded)
```

Saved administrations: [`runs/`](runs/) (grader named per row). Published series: https://financeratecalc.com/verdict-automated.html. Reporting rule: fractions of runs, denominator questions × repeats, never percentages. Companion RL environment with deterministic rewards: [`../rl-env/`](../rl-env/). Paper: `../papers/claim-contract-working-paper.md`. CC BY 4.0.
