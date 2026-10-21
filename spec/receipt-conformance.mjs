#!/usr/bin/env node
// Receipt 1.0 conformance suite. Publisher-independent: everything it needs comes from the manifest.
// Usage: node spec/receipt-conformance.mjs <manifest-url> [out.json] [--sample N]
//   e.g. node spec/receipt-conformance.mjs https://financeratecalc.com/.well-known/receipt.json
// Deterministic, no model, only fetch. Exit 0 when every test passes. Spec: spec/receipt-1.0.md section 10.
import fs from "node:fs";
import crypto from "node:crypto";

const MANIFEST = process.argv[2];
const OUT = process.argv[3] && !process.argv[3].startsWith("--") ? process.argv[3] : null;
const SAMPLE = Number((process.argv.find(a => a.startsWith("--sample=")) || "--sample=12").slice(9));
if (!MANIFEST) { console.error("usage: receipt-conformance.mjs <manifest-url> [out.json] [--sample=N]"); process.exit(2); }

const UA = "receipt-conformance/1.0";
const get = async (url) => { const r = await fetch(url, { headers: { "User-Agent": UA, accept: "application/json" }, redirect: "follow" }); const text = await r.text(); let j = null; try { j = JSON.parse(text); } catch {} return { status: r.status, headers: r.headers, json: j, text }; };

// RFC 8785 canonicalisation for the JSON values that occur in claim blocks (objects, arrays, strings,
// finite numbers, booleans, null). JSON.stringify already emits ES6 shortest numbers and escapes as JCS requires.
const jcs = x => Array.isArray(x) ? x.map(jcs) : (x && typeof x === "object") ? Object.fromEntries(Object.keys(x).sort().map(k => [k, jcs(x[k])])) : x;
const sha8 = obj => crypto.createHash("sha256").update(JSON.stringify(jcs(obj)), "utf8").digest("hex").slice(0, 8);
const LB = "⟦", RB = "⟧";
const parse = r => { const m = new RegExp(`^${LB}?([A-Z0-9]{2,8}):([a-z0-9-]+):([^:${RB}]+):([a-f0-9]{8})(?::([a-z][0-9]{4}))?${RB}?$`).exec(r); return m && { prefix: m[1], id: m[2], value: m[3], hash8: m[4], channel: m[5] || null }; };
const build = (prefix, id, value, hash8) => `${LB}${prefix}:${id}:${value}:${hash8}${RB}`;

const tests = [];
async function test(id, name, fn) {
  const t = { id, name };
  try { const r = await fn(); Object.assign(t, r); t.pass = !!r.pass; } catch (e) { t.pass = false; t.error = String(e.message || e).slice(0, 300); }
  tests.push(t); console.log((t.pass ? "PASS" : "FAIL"), id, name, t.evidence || t.error || "");
}

let M = null, verifyUrl = r => null, docs = [], history = null;

await test("01", "manifest: reachable, required fields, exactly one current hash rule", async () => {
  const r = await get(MANIFEST); M = r.json;
  const req = ["receipt", "prefix", "claims_index", "claim_url_template", "verify", "corrections", "hash_rules"];
  const missing = req.filter(k => !M || M[k] == null);
  const current = (M?.hash_rules || []).filter(h => h.current);
  verifyUrl = rc => M.verify.replace("{receipt}", encodeURIComponent(rc));
  return { pass: r.status === 200 && !missing.length && M.receipt === "1.0" && /^[A-Z0-9]{2,8}$/.test(M.prefix) && current.length === 1 && M.verify.includes("{receipt}") && M.claim_url_template.includes("{id}"),
    evidence: `status=${r.status} missing=[${missing}] prefix=${M?.prefix} current_rule=${current[0]?.id}` };
});
await test("02", "claims index lists claims; a sample of claim documents resolves", async () => {
  const r = await get(M.claims_index); const list = (r.json?.claims || []).filter(c => c.id && c.receipted !== false);
  if (!list.length) return { pass: false, evidence: "no claims" };
  // deterministic sample: first, last, and evenly spaced in between
  const pick = []; for (let i = 0; i < Math.min(SAMPLE, list.length); i++) pick.push(list[Math.floor(i * (list.length - 1) / Math.max(1, Math.min(SAMPLE, list.length) - 1))]);
  for (const c of pick) { const d = await get(M.claim_url_template.replace("{id}", c.id)); if (d.status === 200 && d.json) docs.push({ id: c.id, url: M.claim_url_template.replace("{id}", c.id), doc: d.json }); }
  return { pass: docs.length === pick.length, evidence: `${list.length} claims; ${docs.length}/${pick.length} sampled documents resolved` };
});
await test("03", "claim documents: required fields; hash8 equals jcs-sha256-8 of the claim block", async () => {
  const req = ["receipt_document", "id", "display_value", "claim", "hash_rule", "hash8", "receipt"];
  const bad = [];
  for (const { id, doc } of docs) {
    const missing = req.filter(k => doc[k] == null); const h = sha8(doc.claim);
    const p = parse(doc.receipt);
    if (missing.length || doc.hash8 !== h || !p || p.id !== id || p.value !== String(doc.display_value) || p.hash8 !== h || p.prefix !== M.prefix) bad.push(`${id}: missing=[${missing}] hash8=${doc.hash8} recomputed=${h} receipt=${doc.receipt}`);
  }
  return { pass: docs.length > 0 && !bad.length, evidence: bad.length ? bad.slice(0, 3).join(" | ") : `${docs.length} documents hash-consistent` };
});
await test("04", "each sampled document's receipt verifies current", async () => {
  const bad = [];
  for (const { id, doc } of docs) { const v = await get(verifyUrl(doc.receipt)); if (v.status !== 200 || v.json?.status !== "current" || String(v.json?.current_value) !== String(doc.display_value)) bad.push(`${id}: ${v.status} ${v.json?.status}`); }
  return { pass: docs.length > 0 && !bad.length, evidence: bad.length ? bad.slice(0, 3).join(" | ") : `${docs.length}/${docs.length} current` };
});
await test("05", "altered value segment -> hash-current-value-mismatch", async () => {
  const d = docs[0]; const p = parse(d.doc.receipt);
  const v = await get(verifyUrl(build(M.prefix, p.id, p.value + "0", p.hash8)));
  return { pass: v.json?.status === "hash-current-value-mismatch", evidence: `status=${v.json?.status}` };
});
await test("06", "never-issued hash -> unrecognized, no correction", async () => {
  const d = docs[0]; const p = parse(d.doc.receipt);
  const v = await get(verifyUrl(build(M.prefix, p.id, p.value, "0badf00d")));
  return { pass: v.json?.status === "unrecognized" && !v.json?.correction, evidence: `status=${v.json?.status} correction=${!!v.json?.correction}` };
});
await test("07", "unknown claim id -> HTTP 200, valid:false", async () => {
  const v = await get(verifyUrl(build(M.prefix, "no-such-claim-zz-0000", "1%", "12345678")));
  return { pass: v.status === 200 && v.json?.valid === false, evidence: `status=${v.status} valid=${v.json?.valid} reason=${v.json?.reason}` };
});
await test("08", "malformed receipt -> HTTP 400", async () => {
  const v = await get(verifyUrl("this is not a receipt"));
  return { pass: v.status === 400 && v.json?.valid === false, evidence: `status=${v.status}` };
});
await test("09", "bare (bracketless) form verifies the same as the bracketed form", async () => {
  const d = docs[0]; const bare = d.doc.receipt.replace(LB, "").replace(RB, "");
  const a = await get(verifyUrl(d.doc.receipt)), b = await get(verifyUrl(bare));
  return { pass: a.json?.status === "current" && b.json?.status === "current", evidence: `bracketed=${a.json?.status} bare=${b.json?.status}` };
});
await test("10", "corrections feed parses; items carry id, date, claim_ids", async () => {
  const r = await get(M.corrections); const items = r.json?.items || [];
  const bad = items.filter(i => !i.id || !i.date || !Array.isArray(i.claim_ids));
  return { pass: r.status === 200 && Array.isArray(r.json?.items) && !bad.length, evidence: `${items.length} items, ${bad.length} malformed` };
});
await test("11", "hash history (if declared): current hashes listed; a superseded hash verifies stale with a correction", async () => {
  if (!M.hash_history) return { pass: true, evidence: "not declared (optional)" };
  const r = await get(M.hash_history); history = r.json?.hashes || {};
  const unlisted = docs.filter(d => !(history[d.id] || []).includes(d.doc.hash8)).map(d => d.id);
  // find any id with a hash that is not current under either listed rule
  let staleCase = null;
  for (const [id, hs] of Object.entries(history)) {
    const url = M.claim_url_template.replace("{id}", id); const d = docs.find(x => x.id === id)?.doc || (await get(url)).json; if (!d?.claim) continue;
    const cur = new Set([sha8(d.claim), d.hash8]);
    const old = hs.find(h => !cur.has(h)); if (!old) continue;
    const v = await get(verifyUrl(build(M.prefix, id, "0", old)));
    if (v.json?.status === "stale") { staleCase = { id, old, correction: !!v.json?.correction, has_date: !!v.json?.correction?.date }; break; }
    if (v.json?.status === "current") continue; // old hash still current under a legacy rule
    staleCase = { id, old, status: v.json?.status }; break;
  }
  return { pass: !unlisted.length && (!staleCase || (staleCase.correction === true)), evidence: `unlisted=[${unlisted.slice(0, 3)}] stale_case=${JSON.stringify(staleCase)}` };
});
await test("12", "verify sets no cookie", async () => {
  const d = docs[0]; const v = await get(verifyUrl(d.doc.receipt));
  return { pass: !v.headers.get("set-cookie"), evidence: `set-cookie=${v.headers.get("set-cookie") ? "present" : "none"}` };
});

const passed = tests.filter(t => t.pass).length;
const report = { suite: "receipt-1.0-conformance", suite_version: "1.0", manifest: MANIFEST, publisher: M?.publisher || null, prefix: M?.prefix || null,
  generated_at: new Date().toISOString(), sample: docs.map(d => d.id), tests: tests.length, passed, conformance: passed === tests.length ? "PASS" : "FAIL", results: tests };
report.sha256 = crypto.createHash("sha256").update(JSON.stringify(report.results)).digest("hex");
if (OUT) { fs.mkdirSync(OUT.split("/").slice(0, -1).join("/") || ".", { recursive: true }); fs.writeFileSync(OUT, JSON.stringify(report, null, 1) + "\n"); }
console.log(`${passed}/${tests.length} ${report.conformance}${OUT ? " -> " + OUT : ""}`);
process.exit(passed === tests.length ? 0 : 1);
