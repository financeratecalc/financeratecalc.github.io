# Claim Contract Compiler (v0.1)

Eight fields about one statistic in; everything the figure needs to survive machine restatement out.

```bash
python tools/claimcompiler/claimcompiler.py --demo            # the national FHA figure
python tools/claimcompiler/claimcompiler.py my-claim.json      # yours
```

| output | what it is |
|---|---|
| `safe_sentence` / `safe_sentence_with_receipt` | the one sentence a machine may quote verbatim, with the receipt attached to the number |
| `receipt` | `⟦<PUB>:<id>:<value>:<hash8>:<channel><YYMM>⟧`, hash of the canonical claim object |
| `passport` | what the number is and where it came from (Claim Contract 1.0 §4), hash included |
| `contract` | qualifiers, `does_not_establish` (each entry derived from a passport field or a policy clause), forbidden transformations (§5) |
| `forbidden_paraphrases` | five worked restatements the contract blocks, each with its reason code |
| `test_vectors` | pass / needs_qualifier / block vectors, re-derivable by any checker (§5.3) |
| `jsonld` | schema.org Dataset block with the receipt as a `PropertyValue` identifier |
| `gold_record` | the answer-key row an evaluator grades against (key tokens, rubric) |
| `verify_url` | where any client checks the receipt |

Deterministic, no network, no model. The demo reproduces the live receipt of the national figure (`ebf6b00b`) from the same claim object, which is the point: two implementations, one hash. Pair it with `tools/claimcheck` (does a proposed restatement pass the contract?) and with the transparency workflow (sign the `{id: value, hash8}` snapshot into Rekor so receipts verify without the publisher).

Input schema: see the module docstring; the only hard rule is that `display_value` contains no colon. `claim_extra` adds fields to the hashed claim object; `n_in_claim: false` keeps the cell size out of the hash. Output of the demo: `demo-output.json`.
