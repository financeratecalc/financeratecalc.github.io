// The rule gate against the grammar-built training sentences that state the national FHA figure (so the contract matches).
//   node scripts/gate_on_grammar.mjs   -> eval/gate-on-grammar.json
// A far larger sample than the hand-written sets, with truth by construction; it is NOT held out for anything (the
// classifier is trained on it), so it measures the gate only. Clean rows include sentences that use the trigger words
// to decline the move ("no cause can be read off the percentage"); a keyword rule that flags those is a false alarm.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const src = fs.readFileSync(path.join(ROOT, "worker/index.js"), "utf8");
const a = src.indexOf("async function sentenceFindings(sentence, contract) {"), b = src.indexOf("\n}\n", a);
const sf = new Function("staleValues", src.slice(a, b + 2) + "\nreturn sentenceFindings;")(async () => []);
const id = "national-fha-denial-rate-2025";
const K = { ...JSON.parse(fs.readFileSync(path.join(ROOT, "claims", id + ".contract.json"), "utf8")), passport_id: "frc:claim:" + id };
const rows = fs.readFileSync(path.join(ROOT, "eval/drift-training-set.jsonl"), "utf8").trim().split("\n").map(JSON.parse).filter(r => r.kind === "grammar" && r.claim_id === "g:" + id);
const by = {}; let clean = 0, fa = 0; const faCodes = {}, ex = [];
for (const r of rows) {
  const f = await sf(r.text, K); const codes = [...new Set(f.map(x => x.code))];
  if (!r.codes.length) { clean++; if (codes.length) { fa++; for (const c of codes) faCodes[c] = (faCodes[c] || 0) + 1; if (ex.length < 6) ex.push({ text: r.text, flagged_as: codes }); } }
  else { const k = r.source.split(":")[1]; by[k] ??= { n: 0, flagged: 0 }; by[k].n++; if (codes.length) by[k].flagged++; }
}
const v = Object.values(by).reduce((s, x) => s + x.n, 0), c = Object.values(by).reduce((s, x) => s + x.flagged, 0);
const out = { what: "Rule gate (sentenceFindings, as committed) on grammar-built sentences about the national FHA figure. Truth by construction. Not held out.",
  violating: v, flagged: c, flagged_share: +(c / v).toFixed(3), by_kind: by, clean, clean_flagged: fa, clean_flagged_share: +(fa / clean).toFixed(3), clean_flagged_by_code: faCodes, clean_examples: ex,
  note: "'Flagged' means any code. The clean false alarms are mostly disclaimers: the gate matches the word (cause, statute, recommend) and does not read the negation around it." };
fs.writeFileSync(path.join(ROOT, "eval/gate-on-grammar.json"), JSON.stringify(out, null, 1) + "\n");
console.log(JSON.stringify({ violating: v, flagged: c, share: out.flagged_share, by_kind: Object.fromEntries(Object.entries(by).map(([k, x]) => [k, x.flagged + "/" + x.n])), clean, clean_flagged: fa, by_code: faCodes }));
