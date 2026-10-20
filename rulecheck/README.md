# FRC Rule Watch

Dependabot for mortgage rule constants. Every year the FHA and conforming loan limits change on 1 January; FHA MIP and the VA funding fee change when HUD and VA say so. Code and content that hard-code those numbers keep serving last year's value, silently. Rule Watch finds them.

```yaml
# .github/workflows/rule-watch.yml
on: [push, pull_request, schedule]   # schedule: e.g. weekly, so a value that expires is caught even without a commit
jobs:
  rule-watch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: financeratecalc/financeratecalc.github.io/rulecheck@main
        with:
          fail-on: stale        # or: expiring, never
```

What it reports, per line, as a GitHub annotation:

| class | meaning | effect |
|---|---|---|
| `presented_as_current` | a value past its validity date used or described as current (including a value labelled with the wrong year) | error, fails the check |
| `role_misuse` | $726,200 used as a loan limit; it is the FHA annual-MIP base-loan threshold | error |
| `expiring` | a current value that expires within `warn-days` (default 75) | warning |
| `dated_correct`, `changelog`, `test_or_mock`, `unresolved` | historical, already updated beside it, test data, or no signal | notice or ignored |

Each finding names the value, what it was, the date it stopped being valid, its replacement, and the official source. The table is [`constants.json`](constants.json), derived from FinanceRateCalc's dated rule files (https://financeratecalc.com/rules/index.json), with every correction logged at https://financeratecalc.com/corrections.html.

Ignore a line with `rulecheck:ignore`; ignore a file with `rulecheck:ignore-file` in its first 40 lines.

**Tested on public code (2026-10-18):** 90 files in 53 public repositories that carry superseded mortgage constants. Rule Watch flagged 373 stale uses in 41 files across 29 repositories (one live calculator alone carries a county table of 2025 limits); it caught all 19 cases our earlier scanner had marked as presented-as-current, and found more that the scanner had missed, mostly values labelled with the wrong year (a 2024 FHA floor written as "2025"). Run on our own site, its first catch was three of our own pages (seven stale sentences) (corrections log, 18 October 2026).

Limits: deterministic patterns, no model; it reads the five lines around a match, so a value far from any keyword is not judged. It covers national values, not county tables. It is not legal or underwriting advice.

Licence: MIT (code), CC BY 4.0 (table).

## Discovery layer (candidates, not rules)

`scripts/discover_rule_candidates.py` runs weekly (`.github/workflows/rule-discovery.yml`): it fetches six agency pages (FHFA, HUD, CFPB, VA), stores a text snapshot, and sends only the changed paragraphs that mention a tracked constant to a small model with one job — quote the sentence that states a dated numeric value. Proposals land in `rules/candidates.json` as `pending`, with the verbatim quote, source URL, fetch date and page hash. A human reads the quote against the primary document and moves an approved value into `rules/` and `constants.json` by hand; the script never writes to either. No model consensus, no reward signal, no autonomy: the model reads, a person decides, and `review_seconds` records how long that took.
