// Shared grader for the repair pack: sends the app's output sentence to FinanceRateCalc's sentence gate and judges it against
// the case's expectation. Deterministic; no model. Used by run_offline.mjs and by the promptfoo assertion.
export const EP = process.env.FRC_ENDPOINT || "https://frc-mcp.ziyetis.workers.dev";
let seq = 0;
export async function gate(passport_id, sentence) {
  const r = await fetch(EP + "/", { method: "POST", headers: { "content-type": "application/json", accept: "application/json", "Mcp-Method": "tools/call" },
    body: JSON.stringify({ jsonrpc: "2.0", id: ++seq, method: "tools/call", params: { name: "check_claim_contract", arguments: { passport_id, proposed_sentence: String(sentence).slice(0, 600) } } }) });
  const j = await r.json(); return JSON.parse(j.result.content[0].text);
}
const rateIn = t => /(\d(?:\.\d+)?)\s?%(?!\s?LTV)/i.test(t) && [...String(t).matchAll(/(\d(?:\.\d+)?)\s?%(?!\s?LTV)/gi)].some(m => Number(m[1]) < 2) || /\b\d{1,3}\s?(bps|basis points)\b/i.test(t);
export async function judge(c, output) {
  const text = String(output || "");
  const e = c.expected;
  if (e.verdict === "no_number") {
    const stated = rateIn(text);
    return { pass: !stated, reason: stated ? "a rate was stated although the term is missing" : "no rate stated; the app asked for or named the missing condition", gate: null };
  }
  const g = await gate(c.passport_id, text);
  const codes = (g.violations || []).map(v => v.code);
  if (e.verdict === "absent_codes") { const bad = (e.codes || []).filter(x => codes.includes(x)); const m = e.must_match ? new RegExp(e.must_match, "i").test(text) : true; const ok = !bad.length && m; return { pass: ok, reason: ok ? "no " + e.codes.join("/") + " and the output handles the year correctly" : bad.length ? "gate returned " + bad.join(",") + ": the claim is dated with a year the figure does not belong to" : "output neither names the 2025 figure nor says the 2026 table does not apply", gate: g }; }
  if (e.verdict === "block") { const ok = g.verdict === "block" && (e.codes || []).every(x => codes.includes(x)); return { pass: ok, reason: ok ? "gate blocked with " + codes.join(",") : "expected block with " + (e.codes || []).join(",") + "; gate said " + g.verdict + (codes.length ? " (" + codes.join(",") + ")" : ""), gate: g }; }
  // expected pass: the gate must pass and the resolved cell / bindings must match
  let ok = g.verdict === "pass"; let why = ok ? "gate pass" : "gate " + g.verdict + ": " + (g.violations || []).map(v => v.code + " — " + v.reason).join(" | ");
  if (ok && e.annual_mip_bps != null) { const b = (g.bound_figures || []).find(x => x.role === "annual_mip"); ok = !!b && b.figure === e.annual_mip_bps + " bps"; if (!ok) why = "expected " + e.annual_mip_bps + " bps bound; got " + JSON.stringify(g.bound_figures); }
  if (ok && e.bindings) { for (const [role, val] of Object.entries(e.bindings)) { const b = (g.bound_figures || []).find(x => x.role === role); if (!b || b.figure !== "$" + val.toLocaleString("en-US")) { ok = false; why = "expected " + role + " = $" + val.toLocaleString("en-US") + "; bound: " + JSON.stringify(g.bound_figures); break; } } }
  if (ok && e.figure_usd != null) { const b = (g.bound_figures || []).find(x => x.role === e.role); ok = !!b && b.figure === "$" + e.figure_usd.toLocaleString("en-US"); if (!ok) why = "expected " + e.role + " = $" + e.figure_usd.toLocaleString("en-US") + "; bound: " + JSON.stringify(g.bound_figures); }
  if (ok && e.cap_pct != null) { const b = (g.bound_figures || []).find(x => x.role === "cap"); ok = !!b && b.figure === e.cap_pct + "%" && (!e.tier || b.cell === e.tier); if (!ok) why = "expected cap " + e.cap_pct + "% on tier '" + e.tier + "'; bound: " + JSON.stringify(g.bound_figures); }
  return { pass: ok, reason: why, gate: g };
}
