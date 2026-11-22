// WebMCP tools (assets/webmcp.js) run here against the files in this repository, and compared with the server's own /verify:
// the tool an agent calls in the reader's browser must give the same verdict as the verify service, for every receipt issued.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const assert = (c, m) => { if (!c) { console.error("FAIL:", m); process.exit(1); } };
globalThis.fetch = async (u) => {
  const s = typeof u === "string" ? u : u.url, url = new URL(s, "https://financeratecalc.com");
  if (url.hostname !== "financeratecalc.com") throw new Error("network call blocked: " + url.href);
  const f = path.join(ROOT, decodeURIComponent(url.pathname).slice(1));
  return fs.existsSync(f) && fs.statSync(f).isFile() ? new Response(fs.readFileSync(f), { status: 200, headers: { "content-type": "application/json" } }) : new Response("not found", { status: 404 });
};
if (!globalThis.caches) globalThis.caches = { default: { match: async () => undefined, put: async () => {} } };
const load = async (rel, tag) => { const tmp = path.join(os.tmpdir(), tag + process.pid + ".mjs"); fs.copyFileSync(path.join(ROOT, rel), tmp); const m = await import(pathToFileURL(tmp).href); fs.unlinkSync(tmp); return m; };
const W = await load("assets/webmcp.js", "frc-webmcp-"), worker = (await load("worker/index.js", "frc-webmcp-w-")).default;
const server = async r => (await worker.fetch(new Request("https://frc-mcp.ziyetis.workers.dev/verify?r=" + encodeURIComponent(r)), {})).json();
const tool = n => W.tools.find(t => t.name === n), call = (n, input) => tool(n).execute(input, { signal: new AbortController().signal });

// 1. Shape: three tools, read-only, each with a schema whose required fields exist; names are unique.
assert(W.tools.length === 3 && new Set(W.tools.map(t => t.name)).size === 3, "three distinct tools");
for (const t of W.tools) { assert(t.annotations && t.annotations.readOnlyHint === true && !t.annotations.consequentialHint, t.name + " must be read-only");
  assert(t.description.length > 80 && t.inputSchema.type === "object" && t.inputSchema.required.every(k => t.inputSchema.properties[k]), t.name + " schema"); }

// 2. Every receipt this site has issued verifies as current, here and on the server.
const idx = JSON.parse(fs.readFileSync(path.join(ROOT, "claims/index.json"), "utf8")).claims.filter(c => c.receipt);
let n = 0; for (const c of idx) { const v = await W.verifyReceipt(c.receipt); assert(v.valid && v.status === "current" && v.current_value === c.display_value, "not current here: " + c.receipt + " " + JSON.stringify(v)); n++; }
const sample = idx.filter((_, i) => i % 24 === 0);
for (const c of sample) { const s = await server(c.receipt); assert(s.status === "current", "server disagrees on " + c.receipt + ": " + s.status); }

// 3. The three ways a receipt goes wrong get the same verdict here and on the server.
const one = idx.find(c => c.id === "state-oh-2025"), [, , val, hash] = /FRC:([a-z0-9-]+):([^:]+):([a-f0-9]{8})/.exec(one.receipt);
const hist = JSON.parse(fs.readFileSync(path.join(ROOT, "transparency/receipt-hash-history.json"), "utf8")).hashes;
const old = Object.entries(hist).map(([id, hs]) => ({ id, c: idx.find(x => x.id === id), hs })).find(e => e.c && e.hs.some(h => !e.c.receipt.includes(h)));
const cases = [
  ["altered value", `⟦FRC:state-oh-2025:99.9%:${hash}⟧`, "hash-current-value-mismatch"],
  ["invented hash", `⟦FRC:state-oh-2025:${val}:00000000⟧`, "unrecognized"],
  ["earlier hash of a corrected figure", `⟦FRC:${old.id}:${old.c.display_value}:${old.hs.find(h => !old.c.receipt.includes(h))}⟧`, "stale"],
  ["receipt inside a sentence, no brackets", `In Ohio the rate was 23.0% (FRC:state-oh-2025:${val}:${hash}).`, "current"],
];
for (const [what, r, want] of cases) { const here = await call("verify_receipt", { receipt: r }), there = await server(r);
  assert(here.status === want, `${what}: here ${here.status}, expected ${want}`); assert(there.status === want, `${what}: server ${there.status}, expected ${want}`); }
let v = await call("verify_receipt", { receipt: "⟦FRC:no-such-claim-2025:1%:abcdef12⟧" }); assert(v.valid === false && /unknown claim/.test(v.reason), "unknown id");
v = await call("verify_receipt", { receipt: "22.1% of mortgages" }); assert(v.valid === false && /not a receipt/.test(v.reason), "not a receipt");
v = await call("verify_receipt", {}); assert(v.error, "missing input returns an error value, not an exception");
v = await call("verify_receipt", { receipt: "⟦FRC:../../etc/passwd:1:abcdef12⟧" }); assert(v.valid === false, "path characters are not a claim id");
const rev = await call("verify_receipt", { receipt: idx.find(c => c.id === "official-hud-fhaprod-2026-08-refinance-count").receipt });
assert(rev.status === "current" && rev.publisher_revision && rev.publisher_revision.revised_to === 20682, "publisher revision is reported on the first printing's receipt");

// 4. find_figure: the right figure comes first, results carry receipts that verify, and nothing is made up for a stranger's question.
const first = async q => (await call("find_figure", { query: q })).results[0];
for (const [q, id] of [["ohio fha denial 2025", "state-oh-2025"], ["national fha denial rate 2025", "national-fha-denial-rate-2025"], ["va national denial 2025", "va-national-denial-rate-2025"], ["hud fhaprod 2026-08 refinance count", "official-hud-fhaprod-2026-08-refinance-count"],
  ["how often are FHA loans denied in Texas?", "state-tx-2025"], ["Florida VA loan denial", "va-state-fl-denial-rate-2025"], ["west virginia fha denial", "state-wv-2025"], ["conventional denial rate in New York", "conv-state-ny-denial-rate-2025"],
  ["serious delinquency rate September 2026", "official-hud-lpt-2026-09-serious-delinquency-rate"], ["Rocket Mortgage FHA denial rate", "lender-rocket-mortgage-2025"], ["cleveland metro lender gap", "metro-gap-cleveland-oh-2025"]]) {
  const f = await first(q); assert(f && f.id === id, `"${q}" should find ${id}, found ${f && f.id}`); assert((await W.verifyReceipt(f.receipt)).status === "current", "result receipt verifies"); }
let f = await call("find_figure", { query: "bitcoin price tomorrow" }); assert(f.results.length === 0 && /no figure for anything else/.test(f.next), "an unrelated question finds nothing and says so");
f = await call("find_figure", { query: "the of in" }); assert(f.error, "only filler words");
f = await call("find_figure", { query: "fha denial", limit: 500 }); assert(f.results.length === 20, "limit is capped");
f = await call("find_figure", { query: 7 }); assert(f.error, "non-text query");

// 5. get_figure: the publisher's sentence carries the current value, the qualifiers and limits come from the contract, the receipt verifies.
let g = await call("get_figure", { id: "state-oh-2025" });
assert(g.value === "23.0%" && g.sentence.includes("23.0%") && !g.sentence.includes("{value}") && g.required_qualifiers.period === "2025" && g.does_not_establish.length >= 3 && /Source:/.test(g.attribution), "get_figure state-oh-2025");
assert((await W.verifyReceipt(g.receipt)).status === "current", "get_figure receipt verifies");
g = await call("get_figure", { id: "frc:claim:official-hud-fhaprod-2026-08-refinance-count" }); assert(g.publisher_revision && g.publisher_revision.revised_to === 20682 && /Production Report/.test(g.sentence), "official figure with its revision");
g = await call("get_figure", { id: "no-such-claim" }); assert(g.error && /No figure/.test(g.error), "unknown id");
g = await call("get_figure", { id: "../index" }); assert(g.error, "path characters refused");
let bad = 0; for (const c of idx) { const x = await W.getFigure(c.id); if (x.error || !x.sentence || x.sentence.includes("{value}") || x.receipt !== c.receipt) bad++; }
assert(bad === 0, bad + " figures lack a sentence or a matching receipt");

// 6. Nothing in any tool output predicts, recommends or ranks; and the file sends nothing anywhere but this site's own files.
const src = fs.readFileSync(path.join(ROOT, "assets/webmcp.js"), "utf8");
assert(!/https?:\/\/(?!financeratecalc\.com)/.test(src.replace(/\/\/.*$/gm, "")), "the tools must not call another host");
assert(!/method:\s*["']POST|sendBeacon|localStorage|cookie/i.test(src), "the tools must not send or store anything");

// 7. Registration: every tool is handed to the browser's API once; a browser that refuses one still gets the others.
const got = []; let done = await W.register({ registerTool: async t => { got.push(t.name); } }); assert(done.length === 3 && got.join() === "verify_receipt,find_figure,get_figure", "register");
done = await W.register({ registerTool: async t => { if (t.name === "find_figure") throw new Error("duplicate"); } }); assert(done.length === 2, "one refusal does not stop the rest");

// 8. The pages that say they offer the tools load this file, and only behind the feature check.
for (const p of ["index.html", "verify.html", "check-answer.html", "mcp-server.html"]) { const h = fs.readFileSync(path.join(ROOT, p), "utf8");
  assert(/"modelContext" in document\?document\.modelContext:navigator\.modelContext;if\(mc&&mc\.registerTool\)\{const\{tools\}=await import\("\/assets\/webmcp\.js"\)/.test(h), p + " does not load the tools behind the feature check"); }
console.log(`webmcp: ${n} receipts current here, ${sample.length} cross-checked with the server, ${cases.length} failure cases agree with the server, find and get behave, ${idx.length} figures have a sentence and a receipt`);
