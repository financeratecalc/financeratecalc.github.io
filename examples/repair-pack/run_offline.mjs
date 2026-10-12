#!/usr/bin/env node
// Grade stored outputs of an app without promptfoo or a model (network to the live grader is required):
//   node examples/repair-pack/run_offline.mjs <outputs.json> [out-dir]
// outputs.json: { "RP01": "<the app's answer>", ... }. Writes repair-report.md and report.json. Exit 0 only when all six pass.
import fs from "node:fs"; import path from "node:path";
import { judge, EP } from "./gate.mjs";
const here = path.dirname(new URL(import.meta.url).pathname);
const pack = JSON.parse(fs.readFileSync(path.join(here, "cases.json"), "utf8"));
const outputs = JSON.parse(fs.readFileSync(process.argv[2] || path.join(here, "sample-outputs", "wrong-app.json"), "utf8"));
const out = process.argv[3] || path.join(here, "out");
fs.mkdirSync(out, { recursive: true });
const rows = [];
for (const c of pack.cases) { const o = outputs[c.id]; const r = o == null ? { pass: false, reason: "no output for this case" } : await judge(c, o); rows.push({ id: c.id, title: c.title, output: o, ...r }); console.log(r.pass ? "PASS" : r.grader_error ? "GRADER_ERROR" : "REPAIR", c.id, c.title); }
const passed = rows.filter(r => r.pass).length; const gerr = rows.filter(r => r.grader_error).length;
const md = [`# Mortgage evidence repair report`, ``, `Pack ${pack.version} · grader ${EP} (deterministic sentence gate, no model; network required) · ${new Date().toISOString()} · **${passed}/${rows.length} pass**${gerr ? ` · ${gerr} not graded (grader error)` : ""}`, ``];
for (const r of rows) { const c = pack.cases.find(x => x.id === r.id);
  md.push(`## ${r.id} — ${c.title}: ${r.pass ? "PASS" : r.grader_error ? "NOT GRADED (grader error)" : "REPAIR"}`, ``, `**Question.** ${c.question}`, ``, `**App said.** ${r.output == null ? "(no output)" : r.output}`, ``, `**Grader.** ${r.reason}`);
  if (!r.pass && !r.grader_error) md.push(``, `**Expected.** ${JSON.stringify(c.expected)}`, ``, `**Source.** ${c.source_document} — ${c.source_fragment} (${c.rule_url})`, ``, `**Common failure.** ${c.common_failure}`, ``, `**Fix.** ${c.fix_hint}`, ``, `**Test that must pass after the fix.** Rerun this case: the gate must return ${c.expected.verdict === "no_number" ? "no stated rate" : c.expected.verdict === "prior_year_or_abstain" ? "path (a) the prior-year figure dated correctly, or path (b) explicit abstention" : c.expected.verdict === "block" ? "block with " + c.expected.codes.join(",") : "pass with the expected binding"}.`);
  md.push(``); }
md.push(`---`, `Rule files: https://financeratecalc.com/rules/index.json · Gate: check_claim_contract on https://frc-mcp.ziyetis.workers.dev · Conformance of the gate itself: https://financeratecalc.com/conformance.html · CC BY 4.0`);
fs.writeFileSync(path.join(out, "repair-report.md"), md.join("\n") + "\n");
fs.writeFileSync(path.join(out, "report.json"), JSON.stringify({ pack: pack.pack, version: pack.version, grader: EP, run_at: new Date().toISOString(), passed, total: rows.length, grader_errors: gerr, results: rows.map(({ gate, ...r }) => ({ ...r, gate_verdict: gate && gate.verdict, gate_codes: gate && (gate.violations || []).map(v => v.code) })) }, null, 2) + "\n");
console.log(`${passed}/${rows.length} -> ${out}/repair-report.md`);
process.exit(gerr ? 3 : passed === rows.length ? 0 : 2);
