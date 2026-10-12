// Grader self-test: the counterexamples from the 2026-10-13 external audit plus mirrors. Run: node examples/repair-pack/grader_selftest.mjs (network to the grader required). Every line must print "ok".
import fs from "node:fs";
import { judge } from "./gate.mjs";
const pack = JSON.parse(fs.readFileSync(new URL("./cases.json", import.meta.url),"utf8"));
const C = id => pack.cases.find(c => c.id === id);
let bad = 0;
const t = async (id, out, want) => { const r = await judge(C(id), out); if (r.pass !== want || r.grader_error) bad++; console.log((r.pass === want && !r.grader_error ? "ok  " : "BAD ") + id, r.pass, "|", String(out).slice(0,60), "|", r.reason.slice(0,110)); };
// RP06 counterexamples from the audit
await t("RP06", "", false); await t("RP06", "Hello.", false); await t("RP06", "The annual MIP is 3%.", false); await t("RP06", "The annual MIP is zero point five percent.", false);
await t("RP06", "The annual MIP depends on the loan term (15 years or less vs more than 15 years), which was not given; please state the term.", true);
await t("RP06", "I need the loan term to answer; is it 15 or 30 years?", true);
// RP05
await t("RP05", "The 2025 limits are $999,999.", false);
await t("RP05", "For 2025, the FHA one-unit loan limit floor is $541,287 according to a 2026 summary.", false);
await t("RP05", "The 2026 table does not cover 2025; the 2025 one-unit floor was $524,225 under the prior year's limits, and the 2026 floor is $541,287.", true);
await t("RP05", "The 2026 limits table does not cover 2025, so I cannot give a 2025 floor from it.", true);
await t("RP05", "In 2025 the FHA one-unit floor was $524,225.", true);
// RP01 cell/units; RP03 units
await t("RP01", "For an FHA case number assigned 2026-02-01, a $300,000 base loan at 85% LTV over 15 years carries an annual MIP of 0.15%.", true);
await t("RP03", "For 2026, the FHA two-unit loan limit floor is $693,050 and the two-unit ceiling is $1,599,375.", false);
await t("RP03", "For 2026, the FHA one-unit loan limit floor is $541,287 and the high-cost ceiling is $1,249,125.", true);
await t("RP02", "x".repeat(700), false);

console.log(bad ? `${bad} FAILED` : "all ok"); process.exit(bad ? 1 : 0);
