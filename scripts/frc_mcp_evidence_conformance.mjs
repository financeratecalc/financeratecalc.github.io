#!/usr/bin/env node
// Evidence conformance: published fixtures (fixtures/mortgage-evidence/fixtures.json) against the live endpoint.
// Usage: node scripts/frc_mcp_evidence_conformance.mjs [endpoint] [out]
// Deterministic; no model. Separate from the protocol suite (frc_mcp_conformance.mjs).
import fs from "node:fs";
import crypto from "node:crypto";

const EP = process.argv[2] || "https://frc-mcp.ziyetis.workers.dev";
const OUT = process.argv[3] || "eval/frc-mcp-evidence-conformance.json";
const FX = JSON.parse(fs.readFileSync("fixtures/mortgage-evidence/fixtures.json", "utf8"));
const META26 = { "io.modelcontextprotocol/protocolVersion": "2026-07-28", "io.modelcontextprotocol/clientInfo": { name: "frc-evidence-conformance", version: "1" }, "io.modelcontextprotocol/clientCapabilities": { elicitation: { form: {} } } };
let seq = 0;
async function rpc(method, params) {
  const r = await fetch(EP + "/", { method: "POST", headers: { "content-type": "application/json", accept: "application/json", "Mcp-Method": method }, body: JSON.stringify({ jsonrpc: "2.0", id: ++seq, method, params }) });
  return JSON.parse(await r.text());
}
const text = r => { try { return JSON.parse(r.result.content[0].text); } catch { return null; } };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

const results = [];
const receipts = {};
for (const f of FX.fixtures) {
  const row = { id: f.id, title: f.title, group: f.group, client: f.client, expected_status: f.expected_status };
  try {
    const inp = { ...f.input };
    if (inp.gate) {
      const r = await rpc("tools/call", { name: "check_claim_contract", arguments: { passport_id: inp.passport_id, proposed_sentence: inp.proposed_sentence } });
      const t = text(r); const codes = (t?.violations || []).map(v => v.code);
      row.observed = { verdict: t?.verdict, codes: [...new Set(codes)] };
      if (t?.rule_receipt) receipts[f.id] = t.rule_receipt;
      // a receipt anywhere in the result (nested fields included) counts as issued
      row.observed.receipt = !!t?.rule_receipt || /\u27e6FRC:/.test(JSON.stringify(t || {}));
      row.pass = t?.verdict === f.expected_status && (f.expected_reason_codes || []).every(c => codes.includes(c)) && !(f.expected_absent_codes || []).some(c => codes.includes(c)) && (f.expected_receipt === undefined || f.expected_receipt === !!t?.rule_receipt);
    } else if (inp.verify) {
      const rc = receipts[inp.from_fixture]; if (!rc) throw new Error("no receipt from " + inp.from_fixture);
      let tampered = rc; for (const [k, v] of Object.entries(inp.tamper)) tampered = tampered.replace(k, v);
      const ok = await (await fetch(EP + "/verify?r=" + encodeURIComponent(rc))).json();
      const bad = await (await fetch(EP + "/verify?r=" + encodeURIComponent(tampered))).json();
      row.observed = { original: ok.status, tampered: bad.status };
      row.pass = ok.status === "current" && bad.status !== "current";
    } else {
      const meta = f.client === "2026" ? META26 : undefined;
      const retry = inp.retry_with; delete inp.retry_with;
      const params = { name: f.tool, arguments: inp }; if (meta) params._meta = meta;
      let r = await rpc("tools/call", params);
      if (f.expected_status === "input_required" || retry) {
        const req = r.result?.inputRequests?.[0]?.params?.requestedSchema?.required || [];
        row.observed = { resultType: r.result?.resultType, required: req };
        if (retry) {
          r = await rpc("tools/call", { ...params, requestState: r.result?.requestState, inputResponses: [{ action: "accept", content: retry }] });
          const t = text(r); row.observed.after_retry = { verdict: t?.verdict, value: t?.annual_mip_bps, cell: t?.matched_conditions };
          if (t?.rule_receipt) receipts[f.id] = t.rule_receipt;
          row.pass = r.result?.resultType === "complete" && t?.verdict === f.expected_status && t?.annual_mip_bps === f.expected_value && same(t?.matched_conditions, f.expected_cell);
        } else {
          row.pass = r.result?.resultType === "input_required" && same(req, f.expected_required_fields) && !JSON.stringify(r).includes("annual_mip_bps\":1");
        }
      } else {
        const t = text(r);
        row.observed = { verdict: t?.verdict, codes: t?.reason_codes || [], value: t?.annual_mip_bps, cell: t?.matched_conditions, required: t?.required_fields, unit: t?.unit, source_document_id: t?.source_document_id };
        if (t?.rule_receipt) receipts[f.id] = t.rule_receipt;
        let ok = t?.verdict === f.expected_status;
        if (f.expected_value !== undefined) ok = ok && t?.annual_mip_bps === f.expected_value && t?.unit === f.unit && t?.source_document_id === f.source_document_id;
        if (f.expected_cell) ok = ok && same(t?.matched_conditions, f.expected_cell);
        if (f.expected_reason_codes) ok = ok && f.expected_reason_codes.every(c => (t?.reason_codes || []).includes(c)) && t?.annual_mip_bps === null;
        if (f.expected_required_fields) ok = ok && same(t?.required_fields, f.expected_required_fields);
        row.pass = !!ok;
      }
    }
  } catch (e) { row.pass = false; row.error = String(e.message || e); }
  results.push(row); console.log(row.pass ? "PASS" : "FAIL", row.id, row.title, JSON.stringify(row.observed || row.error));
}
const groups = {};
for (const r of results) { groups[r.group] = groups[r.group] || { tests: 0, passed: 0 }; groups[r.group].tests++; if (r.pass) groups[r.group].passed++; }
const passed = results.filter(r => r.pass).length;
const disc = (await rpc("server/discover", {})).result || {};
const report = { suite: "frc-mcp-evidence-conformance", suite_version: "1.4", fixture_version: FX.fixture_version, endpoint: EP, server_version: disc.serverInfo?.version || null, protocol_version: "2026-07-28 (fixtures marked client=2025 use the 2025 path)",
  generated_at: new Date().toISOString(), tests: results.length, passed, status: passed === results.length ? "evidence_fixture_pass" : "evidence_fixture_fail", groups,
  independent_reproduction_status: "not_independently_reproduced",
  statement: "Published protocol and fixture-level evidence behavior passed the declared test set. This is not an independent accuracy, security, legal or underwriting certification.",
  labels: ["evidence_fixture_pass_or_fail_as_stated", "not_independently_reproduced", "not_a_security_certification", "not_an_underwriting_certification"],
  results };
report.report_sha256 = crypto.createHash("sha256").update(JSON.stringify(results)).digest("hex");
fs.writeFileSync(OUT, JSON.stringify(report, null, 1) + "\n");
console.log(`${passed}/${results.length} ${report.status} -> ${OUT}`);
process.exit(passed === results.length ? 0 : 1);
