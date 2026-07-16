# FinanceRateCalc.com — Engineering Runbook v1.0
_Last updated: 2026-07-06 · Owner: Ziya Yetiş · Bus-factor insurance document_

## 1. Platform Architecture
* **Frontend:** ~2,970 static HTML pages, GitHub Pages (repo: financeratecalc/financeratecalc.github.io, branch `main`)
* **Compute layer:** Cloudflare Worker — `frc-api.ziyetis.workers.dev` (Zai chat proxy)
* **Data engine:** `_data/` — 50+ git-versioned JSON vintages (HMDA 2018-2025, decision surfaces, macro_annual). `data/citable.json` = LLM citation endpoint. Engines fetch from `raw.githubusercontent.com/.../main/_data/` — **main IS production for data.**
* **Monetization:** Lemon Squeezy (all paid products) + Sky Blue affiliate (1,420 pages, rel="sponsored" + FTC disclosure)
* **Analytics:** GA4 `G-ND9P4F3PHT` · Forms: Formspree `mkoewrgp`

## 2. Deployment Workflow
1. Work from a fresh clone; `git pull` before any batch.
2. **Batch pushes** — never storm single-file commits (deploy collisions: Run #2122/#2125).
3. Any JS-bearing page: `node --check` extracted scripts BEFORE push. Engine pages: verdict.html, zai-one.html, lender-response-surface.html, lender-similarity.html, shock-beta.html, index.html (Void).
4. After push: verify GREEN via Actions API before declaring "live". Red run → `rerun-failed-jobs` via API.

## 3. Data Refresh Protocol
1. Download vintage (FFIEC/FHFA/HUD) → process into `_data/` schema.
2. **MANDATORY:** `python3 scripts/validate_schema.py` — exit 0 required before commit.
3. Push = instant production (engines read raw main). No staging exists; the validator IS the staging.
4. Update `data/citable.json` if headline stats changed.

## 4. Secrets Policy
* NO tokens/keys in HTML, JS, JSON, commit messages, or docs — ever.
* Worker secrets live in Cloudflare dashboard only.
* Any credential that touches a chat/transcript surface = compromised → revoke same day.

## 5. Incident Lessons (paid for, do not repay)
* Multi-line JS strings crash silently → node --check rule (Jul 2026)
* Push storms break Pages deploys → batch rule (Jul 2026)
* Mid-deploy crawls create phantom 404s (Ahrefs, Jul 2026) → deploy-then-verify, ignore crawler noise during windows
* Affiliate links need BOTH rel="sponsored" AND visible FTC disclosure (audit, Jul 2026)

## 6. Product Endpoints (Lemon Squeezy)
Store: financeratecalc.lemonsqueezy.com — Black Hole $49 · Condo $9.99 · Zai Pro $49/mo · Zai Broker $149/mo · annuals. Receipt emails configured; reply-to monitored.

* Credential rotation executed & verified via API (old GH token + old Anthropic key → 401 confirmed) — 2026-07-06. Rule: cell closes only on a verified 401, never on a claim.
* Worker secret migration: hardcoded key removed from source, env.ANTHROPIC_API_KEY guard added, end-to-end verified via live Zai routing response — 2026-07-06.

## 7. Publishing Ritual (every new/updated page — no exceptions)
1. `python3 scripts/smoke_test.py` — engines + navigation must be green (0 errors).
2. `python3 scripts/validate_schema.py` — if any `_data/` or `data/` file changed.
3. Commit + push to `main`; verify GREEN via Actions API before declaring live.
4. `python3 scripts/indexnow.py` — instant push to Bing/Yandex/Seznam/Naver (free, no quota). Key file `c6b683da5a78f29f3cfc283546e6ee73.txt` must stay in repo root or the protocol fails.
5. GSC → URL Inspection → Request Indexing for the new URL; resubmit sitemap if pages were added.
6. Update `llms.txt` if the page is a citable source; add an atom to `answers.html` if it answers a real question people ask.

### Visibility invariants (learned the hard way)
* **Every interactive engine needs a static shadow.** JS-rendered numbers are invisible to crawlers and agents — verdict.html and the-vintage.html had ZERO real figures in source until 2026-07-15. Ship a static facts block with every engine.
* **Tables die in RAG chunking; atoms survive.** One self-contained sentence carrying entity + number + date + source is citable; a table row is not.
* **Every flagship page carries author identity** (Person schema + `<meta name="author">` + visible byline). Finance is YMYL: anonymous data is suspect, a named 23-year banker is authority.
* `sameAs` chain = entity reconciliation. Currently: ActiveRain profile + Chrome Web Store. Add LinkedIn when available.
