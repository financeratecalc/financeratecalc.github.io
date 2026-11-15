// The Fannie Mae DU minimum-credit-score rule, through the real server code (worker_local.mjs; no network).
//   node scripts/check_rule_du_score.mjs
import { callTool } from "./worker_local.mjs";
const ID = "frc:rule:fannie-du-minimum-credit-score-2025-11-16";
const check = s => callTool("check_claim_contract", { passport_id: ID, proposed_sentence: s });
const codes = r => (r.violations || []).map(v => v.code + ":" + v.field);
const t = [];
const want = async (name, sentence, verdict, mustHave = [], mustNot = []) => {
  const r = await check(sentence); const c = codes(r);
  const ok = r.verdict === verdict && mustHave.every(x => c.some(y => y.startsWith(x))) && mustNot.every(x => !c.some(y => y.startsWith(x)));
  t.push([name + "  ->  " + r.verdict + " [" + c.join(", ") + "]", ok]);
};
await want("old floor stated as current", "Fannie Mae requires a minimum credit score of 620 for loans run through Desktop Underwriter.", "block", ["STALE_VALUE"]);
await want("the safe wording passes", "For Fannie Mae loans submitted to Desktop Underwriter, the 620 minimum credit score requirement was removed for loan casefiles created on or after 16 November 2025 (Selling Guide Announcement SEL-2025-09); lenders and mortgage insurers may set their own minimums.", "pass");
await want("history stated as history", "Before November 16, 2025, Fannie Mae's Desktop Underwriter required a representative credit score of at least 620.", "pass", [], ["STALE_VALUE"]);
await want("removal without its date", "Fannie Mae removed the 620 minimum credit score for DU loans.", "needs_qualifier", ["QUALIFIER_DELETED:period"]);
await want("no issuer or system named", "The 620 minimum credit score was removed on November 16, 2025.", "needs_qualifier", ["QUALIFIER_DELETED:qualifiers"]);
await want("stretched to Freddie Mac", "Fannie Mae and Freddie Mac removed the 620 minimum for DU loans on November 16, 2025.", "block", ["PROGRAM_MISMATCH"]);
await want("stretched to manual underwriting", "Fannie Mae removed the 620 minimum on November 16, 2025 for DU and manually underwritten loans.", "block", ["PROGRAM_MISMATCH"]);
await want("stretched to lenders", "Since Fannie Mae removed the 620 minimum for DU loans on November 16, 2025, lenders no longer require a minimum score.", "needs_qualifier", ["QUALIFIER_DELETED:scope"]);
await want("turned into a promise", "Fannie Mae removed the 620 minimum for DU loans on November 16, 2025, so you can get approved with a 580 score.", "block", ["INDIVIDUAL_PREDICTION_PROHIBITED"]);
// the other rule files must behave as before: one known-good and one known-stale sentence
const va = await callTool("check_claim_contract", { passport_id: "frc:rule:va-funding-fee-2023-04-07", proposed_sentence: "For a first-use VA purchase loan with less than 5% down closing after 7 April 2023, the funding fee is 2.15% of the loan amount." });
t.push(["VA funding fee sentence still passes  ->  " + va.verdict, va.verdict === "pass"]);
const va2 = await callTool("check_claim_contract", { passport_id: "frc:rule:va-funding-fee-2023-04-07", proposed_sentence: "For a first-use VA purchase loan with less than 5% down, the funding fee is 2.30% of the loan amount." });
t.push(["VA superseded fee still blocked  ->  " + va2.verdict + " [" + codes(va2).join(", ") + "]", va2.verdict === "block"]);
const g = await callTool("get_rule", { rule_id: ID });
t.push(["get_rule returns the file with its sources", g.rule && g.rule.effective_from === "2025-11-16" && g.rule.sources.length === 2]);
for (const [n, ok] of t) console.log(ok ? "ok  " : "FAIL", n);
if (t.some(x => !x[1])) process.exit(1);
