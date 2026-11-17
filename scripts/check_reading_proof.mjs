// Proof of reading, end to end against the server source: draw, read the values from the edition file, verify; then the ways it must fail.
import fs from "node:fs";
import { callTool } from "./worker_local.mjs";
const assert = (c, m) => { if (!c) { console.error("FAIL:", m); process.exit(1); } };
const S = "HUD's August 2026 production report shows 78,925 FHA loans endorsed in the month.";
const read = (src, per, c) => { const d = JSON.parse(fs.readFileSync(`data/official/${src}-${per}.json`)); return c.month === per && d.figures[c.figure] ? d.figures[c.figure].value : d.months_as_printed[c.month][c.figure]; };
const LATEST = JSON.parse(fs.readFileSync("data/official/index.json")).latest;   // editions arrive monthly; never assume which one is newest
let n = 0;
for (const [src, per] of [["hud-fhaprod", "2026-08"], ["hud-lpt", "2026-08"], ["ginnie-iss", "2026-10"], ["sba-7a504", "2026-10"], ["hud-fhaprod", "2026-07"]]) {
  const ch = await callTool("reading_challenge", { source: src, period: per, statement: S, date: "2026-11-16" });
  assert(ch.cells.length === 3 && !JSON.stringify(ch.cells).match(/"value"/), src + ": three cells, no values in the challenge");
  const vals = ch.cells.map(c => read(src, per, c));
  const ok = await callTool("verify_reading_proof", { source: src, period: per, statement: S, date: "2026-11-16", values: vals });
  assert(ok.verdict === "read" && ok.matched === 3 && ok.proof.includes("FRC-READ:" + src), src + ": correct values verify");
  assert((per !== LATEST[src]) === ok.edition_status.startsWith("superseded"), src + " " + per + ": edition status");
  const viaLine = await callTool("verify_reading_proof", { statement: "  " + S.toUpperCase() + " ", proof: ok.proof });
  assert(viaLine.verdict === "read", src + ": proof line verifies; case and spacing of the statement do not matter");
  const other = await callTool("verify_reading_proof", { statement: S + " It rose.", proof: ok.proof });
  assert(other.verdict === "statement_mismatch", src + ": a proof line does not transfer to another statement");
  const wrong = await callTool("verify_reading_proof", { source: src, period: per, statement: S, date: "2026-11-16", values: [vals[0], Number(vals[1]) + 1, vals[2]] });
  assert(wrong.verdict === "not_shown" && wrong.matched === 2 && wrong.proof === null && !JSON.stringify(wrong).includes(String(vals[1])), src + ": a wrong value fails and the right one is not disclosed");
  const day2 = await callTool("reading_challenge", { source: src, period: per, statement: S, date: "2026-11-17" });
  const st2 = await callTool("reading_challenge", { source: src, period: per, statement: S + " It rose.", date: "2026-11-16" });
  const key = c => c.cells.map(x => x.month + x.figure).join();
  if (ch.cells_in_edition > 20) assert(key(day2) !== key(ch) && key(st2) !== key(ch), src + ": another day or another statement draws other cells");
  const replay = await callTool("verify_reading_proof", { source: src, period: per, statement: S, date: "2026-11-17", values: vals });
  if (ch.cells_in_edition > 20) assert(replay.verdict === "not_shown", src + ": yesterday's values do not pass for today");
  n++;
}
const bad = await callTool("verify_reading_proof", { statement: S, proof: "FRC-READ:nonsense" });
assert(bad._isError, "malformed proof line is refused");
console.log("proof of reading: " + n + " editions; draw, verify, proof line, wrong value, other statement, other day all behave");
// the offline verifier (Python, no server) must agree with the server on a fresh proof
import { execFileSync } from "node:child_process";
{
  const st = "Ginnie Mae issued $44,265 million of securities in October 2026.";
  const ch = await callTool("reading_challenge", { source: "ginnie-iss", period: "2026-10", statement: st, date: "2026-11-16" });
  const ok = await callTool("verify_reading_proof", { source: "ginnie-iss", period: "2026-10", statement: st, date: "2026-11-16", values: ch.cells.map(c => read("ginnie-iss", "2026-10", c)) });
  const out = JSON.parse(execFileSync("python3", ["scripts/verify_reading_proof.py", ok.proof, st]).toString());
  assert(out.verdict === "read" && out.matched === 3, "offline verifier agrees with the server");
  let failed = false; try { execFileSync("python3", ["scripts/verify_reading_proof.py", ok.proof, st + " More."], { stdio: "pipe" }); } catch { failed = true; }
  assert(failed, "offline verifier rejects the proof for another statement");
  console.log("offline verifier agrees:", ok.proof);
}
{ // the statement's own numbers are placed in the edition
  const st = "Ginnie Mae issued 44,265 million USD in October 2026, down from 99,999.";
  const ch = await callTool("reading_challenge", { source: "ginnie-iss", period: "2026-10", statement: st, date: "2026-11-16" });
  const v = await callTool("verify_reading_proof", { source: "ginnie-iss", period: "2026-10", statement: st, date: "2026-11-16", values: ch.cells.map(c => read("ginnie-iss", "2026-10", c)) });
  const f = Object.fromEntries(v.statement_figures.map(x => [x.number, x]));
  assert(v.verdict === "read" && f[44265].in_edition && f[44265].receipt_id === "official-ginnie-iss-2026-10-total-issuance-musd" && f[99999].in_edition === false && !(2026 in f), "statement numbers: the printed one is found with its receipt id, the invented one is not, the year is ignored");
  console.log("statement figures placed:", JSON.stringify(v.statement_figures));
}
