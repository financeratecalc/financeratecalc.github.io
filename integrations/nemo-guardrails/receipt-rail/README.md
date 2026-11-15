# Receipt rail for NVIDIA NeMo Guardrails

An output rail that checks every receipt (`⟦FRC:id:value:hash⟧`) in a model's answer against the publisher's public
verify endpoint before the answer is shown. No model is called by the rail and no key is needed.

**Why.** A number from a public record can be wrong without being invented: the publisher corrected it, an official
report printed a different value in a later edition, or the digits were altered on the way. A receipt binds the number
to its source file, definition and period; this rail refuses an answer whose receipt no longer verifies.

| The receipt is | The rail |
|---|---|
| current | lets the answer through |
| stale (publisher corrected the figure) | blocks, with the current value in the reason |
| altered (hash does not match the number) | blocks |
| not issued by the publisher | blocks |
| current, but its source printed a different value in a later edition and the answer does not say so | blocks |

## Use

Copy `actions.py`, `rails.co` and `config.yml` into your guardrails configuration folder and add your `models:` block.
The rail is the single line under `rails.output.flows`. To get receipts into answers, connect the model to the source's
tools (MCP server `https://frc-mcp.ziyetis.workers.dev`), whose results carry the figure with its receipt.

Options (environment): `FRC_VERIFY_URL` (another Receipt 1.0 publisher's verify endpoint),
`FRC_RAIL_REQUIRE_RECEIPT=1` (also block an FHA or VA denial rate stated with no receipt).

## Status and limits

- The checking logic is unit-tested here (`python3 test_actions.py`, no network). The rail has also been run inside the
  library itself (`live_test.py`, nemoguardrails 0.24.1, 15 November 2026, no model configured, output rail only): a
  message with an issued receipt came back unchanged and the same message with one character of the receipt altered
  was replaced by the refusal. Result on record in `live-test.json`. It has not been run in a full pipeline with a
  model generating the message, or on any version other than 0.24.1.
- It verifies receipts; it does not judge numbers that carry none unless the strict option is on, and then only for
  the pattern named above.
- Any publisher that implements Receipt 1.0 (https://financeratecalc.com/spec/receipt-1.0.md) can be verified the
  same way by pointing `FRC_VERIFY_URL` at its endpoint.

Licence: MIT for this folder. The figures: CC BY 4.0, FinanceRateCalc.
