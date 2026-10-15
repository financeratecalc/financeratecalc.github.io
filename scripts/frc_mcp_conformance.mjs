#!/usr/bin/env node
// frc-mcp conformance + behaviour suite. Runs against a live endpoint, writes eval/frc-mcp-conformance.json.
// Usage: node scripts/frc_mcp_conformance.mjs [endpoint] [out]
// Deterministic: no model. Tests the MCP 2026-07-28 surface, the 2025 fallback, and the behaviour that
// matters for a financial evidence tool: missing conditions are asked for, never guessed; borrower data is
// refused; receipts verify. Each test records what was sent and the field that decided it.
import fs from "node:fs";
import crypto from "node:crypto";

const EP = process.argv[2] || "https://frc-mcp.ziyetis.workers.dev";
const OUT = process.argv[3] || "eval/frc-mcp-conformance.json";
const META26 = { "io.modelcontextprotocol/protocolVersion": "2026-07-28", "io.modelcontextprotocol/clientInfo": { name: "frc-conformance", version: "1" },
  "io.modelcontextprotocol/clientCapabilities": { elicitation: { form: {} } } };

let seq = 0;
async function rpc(method, params, headers = {}) {
  const body = { jsonrpc: "2.0", id: ++seq, method, params };
  const r = await fetch(EP + "/", { method: "POST", headers: { "content-type": "application/json", accept: "application/json", "Mcp-Method": method, ...headers }, body: JSON.stringify(body) });
  const text = await r.text();
  let j; try { j = JSON.parse(text); } catch { j = { parse_error: text.slice(0, 200) }; }
  return { status: r.status, headers: Object.fromEntries(r.headers), body: j };
}
const toolText = res => { try { return JSON.parse(res.body.result.content[0].text); } catch { return null; } };

const tests = [];
async function test(id, name, fn) {
  const t = { id, name };
  try { const r = await fn(); Object.assign(t, r); t.pass = !!r.pass; } catch (e) { t.pass = false; t.error = String(e.message || e); }
  tests.push(t); console.log((t.pass ? "PASS" : "FAIL"), id, name, t.evidence || t.error || "");
}

await test("01", "server/discover answers with protocol versions, capabilities and task table", async () => {
  const r = await rpc("server/discover", {});
  const d = r.body.result || {};
  return { pass: Array.isArray(d.protocolVersions) && d.protocolVersions.includes("2026-07-28") && d.resultType === "complete" && Array.isArray(d.can_answer) && Array.isArray(d.cannot_answer) && Array.isArray(d.tasks), evidence: `versions=${(d.protocolVersions || []).join(",")} tasks=${(d.tasks || []).length}` };
});
await test("02", "tools/list is deterministic across two calls", async () => {
  const a = await rpc("tools/list", {}), b = await rpc("tools/list", {});
  const na = (a.body.result.tools || []).map(t => t.name), nb = (b.body.result.tools || []).map(t => t.name);
  return { pass: na.length > 0 && JSON.stringify(na) === JSON.stringify(nb), evidence: `${na.length} tools, same order` };
});
await test("03", "tools/list carries cache metadata (ttlMs, cacheScope)", async () => {
  const r = await rpc("tools/list", {}); const d = r.body.result || {};
  return { pass: Number.isFinite(d.ttlMs) && (d.cacheScope === "public" || d.cacheScope === "private"), evidence: `ttlMs=${d.ttlMs} scope=${d.cacheScope}` };
});
await test("04", "2026 client, missing term and date -> input_required with exactly those fields", async () => {
  const r = await rpc("tools/call", { name: "resolve_fha_annual_mip", arguments: { base_loan_amount: 300000, ltv_pct: 85 }, _meta: META26 });
  const d = r.body.result || {}; const req = d.inputRequests?.[0]?.params?.requestedSchema?.required || [];
  return { pass: d.resultType === "input_required" && req.includes("term_years") && req.includes("case_number_date") && !req.includes("ltv_pct"), evidence: `required=${req.join(",")}`, requestState: d.requestState };
});
await test("05", "2026 client, only date missing -> input_required for the date alone, no number", async () => {
  const r = await rpc("tools/call", { name: "resolve_fha_annual_mip", arguments: { base_loan_amount: 300000, ltv_pct: 85, term_years: 15 }, _meta: META26 });
  const d = r.body.result || {}; const req = d.inputRequests?.[0]?.params?.requestedSchema?.required || [];
  return { pass: d.resultType === "input_required" && req.length === 1 && req[0] === "case_number_date" && !JSON.stringify(d).includes("annual_mip_bps\":15"), evidence: `required=${req.join(",")}` };
});
await test("06", "retry with inputResponses resolves the cell (15 bps) and returns complete", async () => {
  const first = await rpc("tools/call", { name: "resolve_fha_annual_mip", arguments: { base_loan_amount: 300000, ltv_pct: 85 }, _meta: META26 });
  const rs = first.body.result?.requestState;
  const r = await rpc("tools/call", { name: "resolve_fha_annual_mip", arguments: { base_loan_amount: 300000, ltv_pct: 85 }, _meta: META26, requestState: rs, inputResponses: [{ action: "accept", content: { term_years: 15, case_number_date: "2026-02-01" } }] });
  const t = toolText(r);
  return { pass: r.body.result?.resultType === "complete" && t?.verdict === "pass" && t?.annual_mip_bps === 15 && typeof t?.rule_receipt === "string", evidence: `verdict=${t?.verdict} bps=${t?.annual_mip_bps}`, receipt: t?.rule_receipt };
});
await test("07", "all conditions present -> complete, correct cell for three known inputs", async () => {
  const cases = [[300000, 85, 15, 15], [300000, 96.5, 30, 55], [800000, 80, 15, 40]];
  const got = [];
  for (const [amt, ltv, term, want] of cases) { const r = await rpc("tools/call", { name: "resolve_fha_annual_mip", arguments: { base_loan_amount: amt, ltv_pct: ltv, term_years: term, case_number_date: "2026-02-01" } }); got.push(toolText(r)?.annual_mip_bps === want); }
  return { pass: got.every(Boolean), evidence: `cells ${got.map(x => x ? "ok" : "WRONG").join("/")}` };
});
await test("08", "case date before the rule's effective date -> block RULE_NOT_IN_FORCE, no number", async () => {
  const r = await rpc("tools/call", { name: "resolve_fha_annual_mip", arguments: { base_loan_amount: 300000, ltv_pct: 85, term_years: 15, case_number_date: "2022-06-01" } });
  const t = toolText(r);
  return { pass: t?.verdict === "block" && (t?.reason_codes || []).includes("RULE_NOT_IN_FORCE") && t?.annual_mip_bps === null, evidence: `codes=${(t?.reason_codes || []).join(",")}` };
});
await test("09", "borrower attributes (income, credit score) are refused, not used", async () => {
  const r = await rpc("tools/call", { name: "resolve_fha_annual_mip", arguments: { base_loan_amount: 300000, ltv_pct: 85, term_years: 15, case_number_date: "2026-02-01", credit_score: 640, income: 50000 } });
  const t = toolText(r);
  return { pass: t?.verdict === "block" && (t?.reason_codes || []).includes("FORBIDDEN_INPUT") && t?.annual_mip_bps === null, evidence: `rejected=${(t?.rejected_fields || []).join(",")}` };
});
await test("10", "2025 client (no elicitation capability), missing fields -> block CONDITION_MISSING, no number", async () => {
  const r = await rpc("tools/call", { name: "resolve_fha_annual_mip", arguments: { base_loan_amount: 300000, ltv_pct: 85 } });
  const t = toolText(r);
  return { pass: r.body.result?.resultType === "complete" && t?.verdict === "block" && (t?.reason_codes || []).includes("CONDITION_MISSING") && t?.annual_mip_bps === null, evidence: `required_fields=${(t?.required_fields || []).join(",")}` };
});
await test("11", "2025 initialize handshake still works and returns a session", async () => {
  const r = await rpc("initialize", { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "frc-conformance-legacy", version: "1" } });
  return { pass: r.status === 200 && !!r.body.result?.serverInfo?.name && !!(r.headers["mcp-session-id"]), evidence: `server=${r.body.result?.serverInfo?.name} session=${r.headers["mcp-session-id"] ? "yes" : "no"}` };
});
await test("12", "rule receipt from test 06 verifies as current; a tampered value does not", async () => {
  const rc = tests.find(t => t.id === "06")?.receipt; if (!rc) return { pass: false, evidence: "no receipt from test 06" };
  const ok = await (await fetch(EP + "/verify?r=" + encodeURIComponent(rc))).json();
  const bad = await (await fetch(EP + "/verify?r=" + encodeURIComponent(rc.replace("15bps", "55bps")))).json();
  return { pass: ok.status === "current" && bad.status !== "current", evidence: `current=${ok.status} tampered=${bad.status}` };
});
await test("13", "sentence gate: stale value + second-person prediction -> block with both codes", async () => {
  const r = await rpc("tools/call", { name: "check_claim_contract", arguments: { passport_id: "frc:claim:national-fha-denial-rate-2025", proposed_sentence: "About 21.7% of mortgage applications were denied in 2025, so you will probably be rejected." } });
  const t = toolText(r); const codes = (t?.violations || []).map(v => v.code);
  return { pass: t?.verdict === "block" && codes.includes("STALE_VALUE") && codes.includes("INDIVIDUAL_PREDICTION_PROHIBITED"), evidence: `codes=${[...new Set(codes)].join(",")}` };
});
await test("14", "sentence gate: canonical sentence -> pass", async () => {
  const r = await rpc("tools/call", { name: "check_claim_contract", arguments: { passport_id: "frc:claim:national-fha-denial-rate-2025", proposed_sentence: "In 2025, 22.1% of decisioned FHA applications were denied (262,250 of 1,187,606). Source: FinanceRateCalc." } });
  const t = toolText(r);
  return { pass: t?.verdict === "pass", evidence: `verdict=${t?.verdict}` };
});
await test("15", "resolver: frc:rule id redirects to the rule file", async () => {
  const r = await fetch(EP + "/resolve/frc:rule:hud-ml-2023-05-annual-mip", { redirect: "manual" });
  return { pass: r.status === 302 && String(r.headers.get("location")).endsWith("/rules/fha-annual-mip-ml-2023-05.json"), evidence: `status=${r.status}` };
});

await test("16", "cite card: /cite/<claim-id> returns a receipted sentence whose receipt verifies as current", async () => {
  const c = await (await fetch(EP + "/cite/national-fha-denial-rate-2025")).json();
  if (!c.cited || !c.receipt) return { pass: false, evidence: "no card" };
  const v = await (await fetch(c.verify_url)).json();
  return { pass: v.status === "current" && String(c.sentence_with_receipt).includes(c.receipt) && !!c.formats?.markdown && c.receipt.includes(":c"), evidence: `verify=${v.status} channel=c` };
});
await test("17", "receipt forgery: a real claim id with a hash never issued is 'unrecognized' with no correction; an unknown id is refused cleanly", async () => {
  const f = await (await fetch(EP + "/verify?r=" + encodeURIComponent("\u27e6FRC:national-fha-denial-rate-2025:22.1%:deadbeef\u27e7"))).json();
  const s = await (await fetch(EP + "/verify?r=" + encodeURIComponent("\u27e6FRC:national-fha-denial-rate-2025:21.7%:779c4e5e\u27e7"))).json();
  const u = await fetch(EP + "/verify?r=" + encodeURIComponent("\u27e6FRC:state-zz-2025:10.0%:12345678\u27e7")); const uj = await u.json();
  return { pass: f.status === "unrecognized" && !f.correction && s.status === "stale" && !!s.correction && u.status === 200 && uj.reason === "unknown claim id",
    evidence: `forged=${f.status} correction=${!!f.correction}; pre-correction=${s.status} correction=${!!(s.correction && s.correction.date)}; unknown id=${u.status} ${uj.reason}` };
});
const passed = tests.filter(t => t.pass).length;
const disc = (await rpc("server/discover", {})).body.result || {};
const report = { suite: "frc-mcp-conformance-2026", suite_version: "1.1", endpoint: EP, server: disc.serverInfo || null, protocol_versions: disc.protocolVersions || null,
  generated_at: new Date().toISOString(), tests: tests.length, passed, conformance: passed === tests.length ? "PASS" : "FAIL",
  method: "Deterministic HTTP calls against the live endpoint; no model. Behaviour tests check that a missing public condition is asked for (2026 clients) or blocked (2025 clients) and never guessed, that borrower attributes are refused, that receipts verify and tampering is detected, and that the sentence gate grades the published vectors.",
  results: tests.map(({ receipt, requestState, ...t }) => t) };
report.sha256 = crypto.createHash("sha256").update(JSON.stringify(report.results)).digest("hex");
fs.mkdirSync(OUT.split("/").slice(0, -1).join("/") || ".", { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(report, null, 1) + "\n");
console.log(`${passed}/${tests.length} ${report.conformance} -> ${OUT}`);
process.exit(passed === tests.length ? 0 : 1);
