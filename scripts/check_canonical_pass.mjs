// Invariant: the gate must pass every contract's own canonical sentence. A contract whose safe wording is flagged by the
// gate teaches callers a sentence the server then rejects (found 14 Nov 2026: 48 small-loan-penalty templates lacked the
// word 'decisioned' that their own contract requires).   node scripts/check_canonical_pass.mjs   (exit 1 on any failure)
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const src = fs.readFileSync(path.join(ROOT, "worker/index.js"), "utf8");
const a = src.indexOf("async function sentenceFindings(sentence, contract) {"), b = src.indexOf("\n}\n", a);
const sf = new Function("staleValues", src.slice(a, b + 2) + "\nreturn sentenceFindings;")(async () => []);
let n = 0; const bad = [];
for (const f of fs.readdirSync(path.join(ROOT, "claims")).filter(x => x.endsWith(".contract.json"))) {
  const c = JSON.parse(fs.readFileSync(path.join(ROOT, "claims", f), "utf8")); const t = c.canonical_claim && c.canonical_claim.template;
  if (!t || !c.current_value) continue; n++;
  const r = await sf(t.replace("{value}", c.current_value), c);
  if (r.length) bad.push(f.replace(".contract.json", "") + ": " + r.map(x => x.code + " " + x.matched).join(", "));
}
console.log(`canonical sentences: ${n} checked, ${bad.length} flagged by the gate`);
bad.slice(0, 10).forEach(x => console.log("  " + x));
process.exit(bad.length ? 1 : 0);
