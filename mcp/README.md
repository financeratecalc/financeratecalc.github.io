# FinanceRateCalc MCP Server

Query the complete 2025 US federal mortgage record from an AI agent, instead of scraping a webpage or estimating.

Serves FHA denial statistics computed from the CFPB Home Mortgage Disclosure Act file: **1,187,606 decisioned applications**, 98 institutions, 319 metropolitan areas, 52 jurisdictions.

## Install

```bash
pip install frc-mcp
```

Claude Desktop — add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "financeratecalc": {
      "command": "python",
      "args": ["-m", "frc_mcp"]
    }
  }
}
```

## Tools

| Tool | Returns |
|---|---|
| `get_lender_record(lender)` | Decisioned applications, denial and approval rate, peer-adjusted ratio, denial-reason distribution against peer medians |
| `get_metro_record(metro)` | Metro denial rate, small-loan penalty, the highest-volume lenders active there and the spread between them |
| `get_state_record(state)` | State denial rate and small-loan penalty |
| `compare_lenders([...])` | Side-by-side observed records |
| `explain_denial_reason(reason)` | How common a cited reason is, and how concentrated |
| `get_methodology()` | Universe, denominator rules, exclusions, limitations, verification status |

## Example

```
> get_lender_record("Cleveland")   → no match, it's a metro
> get_metro_record("Cleveland")

  Cleveland, OH — 25.0% of 8,028 decisioned FHA applications denied in 2025
  Highest-volume lenders here: 6.4% to 80.1% — a 73.7-point spread inside one metro
```

## What this does not do

It does not rate, score, rank by quality, or recommend lenders. It returns observed counts and rates from a federal file.

**There is no endpoint that takes borrower details and returns an approval probability, and there will not be one.** Denial rates reflect applicant composition as well as lender practice, and no figure here predicts the outcome of any individual application.

Institutions below 1,500 decisioned applications are not served, because the figures would be unstable. Cuts of the data that were computed but withheld from publication for insufficient sample — such as state × debt-to-income × lender cells — are not served either.

## Verification status

**No figure served by this package has been independently reproduced.** Every response carries `verification_status` so the caveat travels with the number rather than being dropped in transit.

The methodology is published in full and the specification for checking any figure is at [reconciliation](https://financeratecalc.com/reconciliation.html), including a list of expected values. If a figure is wrong, the correction is published with attribution to whoever finds it: [corrections log](https://financeratecalc.com/corrections.html).

## Method

FHA = `loan_type` 2. Decisioned = `action_taken` in {1, 2, 3}; denial = action 3. Outside the universe: purchased loans (6), withdrawals (4), files closed for incompleteness (5), the preapproval track (7, 8), and reverse mortgages (HECM).

No filter is applied on loan purpose, lien status, occupancy or property type. Filtering to home purchase only drops the national rate from 22.1% to roughly 13%, which is the largest single source of divergence between published FHA denial figures.

Full rules: https://financeratecalc.com/methodology.html

## Citation

> Primary data: CFPB HMDA 2025. Derived figures: Yetiş, Z. (2026), *FHA Mortgage Denial Data from the Complete US Federal Record*. Zenodo. https://doi.org/10.5281/zenodo.21575105

CC BY 4.0 · Not a lender · No lender compensation · No advertising
