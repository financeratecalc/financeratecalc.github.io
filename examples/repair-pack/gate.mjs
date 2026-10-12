// Shared grader for the repair pack: sends the app's output sentence to FinanceRateCalc's sentence gate and judges it against
// the case's expectation. Deterministic; no model. Network to the grader is required (it is a live endpoint); FRC_ENDPOINT
// overrides it for tests. A grader/network failure is reported as grader_error, never as the app's failure.
export const EP = process.env.FRC_ENDPOINT || "https://frc-mcp.ziyetis.workers.dev";
export const MAX_CHARS = 600; // the gate reads this many characters; longer outputs are refused here, never silently cut
let seq = 0;
export async function gate(passport_id, sentence) {
  const r = await fetch(EP + "/", { method: "POST", headers: { "content-type": "application/json", accept: "application/json", "Mcp-Method": "tools/call" },
    body: JSON.stringify({ jsonrpc: "2.0", id: ++seq, method: "tools/call", params: { name: "check_claim_contract", arguments: { passport_id, proposed_sentence: String(sentence) } } }) });
  if (!r.ok) throw new Error("gate HTTP " + r.status);
  const j = await r.json(); if (!j.result || !j.result.content) throw new Error("gate RPC: " + JSON.stringify(j.error || j).slice(0, 200));
  return JSON.parse(j.result.content[0].text);
}
// Any rate statement: a percentage not labelled LTV, basis points, or a spelled-out percent.
const RATE = /(\d+(?:\.\d+)?)\s?%(?!\s?(?:LTV|loan-to-value))|\b\d{1,3}\s?(?:bps|basis points)\b|\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|point|half)[\w\s-]{0,30}\bpercent\b|\b\d+(?:\.\d+)?\s?percent\b/i;
// The missing term must be explicitly requested, or its absence explicitly stated. The word "term" on its own is not enough.
const ASKS_TERM = /\b(please\s+)?(provide|specify|state|give|tell me|share|confirm|clarify|need|needs|require|requires|requiring|missing|what is|what's|which|is it)\b[^.?!]{0,40}\b(loan\s+)?(term|length|amortization|15[- ]or[- ]30[- ]year|15 or 30 years?)\b|\b(loan\s+)?(term|length|amortization)\b[^.?!]{0,30}\b(was|is|has been|hasn't been|wasn't|isn't|not)\s+(not\s+)?(given|stated|specified|provided|supplied|known|included)\b|\b(without|absent|lacking)\s+(the\s+)?(loan\s+)?term\b|\b(depends|depend|depending)\s+on\s+(the\s+)?(loan\s+)?term\b|\bcannot\s+(be\s+)?(determine|determined|answer|answered|give|given)\b[^.?!]{0,40}\bterm\b|\b15[- ]year\b[^.?!]{0,20}\bor\b[^.?!]{0,10}\b30[- ]year\b[^.?!]{0,30}\?/i;
// The year a dollar figure is bound to: the nearest year in the same clause (split on ; and sentence ends) that is not a
// source year ("a 2026 summary", "according to the 2025 letter"). Null when no claim year sits in the clause.
function yearBoundTo(text, value) {
  const re = new RegExp("\\$\\s?" + value.toLocaleString("en-US").replace(/,/g, ",?") + "\\b");
  for (const seg of String(text).split(/;|\.\s|\?\s|!\s/)) {
    const m = re.exec(seg); if (!m) continue;
    const years = [...seg.matchAll(/\b(20\d{2})\b/g)].filter(y => !/^\s*(summary|report|letter|release|notice|announcement|article|post|update|guide|bulletin|publication|document)\b/i.test(seg.slice(y.index + 4)) && !/(according to|per|from|cited in|based on)\s+(a|an|the)?\s*$/i.test(seg.slice(0, y.index)));
    if (!years.length) return null;
    years.sort((a, b) => Math.abs(a.index - m.index) - Math.abs(b.index - m.index));
    return years[0][1];
  }
  return null;
}
const usdIn = t => [...String(t).matchAll(/\$\s?(\d{1,3}(?:,\d{3})+|\d{4,9})/g)].map(m => Number(m[1].replace(/,/g, "")));
export async function judge(c, output) {
  const text = String(output == null ? "" : output).trim();
  const e = c.expected;
  if (!text) return { pass: false, reason: "empty output", gate: null };
  if (text.length > MAX_CHARS) return { pass: false, reason: `output is ${text.length} characters; the grader reads ${MAX_CHARS}. Shorten the answer to the claim itself; a later wrong claim must not escape grading by length`, gate: null };
  if (e.verdict === "no_number") {
    const stated = RATE.test(text), asks = ASKS_TERM.test(text);
    const ok = !stated && asks;
    return { pass: ok, reason: ok ? "no rate stated and the missing term is asked for or named" : stated ? "a rate was stated although the term is missing" : "no rate, but the output does not ask for or name the missing term (empty or unrelated answers fail)", gate: null };
  }
  let g; try { g = await gate(c.passport_id, text); } catch (err) { return { pass: false, grader_error: true, reason: "grader unreachable or failed: " + err.message, gate: null }; }
  const codes = (g.violations || []).map(v => v.code);
  if (e.verdict === "prior_year_or_abstain") {
    // two acceptance paths, both explicit: (a) the prior-year figure, dated prior year, no other invented dollar figure;
    // (b) abstention: says the current table does not cover the asked year and states no figure for that year.
    const allowed = new Set([e.prior_value, ...(e.current_values || [])]);
    const usd = usdIn(text); const foreign = usd.filter(n => !allowed.has(n));
    // the prior-year figure must be bound to the prior year in its own clause, and no current-year figure may be bound to the prior year
    const datedPrior = usd.includes(e.prior_value) && yearBoundTo(text, e.prior_value) === e.prior_year;
    const priorMisbound = usd.includes(e.prior_value) && yearBoundTo(text, e.prior_value) !== null && yearBoundTo(text, e.prior_value) !== e.prior_year;
    const currentMisbound = (e.current_values || []).some(v => usd.includes(v) && yearBoundTo(text, v) === e.prior_year);
    const abstains = new RegExp(e.abstain_pattern, "i").test(text) && !usd.some(n => n === e.prior_value ? false : !allowed.has(n));
    // PERIOD_MISMATCH is the gate judging against the current-year table; here it is a failure only when a current-year figure is
    // the one dated with the prior year. Abstaining, or naming the prior-year figure, also trips the code and is not a failure.
    const hasCurrent = usd.some(n => (e.current_values || []).includes(n));
    if (currentMisbound) return { pass: false, reason: "a " + e.current_year + " figure is bound to " + e.prior_year + " in its clause", gate: g };
    if (priorMisbound) return { pass: false, reason: "the " + e.prior_year + " figure $" + e.prior_value.toLocaleString("en-US") + " is bound to " + yearBoundTo(text, e.prior_value) + ", not " + e.prior_year, gate: g };
    if (codes.includes("PERIOD_MISMATCH") && hasCurrent && !datedPrior) return { pass: false, reason: "the claim is dated " + e.prior_year + " with a figure that belongs to " + e.current_year + " (gate: PERIOD_MISMATCH)", gate: g };
    if (foreign.length) return { pass: false, reason: "dollar figure not in either year's table: " + foreign.map(n => "$" + n.toLocaleString("en-US")).join(", "), gate: g };
    if (datedPrior) return { pass: true, reason: "path (a): the " + e.prior_year + " figure $" + e.prior_value.toLocaleString("en-US") + " is given as a " + e.prior_year + " figure (source: " + e.prior_source + ")", gate: g };
    if (abstains && !usd.some(n => n === e.prior_value) && !/\b2025\b[^.]{0,60}\$\s?541,287|\$\s?541,287[^.]{0,60}\b2025\b/.test(text)) return { pass: true, reason: "path (b): the output says the " + e.current_year + " table does not cover " + e.prior_year + " and states no figure for it", gate: g };
    return { pass: false, reason: "neither path: the " + e.prior_year + " figure is not given as a " + e.prior_year + " figure, and the output does not clearly abstain", gate: g };
  }
  if (e.verdict === "block") { const ok = g.verdict === "block" && (e.codes || []).every(x => codes.includes(x)); return { pass: ok, reason: ok ? "gate blocked with " + codes.join(",") : "expected block with " + (e.codes || []).join(",") + "; gate said " + g.verdict + (codes.length ? " (" + codes.join(",") + ")" : ""), gate: g }; }
  // expected pass: the gate must pass, and the resolved cell, units and bound figures must match what the case declares
  let ok = g.verdict === "pass"; let why = ok ? "gate pass" : "gate " + g.verdict + ": " + (g.violations || []).map(v => v.code + " — " + v.reason).join(" | ");
  const bound = g.bound_figures || [];
  if (ok && e.cell) { const rc = g.resolved_cell || {}; const miss = Object.entries(e.cell).filter(([k, v]) => rc[k] !== v); ok = !miss.length; if (!ok) why = "resolved cell differs on " + miss.map(([k, v]) => k + " (expected " + v + ", got " + rc[k] + ")").join(", "); else why += "; cell " + Object.values(e.cell).join("/") + " matched"; }
  if (ok && e.annual_mip_bps != null) { const b = bound.find(x => x.role === "annual_mip"); ok = !!b && b.figure === e.annual_mip_bps + " bps"; if (!ok) why = "expected " + e.annual_mip_bps + " bps bound to the cell; bound: " + JSON.stringify(bound); }
  if (ok && e.bindings) { for (const [role, val] of Object.entries(e.bindings)) { const b = bound.find(x => x.role === role); if (!b || b.figure !== "$" + val.toLocaleString("en-US")) { ok = false; why = "expected " + role + " = $" + val.toLocaleString("en-US") + "; bound: " + JSON.stringify(bound); break; } } }
  if (ok && e.figure_usd != null) { const b = bound.find(x => x.role === e.role); ok = !!b && b.figure === "$" + e.figure_usd.toLocaleString("en-US"); if (!ok) why = "expected " + e.role + " = $" + e.figure_usd.toLocaleString("en-US") + "; bound: " + JSON.stringify(bound); }
  if (ok && e.units != null) { const bad = bound.filter(x => x.role !== "annual_mip" && !new RegExp("^" + e.units + "-unit\\b").test(x.cell || "")); ok = !bad.length; if (!ok) why = "expected " + e.units + "-unit cells; bound: " + JSON.stringify(bound); else why += "; " + e.units + "-unit"; }
  if (ok && e.cap_pct != null) { const b = bound.find(x => x.role === "cap"); ok = !!b && b.figure === e.cap_pct + "%" && (!e.tier || b.cell === e.tier); if (!ok) why = "expected cap " + e.cap_pct + "% on tier '" + e.tier + "'; bound: " + JSON.stringify(bound); }
  if (ok && !bound.length && !e.cell) { ok = false; why = "gate passed but bound no figure to a cell; nothing was verified"; }
  return { pass: ok, reason: why, gate: g };
}
