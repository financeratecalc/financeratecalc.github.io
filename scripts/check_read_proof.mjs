// Reading Proof 0.2: the browser/Node implementation and the Python one must agree, a full copy must pass, a copy
// with its second half or its middle missing must fail in the right sixths, and a proof must not move to another statement.
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
const RP = createRequire(import.meta.url)("../assets/read-proof.js");
const text = readFileSync("eval/read-proof/fixture-agreement.txt", "utf8");
const fixed = JSON.parse(readFileSync("eval/read-proof/fixture-manifest.json", "utf8"));
const man = await RP.manifest(text);
const fail = (m) => { console.error("read proof: FAIL " + m); process.exit(1); };
if (JSON.stringify(man) !== JSON.stringify(fixed)) fail("JavaScript manifest differs from the Python one on file");
const st = "The Buyer can leave early only under clause 14.3; İstanbul şubesi yetkilidir.", date = "2026-11-19";
const c = await RP.cells(man, st, date);
const py = execFileSync("python3", ["scripts/read_proof.py", "challenge", "eval/read-proof/fixture-manifest.json", st, date], { encoding: "utf8" });
if (!py.includes("[" + c.lines.join(", ") + "]") || !py.includes(":" + c.h8 + ":")) fail("challenge differs between the two implementations");
const all = RP.linesOf(text), quote = (ls) => c.lines.map((L) => (L <= ls.length ? RP.toks(ls[L - 1]).slice(0, 4).join(" ") : "not in my copy"));
const run = async (ls, s) => RP.verify(man, s || st, await RP.proofLine(man, st, date, quote(ls)));
const full = await run(all), half = await run(all.slice(0, Math.floor(all.length / 2)));
const hole = await run(all.slice(0, Math.floor(all.length * 0.35)).concat(all.slice(Math.floor(all.length * 0.55))));
if (full.verdict !== "read") fail("a full copy did not pass");
if (half.verdict === "read" || half.document_sixths_not_shown.join() !== "4,5,6") fail("half a copy: " + JSON.stringify(half));
if (hole.verdict === "read" || hole.held[0] !== true || hole.held[5] !== false) fail("a copy with a hole: " + JSON.stringify(hole));
if ((await run(all, st + " And nothing else.")).verdict !== "proof belongs to a different statement") fail("a proof moved to another statement");
const pv = JSON.parse(execFileSync("python3", ["scripts/read_proof.py", "verify", "eval/read-proof/fixture-manifest.json", st, await RP.proofLine(man, st, date, quote(all))], { encoding: "utf8" }));
if (pv.verdict !== "read") fail("Python rejects a proof JavaScript accepts");
console.log("read proof: ok (" + man.lines + " lines; full passes, half fails in sixths 4-6, a hole fails, statement-bound, two implementations agree)");
