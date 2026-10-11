#!/usr/bin/env node
// Appends the latest protocol and evidence reports to eval/frc-mcp-conformance-history.json. Never overwrites earlier entries.
import fs from "node:fs";
const H = "eval/frc-mcp-conformance-history.json";
const hist = fs.existsSync(H) ? JSON.parse(fs.readFileSync(H, "utf8")) : { purpose: "Every published conformance run, passes and failures alike; entries are appended, never edited.", runs: [] };
const prev = hist.runs.length ? hist.runs[hist.runs.length - 1] : null;
for (const [suite, path] of [["protocol", "eval/frc-mcp-conformance.json"], ["evidence", "eval/frc-mcp-evidence-conformance.json"]]) {
  if (!fs.existsSync(path)) continue;
  const r = JSON.parse(fs.readFileSync(path, "utf8"));
  const hash = r.sha256 || r.report_sha256;
  if (hist.runs.some(x => x.suite === suite && x.report_hash === hash)) continue;
  const failed = (r.results || []).filter(t => !t.pass).map(t => t.id + ": " + (t.title || t.name));
  const last = [...hist.runs].reverse().find(x => x.suite === suite);
  const changed = last ? (r.results || []).filter(t => { const p = (last.result_ids || {})[t.id]; return p !== undefined && p !== !!t.pass; }).map(t => t.id) : [];
  hist.runs.push({ suite, suite_version: r.suite_version, fixture_version: r.fixture_version || null, server_version: r.server?.version || r.server_version || null, test_run_timestamp: r.generated_at, tests: r.tests, passed: r.passed, failed: r.tests - r.passed, report_hash: hash, changed_tests: changed, failure_summary: failed, result_ids: Object.fromEntries((r.results || []).map(t => [t.id, !!t.pass])) });
}
fs.writeFileSync(H, JSON.stringify(hist, null, 1) + "\n");
console.log("history entries:", hist.runs.length, prev ? "(previous: " + prev.test_run_timestamp + ")" : "");
