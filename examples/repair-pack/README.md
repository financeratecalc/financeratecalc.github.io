# Mortgage evidence repair pack — does your app make these six mistakes?

Six questions a mortgage calculator or assistant tends to answer with a number that exists in the official table but is bound to the wrong role, tier, year or condition, or produced when a condition is missing. The pack tests **your** app, not FinanceRateCalc. The grader is FinanceRateCalc's deterministic sentence gate (`check_claim_contract`): no model judges the output, and the gate's own behaviour is published and tested on every deploy ([conformance](https://financeratecalc.com/conformance.html), 53 fixtures).

This is what a failing run looks like (an app that gets five of six "almost right"):

```
# Mortgage evidence repair report
Pack 1.0 · grader https://frc-mcp.ziyetis.workers.dev · 0/6 pass

## RP03 — Floor and ceiling bound to the right roles: REPAIR
App said.  For 2026, the FHA one-unit loan limit floor is $1,249,125 and the high-cost ceiling is $541,287.
Grader.    VALUE_MISMATCH — $1,249,125 is bound to the floor (1-unit); that cell is $541,287 ($1,249,125 is the ceiling of units 1)
           VALUE_MISMATCH — $541,287 is bound to the ceiling (1-unit); that cell is $1,249,125 ($541,287 is the floor of units 1)
Expected.  floor = $541,287, ceiling = $1,249,125, one unit
Source.    HUD Mortgagee Letter 2025-23 — One-unit: floor $541,287 (low-cost counties); ceiling $1,249,125 (high-cost counties).
Fix.       Bind each figure to its role in the clause where it appears.
Test that must pass after the fix: rerun this case; the gate must return pass with the expected binding.
```

Full reports: [wrong-app.repair-report.md](sample-outputs/wrong-app.repair-report.md) (0/6) · [right-app.repair-report.md](sample-outputs/right-app.repair-report.md) (6/6). The two sample apps are six stored sentences each ([wrong](sample-outputs/wrong-app.json), [right](sample-outputs/right-app.json)); the pack must separate them, and it does.

## The six cases

| id | what goes wrong | the test |
|---|---|---|
| RP01 | FHA annual MIP: a neighbouring cell (0.55%, 0.50%) instead of the one the conditions select (15 bps) | gate pass, resolved cell = le15 / le726200 / le90, `15 bps` bound to it |
| RP02 | $726,200 quoted as the FHA loan limit; it is the MIP base-loan threshold | gate pass with `$541,287` bound to the floor |
| RP03 | floor and ceiling swapped: right numbers, wrong roles | both bindings correct, on the 1-unit cells |
| RP04 | QM points-and-fees cap of another tier (5%) on the ≥ $137,958 tier (3%) | `3%` bound to that tier |
| RP05 | a 2026 figure dated 2025 because the source was a 2026 document | path (a): the 2025 figure ($524,225) bound to 2025 in its own clause (a source year does not count); or path (b): the app says the 2026 table does not cover 2025 and states no figure. Any other dollar figure fails |
| RP06 | term missing → a rate anyway | no rate stated (percent, bps or spelled out) **and** the term explicitly requested or its absence stated; the word "term" alone, empty or unrelated answers fail |

Each case in [`cases.json`](cases.json) carries the question, the expected cell or binding, the source document and fragment, the common failure, the fix hint and the rule file URL. The report prints all of it for every failing case, so a coding agent can work from the report alone.

## Run it on your app

**With promptfoo (your model or app, your cost):**
```
# edit providers: in promptfooconfig.yaml to point at your app or model
npx promptfoo@latest eval -c examples/repair-pack/promptfooconfig.yaml
npx promptfoo@latest view
```
The assertion ([`gate_assert.js`](gate_assert.js)) sends each answer to the gate and returns pass/fail with the reason, the source and the fix. Put the config in your CI and the six cases rerun whenever your prompt, model or calculation code changes.

**Without promptfoo (stored answers, no model; network to the grader is still required):**
```
node examples/repair-pack/run_offline.mjs my-outputs.json out/
```
`my-outputs.json` is `{ "RP01": "<your app's answer>", ... }`. Writes `repair-report.md` and `report.json`. Exit 0 on 6/6, 2 when a case needs repair, 3 when the grader could not be reached (those cases are marked NOT GRADED, never counted as your app's failure). Answers over 600 characters are refused with a reason, not cut.

Node 18+. No key, no account; the grader is a public endpoint. `FRC_ENDPOINT` points the pack at another copy of the gate for tests.

**Grader self-test:** `node examples/repair-pack/grader_selftest.mjs` runs the counterexamples an external audit found on 2026-10-13 (an empty answer, "Hello.", a 3% rate and a spelled-out rate all passed RP06; "$999,999" passed RP05) plus a second audit the same day ("This term is confusing." passed RP06; a 2025 figure dated 2026, and two right figures on swapped years, passed RP05) and their mirrors. Every line must print `ok`.

## What it is not

- Not a test of FinanceRateCalc; the gate's own tests are elsewhere. If the gate grades one of your correct answers as wrong, that is a bug in the gate: open an issue with the sentence, and it becomes a fixture.
- Not a model benchmark. Six cases, one domain, fixed wording. Your app may fail on wording the pack does not try.
- Not a claim about causes, lenders or any individual's application; the pack only covers published rule cells.
- Passing the pack is not MCP adoption: the grader is reached over JSON-RPC here. The same gate is available to agents as an MCP tool, and the fix hints name the MCP tools, but using the pack does not require connecting the server.

CC BY 4.0. Source: https://github.com/financeratecalc/financeratecalc.github.io/tree/main/examples/repair-pack
