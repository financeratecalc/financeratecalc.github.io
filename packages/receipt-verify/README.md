# receipt-verify

Verify a [Receipt 1.0](https://financeratecalc.com/spec/receipt-1.0.md) claim receipt — `⟦PREFIX:id:value:hash8⟧` — against the publisher that issued it, without trusting the publisher's server. Zero dependencies; Node 18+ or any browser.

```js
import { verify } from "receipt-verify";
const r = await verify("⟦FRC:state-oh-2025:23.0%:34beae06⟧", { manifest: "https://financeratecalc.com/.well-known/receipt.json" });
r.status // "current" | "stale" | "hash-current-value-mismatch" | "unrecognized"
```

```sh
npx receipt-verify '⟦FRC:state-oh-2025:23.0%:34beae06⟧'        # exit 0 only when current
```

What it does: parses the receipt, reads the publisher's manifest (`/.well-known/receipt.json`: claim URL template, hash rules, hash history), fetches the claim document, hashes its `claim` block under each listed rule (`jcs-sha256-8` = RFC 8785 canonical JSON, sha256, first 8 hex; the legacy `frc-0.1` rule is included), and compares.

| status | meaning |
| --- | --- |
| `current` | hash and quoted value match the publisher's current claim document |
| `hash-current-value-mismatch` | the hash is the publisher's, the quoted value is not — the quote was altered |
| `stale` | issued for an earlier value, since corrected; the result carries the current value |
| `unrecognized` | never issued as written: forged, mistyped or truncated |

Offline: pass `claim` (the claim document object) and `history` (the hash-history object) and nothing is fetched. Another publisher's rule: pass `rules: { "my-rule": async claim => hash8 }` and name it in the manifest.

Any publisher can issue receipts — the format is not FinanceRateCalc's; the spec, the conformance suite and this verifier are. MIT.
