# Demonstration Subjects

The Figure Receipt profile (draft-yetis-scitt-figure-receipts) is not specific to one country or one field. These two
Subjects restate figures of another publisher, Eurostat, under the same profile and with the same signing key as the
site's own figures. They are demonstrations: they are not FinanceRateCalc figures and are not counted among them.

| Subject | Figure | As retrieved |
| --- | --- | --- |
| `example-eurostat-prc-hpi-q-eu27-2026q2` | House price index, EU27, 2026-Q2, 2015 = 100 | 168.56 |
| `example-eurostat-demo-mlexpec-eu27-2024` | Life expectancy at birth, EU27, 2024, total (flagged estimated and provisional by the publisher) | 81.5 |

How each was made:

1. `.github/workflows/intl-fetch.yml` requested one observation from the Eurostat dissemination API and stored the
   response bytes unchanged in `data/intl/raw/`, with their SHA-256 and the time of retrieval in `data/intl/manifest.json`.
2. `scripts/build_intl_examples.py` copied the one observation, the publisher's labels and the publisher's flag into a
   statement. Nothing is computed.
3. The statement service signs it: `https://frc-mcp.ziyetis.workers.dev/statement/<Subject>` (add `?view=json` to read it).

One difference from the site's own restated figures, stated in each statement's limits: the digest is of an API response
as retrieved, kept at the archived address, not of a document the publisher keeps unchanged. A later retrieval can return
different bytes for the same value. When a later capture differs, it becomes the next revision of the same Subject.

Source: Eurostat. Reuse of Eurostat data is authorised with acknowledgement of the source.
