#!/usr/bin/env node
// One command, one finished deliverable: a research note built from one published FinanceRateCalc claim.
//   node examples/research-note/make_note.mjs [claim-id] [out-dir]
// Default claim: national-fha-denial-rate-2025. No model, no key, no account. Node 18+.
// Produces brief.md (human note), evidence.json (the claim, contract and verification as returned), manifest.json
// (what was used: URLs, id, receipt, hash, period, server version, run time, status). A stale or mismatched receipt
// is written as such and the process exits non-zero; "delivered" is never written for an unverified figure.
import fs from "node:fs";
import path from "node:path";

const EP = process.env.FRC_ENDPOINT || "https://frc-mcp.ziyetis.workers.dev";
const id = (process.argv[2] || "national-fha-denial-rate-2025").replace(/^frc:claim:/, "");
const out = process.argv[3] || path.join("out", id);
const SITE = process.env.FRC_SITE_BASE || "https://financeratecalc.com"; // override only for offline tests
const get = async u => { u = String(u).replace("https://financeratecalc.com", SITE).replace("https://frc-mcp.ziyetis.workers.dev", EP); const r = await fetch(u, { headers: { "User-Agent": "frc-example-research-note/1.0" } }); if (!r.ok) throw new Error(`${r.status} ${u}`); return r.json(); };

const card = await get(`${EP}/cite/${encodeURIComponent(id)}`);
if (!card.cited) { console.error("no cite card for", id, card.reason || ""); process.exit(1); }
const passport = await get(card.passport_url);
const contract = card.contract_url ? await get(card.contract_url) : null;
const verify = await get(card.verify_url);
const disc = await get(`${EP}/server-card`).catch(() => ({}));

// Required fields, read from the contract: the note is not written if any is missing from the card.
const required = ["value", "sentence", "receipt", "attribution"];
const missing = required.filter(k => !card[k]);
const quals = card.required_qualifiers || (contract && contract.required_qualifiers) || {};
const status = missing.length ? "incomplete" : verify.status === "current" ? "verified" : verify.status === "stale" ? "stale" : "unverified";

// Previous run, if any: a changed receipt is reported, never silently overwritten as "updated".
let previous = null;
try { previous = JSON.parse(fs.readFileSync(path.join(out, "manifest.json"), "utf8")); } catch {}
const changed = previous && previous.receipt && previous.receipt !== card.receipt;

fs.mkdirSync(out, { recursive: true });
const now = new Date().toISOString();
const manifest = { example: "frc-research-note", version: "1.0", run_at: now, claim_id: card.id, value: card.value, receipt: card.receipt, receipt_hash: (card.receipt.match(/:([a-f0-9]{8}):/) || [])[1] || null,
  verify_status: verify.status, verify_url: card.verify_url, status, missing_fields: missing, period: (passport.claim && passport.claim.period) || quals.period || null,
  sources: { cite: `${EP}/cite/${id}`, passport: card.passport_url, contract: card.contract_url, server_card: `${EP}/server-card` }, server_version: (disc.serverInfo && disc.serverInfo.version) || null,
  data_vintage: (passport.provenance && passport.provenance.primary_source) || null, license: card.license || "CC BY 4.0",
  previous_run: previous ? { run_at: previous.run_at, receipt: previous.receipt, changed_since: !!changed } : null,
  correction: verify.correction || null, paths: { api_json: true, mcp: false }, note: "Figures fetched over the JSON cite/verify path; the same card is available to agents over MCP (check_claim_contract, get_* tools). Using the JSON path is not MCP adoption." };
fs.writeFileSync(path.join(out, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
fs.writeFileSync(path.join(out, "evidence.json"), JSON.stringify({ cite_card: card, passport, contract, verification: verify }, null, 2) + "\n");

const keep = Object.entries(quals).map(([k, v]) => `- ${k}: ${v}`).join("\n");
const dne = (card.does_not_establish || (contract && contract.does_not_establish) || []).map(x => `- ${x}`).join("\n");
const banner = status === "verified" ? "" : status === "stale" ? `> **Stale receipt.** The publisher has corrected this figure since the receipt was issued. Current value and correction: ${card.verify_url}\n\n` : `> **Not verified** (${status}${missing.length ? ": missing " + missing.join(", ") : ""}). Do not publish this note as is.\n\n`;
const brief = `# Research note: ${card.id}\n\n${banner}${changed ? `> Receipt changed since the previous run (${previous.run_at}). The previous note no longer describes the current figure.\n\n` : ""}**Finding.** ${card.sentence_with_receipt}\n\n${card.attribution}\n\n**Keep these qualifiers when you paraphrase:**\n${keep || "- (none listed)"}\n\n**This figure does not establish:**\n${dne || "- (none listed)"}\n\n**Provenance.** Data: ${manifest.data_vintage || "see passport"}. Passport: ${card.passport_url}${card.contract_url ? ` · Use contract: ${card.contract_url}` : ""} · Verify the receipt at any later date: ${card.verify_url}\n\nStatus at ${now}: **${status}** (verify: ${verify.status}; server ${manifest.server_version || "?"}). License ${manifest.license}.\n`;
fs.writeFileSync(path.join(out, "brief.md"), brief);
console.log(`${status.toUpperCase()}  ${card.id}  ${card.value}  ->  ${out}/{brief.md,evidence.json,manifest.json}`);
if (changed) console.log("note: receipt changed since previous run", previous.receipt, "->", card.receipt);
process.exit(status === "verified" ? 0 : 2);
