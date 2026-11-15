// The locate_denominator tool, run from the worker source against the published denominator-map data.
//   node scripts/check_locate_denominator.mjs
// Known placements (from the denominator map): 22.08 -> FHA all/decisioned; 10.61 -> FHA purchase, acted-on base;
// 8.24 -> VA purchase/decisioned; 12.23 (a widely quoted figure) -> no cell.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const src = fs.readFileSync(path.join(ROOT, "worker/index.js"), "utf8");
const a = src.indexOf('  if (name === "locate_denominator") {'), b = src.indexOf('  if (name === "get_official_figure") {');
if (a < 0 || b < a) throw new Error("locate_denominator handler not found in worker/index.js");
const getJSON = async p => JSON.parse(fs.readFileSync(path.join(ROOT, p), "utf8"));
const call = new Function("getJSON", "BASE", `return async function(name, args){\n${src.slice(a, b)}\n}`)(getJSON, "https://financeratecalc.com");
const has = (r, f) => r.matches.some(m => Object.entries(f).every(([k, v]) => m[k] === v));
const t = [];
let r = await call("locate_denominator", { rate_pct: 22.08 }); t.push(["22.08 -> FHA all|all decisioned", has(r, { program: "FHA", loan_purpose: "all", scope: "all", base: "decisioned", denominator: 1187606, denials: 262250 })]);
r = await call("locate_denominator", { rate_pct: 10.61 }); t.push(["10.61 -> FHA purchase acted_on", has(r, { program: "FHA", loan_purpose: "purchase", base: "acted_on" })]);
r = await call("locate_denominator", { rate_pct: 8.24, program: "va" }); t.push(["8.24 -> VA purchase decisioned, receipted", has(r, { program: "VA", loan_purpose: "purchase", scope: "all", base: "decisioned", receipted: true }) && r.matches.every(m => m.program === "VA")]);
r = await call("locate_denominator", { rate_pct: 12.23 }); t.push(["12.23 -> no cell", r.matches.length === 0 && /not evidence the figure is wrong/.test(r.reading)]);
r = await call("locate_denominator", { rate_pct: 22.08, tolerance: 9 }); t.push(["tolerance capped at 0.5", r.tolerance_points === 0.5]);
for (const bad of [{ rate_pct: "x" }, { rate_pct: 140 }, { rate_pct: 12, program: "usda" }]) { let threw = false; try { await call("locate_denominator", bad); } catch { threw = true; } t.push(["rejects " + JSON.stringify(bad), threw]); }
r = await call("locate_denominator", { rate_pct: 22.08 });
for (const m of r.matches) t.push([`arithmetic ${m.program} ${m.loan_purpose}|${m.scope} ${m.base}`, Math.abs(100 * m.denials / m.denominator - m.rate_pct) < 0.006]);
for (const [n, ok] of t) console.log(ok ? "ok  " : "FAIL", n);
console.log("cells searched:", r.cells_searched);
if (t.some(x => !x[1])) process.exit(1);
