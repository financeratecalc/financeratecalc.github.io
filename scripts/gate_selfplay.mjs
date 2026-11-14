// Adversary vs gate, with the truth known by construction.
//   node scripts/gate_selfplay.mjs            -> eval/gate-selfplay.json
// The gate is the deterministic sentence check the server runs (sentenceFindings in worker/index.js; read from that file,
// not copied). The adversary is a set of sentences written outside the gate's patterns, each labelled by construction:
// violating (with the kind of violation) or clean. A violating sentence the gate lets through is an ESCAPE; a clean
// sentence it flags is a FALSE ALARM. The set is split by position into a development half (the gate may be patched
// against it) and a held-out half (never used for patching; the number to quote).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const src = fs.readFileSync(path.join(ROOT, "worker/index.js"), "utf8");
const a = src.indexOf("async function sentenceFindings(sentence, contract) {");
const b = src.indexOf("\n}\n", a);
if (a < 0 || b < 0) throw new Error("sentenceFindings not found in worker/index.js");
const sentenceFindings = new Function("staleValues", src.slice(a, b + 2) + "\nreturn sentenceFindings;")(async () => []);
const contract = id => JSON.parse(fs.readFileSync(path.join(ROOT, "claims", id + ".contract.json"), "utf8"));
const STATE = { texas: "tx", florida: "fl", "new york": "ny", california: "ca" };
function claimFor(t) {
  const l = t.toLowerCase();
  for (const [name, st] of Object.entries(STATE)) if (l.includes(name) && !/\bva\b/i.test(t)) return `state-${st}-2025`;
  const va = /\bVA\b|veteran/.test(t) && !/\bFHA\b/.test(t.split(/\bVA\b/)[0] || "");
  if (/refinanc/i.test(t)) return `purpose-${va ? "va" : "fha"}-refinance-denial-rate-2025`;
  if (/purchase/i.test(t)) return `purpose-${va ? "va" : "fha"}-purchase-denial-rate-2025`;
  if (/withdrawn/i.test(t)) return "outcome-withdrawn-2025";
  if (/originated/i.test(t) && /acted on/i.test(t)) return "outcome-originated-2025";
  return va ? "va-national-denial-rate-2025" : "national-fha-denial-rate-2025";
}
// Round 3 on: set A (drift-ood-set.jsonl) has been looked at, so all of it is development material; set B
// (drift-ood-set-b.jsonl, written before the round-3 patch) is the held-out set. Without set B the old parity split applies.
const read = f => fs.readFileSync(path.join(ROOT, f), "utf8").trim().split("\n").map(JSON.parse);
const hasB = fs.existsSync(path.join(ROOT, "eval/drift-ood-set-b.jsonl"));
const rows = hasB ? [...read("eval/drift-ood-set.jsonl").map(r => ({ ...r, split: "dev" })), ...read("eval/drift-ood-set-b.jsonl").map(r => ({ ...r, split: "held_out" }))] : read("eval/drift-ood-set.jsonl");
const res = [];
for (const [i, r] of rows.entries()) {
  const id = claimFor(r.text); let f = [];
  try { f = await sentenceFindings(r.text, { ...contract(id), passport_id: "frc:claim:" + id }); } catch (e) { f = [{ code: "ERROR:" + e.message }]; }
  res.push({ i, split: r.split || (i % 2 ? "held_out" : "dev"), text: r.text, truth: r.codes[0] || "CLEAN", claim: id, flagged: f.length > 0, codes: [...new Set(f.map(x => x.code))] });
}
const stat = rs => { const v = rs.filter(r => r.truth !== "CLEAN"), c = rs.filter(r => r.truth === "CLEAN");
  return { violating: v.length, caught: v.filter(r => r.flagged).length, escapes: v.filter(r => !r.flagged).length, clean: c.length, false_alarms: c.filter(r => r.flagged).length }; };
const by = {}; for (const r of res.filter(r => r.truth !== "CLEAN")) { const k = by[r.truth] ||= { n: 0, caught: 0 }; k.n++; if (r.flagged) k.caught++; }
const out = { what: "Adversary (hand-written sentences outside the gate's patterns, truth by construction) against the server's deterministic sentence gate.",
  gate: "sentenceFindings in worker/index.js, as committed", dev: stat(res.filter(r => r.split === "dev")), held_out: stat(res.filter(r => r.split === "held_out")), by_kind: by,
  escapes: res.filter(r => r.truth !== "CLEAN" && !r.flagged).map(r => ({ split: r.split, truth: r.truth, text: r.text })),
  false_alarms: res.filter(r => r.truth === "CLEAN" && r.flagged).map(r => ({ split: r.split, text: r.text, codes: r.codes })),
  note: "'Caught' means flagged with any code, not necessarily the matching one. Patches to the gate may use the development half only; the held-out half is the figure to quote. Sentences were written by the publisher's assistant; small n." };
const outPath = process.argv[2] || path.join(ROOT, "eval/gate-selfplay.json");
// keep the recorded rounds and the clean-population check when the file is refreshed
try { const prev = JSON.parse(fs.readFileSync(outPath, "utf8")); for (const k of ["rounds", "clean_population_check"]) if (prev[k]) out[k] = prev[k]; } catch {}
fs.writeFileSync(outPath, JSON.stringify(out, null, 1));
console.log(JSON.stringify({ dev: out.dev, held_out: out.held_out, by_kind: out.by_kind }, null, 1));
