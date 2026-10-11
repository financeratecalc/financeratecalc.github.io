# FRC Proof Object 0.1 (draft, 2026-10-11)

A machine-readable block that travels with a figure so that an agent, a platform or a grader can check the figure without reading prose. Every figure-bearing result of the FinanceRateCalc MCP server (`frc-mcp` ≥ 1.19.0) carries one under the key `proof`.

```json
{
  "proof_object": "0.1",
  "kind": "claim",                                  // claim | rule_cell
  "id": "frc:claim:national-fha-denial-rate-2025",  // resolvable identifier
  "value": "22.1%",
  "receipt": "⟦FRC:national-fha-denial-rate-2025:22.1%:3f9a1c2b:m2610⟧",
  "verify_url": "https://frc-mcp.ziyetis.workers.dev/verify?r=…",
  "resolve_url": "https://frc-mcp.ziyetis.workers.dev/resolve/frc:claim:national-fha-denial-rate-2025",
  "source_url": "https://financeratecalc.com/claims/national-fha-denial-rate-2025.json",
  "contract_url": "https://financeratecalc.com/claims/national-fha-denial-rate-2025.contract.json",
  "source_vintage": "CFPB HMDA 2025 public LAR",
  "effective_from": null,                           // set for rule cells (e.g. "2023-03-20")
  "method_version": "frc-hmda-2025-v1",
  "verification_status": "reproducible from the public record by the published method; not independently reproduced",
  "scope": "historical aggregate; not an individual prediction, not a lender recommendation, not a legal conclusion",
  "corrections_feed": "https://financeratecalc.com/corrections.json"
}
```

## Fields

| field | meaning |
|---|---|
| `id` | An identifier in the `frc:claim:` or `frc:rule:` namespace. `GET /resolve/<id>` on the MCP host redirects to the object. |
| `value` | The figure as it should be quoted, with its unit. |
| `receipt` | `⟦FRC:<id>:<value>:<hash8>:<channel>⟧`. `hash8` is the first 8 hex of sha256 over the canonical claim object (or, for a rule cell, over `{rule_id, …cell}`); a corrected value changes the hash. `channel` names the door the receipt left by and the month. |
| `verify_url` | Returns `current`, `stale` (with the correction that superseded it) or `hash-current-value-mismatch` (the quote was altered). Independent check: the signed receipts snapshot in the public Rekor log. |
| `source_vintage`, `effective_from` | The record or issuer document the value comes from, and when a rule took effect. |
| `verification_status` | What the publisher claims and does not claim about reproduction. Never "verified" in the legal sense. |
| `scope` | What the figure does not establish. Preserve it when restating. |

## What a consumer can do with it

1. **An agent** quotes `value` with `receipt` attached to the number, keeps `scope`, and links `verify_url`.
2. **A platform** can refuse to render a financial figure without a proof block, or flag one whose receipt verifies as `stale`.
3. **A grader** scores a restatement on six checks (figure, period, population, program scope, attribution, forbidden transformations) against `contract_url`; worked example: https://financeratecalc.com/samples/scoring-a-correct-number.html

## Non-goals

No claim of legal verification or underwriting advice. No model in the loop: receipts, verdicts and resolution are deterministic. Proposed sentences sent to the gate are not stored.

## Status

Draft 0.1, one implementation (frc-mcp). Feedback: press@financeratecalc.com. License CC BY 4.0.
