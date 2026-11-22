// WebMCP tools for financeratecalc.com: what an AI agent working inside the reader's browser can call on this page.
// Three tools, all read-only, all answered in the browser from this site's own public files (claim documents, their use
// contracts, the receipt hash history). No account, no key, nothing about the reader is sent anywhere.
//   verify_receipt   is this receipt current, corrected since, altered, or never issued?           (Receipt 1.0, /spec/receipt-1.0.md)
//   find_figure      which published figures match these words? each with its value and receipt
//   get_figure       one figure in full: the sentence to use, the qualifiers it needs, what it does not establish, its source
// The page loads this file only when the browser offers document.modelContext; other readers download nothing.
const RX = /FRC:([a-z0-9-]+):([^:\s⟧]+):([a-f0-9]{8})(?::([a-z][0-9]{4}))?/i;
const SITE = "https://financeratecalc.com";
const cache = new Map();
async function getJSON(path, signal) {
  if (cache.has(path)) return cache.get(path);
  const r = await fetch(path, { signal });
  if (!r.ok) throw new Error(path + " answered " + r.status);
  const j = await r.json(); cache.set(path, j); return j;
}
const jcs = x => Array.isArray(x) ? x.map(jcs) : (x && typeof x === "object") ? Object.fromEntries(Object.keys(x).sort().map(k => [k, jcs(x[k])])) : x;
async function h8(t) { const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(t)); return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, "0")).join("").slice(0, 8); }
const MEANING = {
  current: "This figure is current and unchanged since the receipt was issued.",
  stale: "The figure was corrected after this receipt was issued. Use current_value and its current receipt, and say the earlier value was corrected.",
  unrecognized: "This publisher never issued this receipt as written. Do not cite it.",
  "hash-current-value-mismatch": "The receipt is real but the value beside it was changed. Use current_value.",
};
const revisionOf = P => P.revision_status && P.revision_status.revised_to != null ? { revised_to: P.revision_status.revised_to, revised_in: P.revision_status.revised_in || null,
  note: "The receipt holds for the figure as first printed. The official publisher printed a different number in a later edition without marking the change." } : null;

export async function verifyReceipt(receipt, signal) {
  const m = RX.exec(String(receipt || ""));
  if (!m) return { valid: false, reason: "not a receipt: expected ⟦FRC:<claim id>:<value>:<8 hex characters>⟧" };
  const [, id, value, hash] = m;
  let P; try { P = await getJSON("/claims/" + id + ".json", signal); } catch (e) { if (signal && signal.aborted) throw e; return { valid: false, reason: "unknown claim id", id }; }
  if (!P || !P.claim) return { valid: false, reason: "unknown claim id", id };
  const now = await h8(JSON.stringify(jcs(P.claim))), legacy = await h8(JSON.stringify(P.claim, Object.keys(P.claim).sort()));
  const cur = String(P.display_value || ""); let status;
  if (hash === now || hash === legacy) status = cur === value ? "current" : "hash-current-value-mismatch";
  else { let hist = {}; try { hist = (await getJSON("/transparency/receipt-hash-history.json", signal)).hashes || {}; } catch (e) { if (signal && signal.aborted) throw e; } status = (hist[id] || []).includes(hash) ? "stale" : "unrecognized"; }
  return { valid: true, id, quoted_value: value, current_value: cur, status, meaning: MEANING[status], current_receipt: P.receipt || null, publisher_revision: revisionOf(P),
    claim_url: SITE + "/claims/" + id + ".json", checked: "in this browser, from the public claim document and the hash history (Receipt 1.0)" };
}

const words = s => String(s || "").toLowerCase().replace(/[^a-z0-9%.]+/g, " ").split(" ").filter(w => w.length > 1 || /\d/.test(w));
const STOP = new Set(["the", "of", "in", "for", "and", "to", "is", "what", "was", "were", "how", "many", "much", "often", "are", "by", "on", "at", "an", "get", "rate", "rates", "loan", "loans", "mortgage", "mortgages", "applications", "application", "percent", "percentage", "share"]);
// Plain words a reader uses, mapped to the words the claim ids use: state names to postal codes, month names to numbers, a few variants.
const STATES = { alabama: "al", alaska: "ak", arizona: "az", arkansas: "ar", california: "ca", colorado: "co", connecticut: "ct", delaware: "de", florida: "fl", georgia: "ga", hawaii: "hi", idaho: "id", illinois: "il", indiana: "in", iowa: "ia", kansas: "ks", kentucky: "ky", louisiana: "la", maine: "me", maryland: "md", massachusetts: "ma", michigan: "mi", minnesota: "mn", mississippi: "ms", missouri: "mo", montana: "mt", nebraska: "ne", nevada: "nv", "new hampshire": "nh", "new jersey": "nj", "new mexico": "nm", "new york": "ny", "north carolina": "nc", "north dakota": "nd", ohio: "oh", oklahoma: "ok", oregon: "or", pennsylvania: "pa", "rhode island": "ri", "south carolina": "sc", "south dakota": "sd", tennessee: "tn", texas: "tx", utah: "ut", vermont: "vt", virginia: "va", washington: "wa", "west virginia": "wv", wisconsin: "wi", wyoming: "wy", "district of columbia": "dc", "puerto rico": "pr" };
const MONTHS = { january: "01", february: "02", march: "03", april: "04", may: "05", june: "06", july: "07", august: "08", september: "09", october: "10", november: "11", december: "12", jan: "01", feb: "02", mar: "03", apr: "04", jun: "06", jul: "07", aug: "08", sep: "09", sept: "09", oct: "10", nov: "11", dec: "12" };
const SAME = { denied: "denial", denials: "denial", deny: "denial", rejected: "denial", rejection: "denial", conventional: "conv", delinquent: "delinquency", delinquencies: "delinquency", refi: "refinance", lenders: "lender", states: "state", metros: "metro", gaps: "gap" };
function queryWords(query) {
  const text = " " + String(query || "").toLowerCase().replace(/[^a-z0-9%.]+/g, " ") + " ", out = new Set();
  let state = null;
  for (const [name, code] of Object.entries(STATES)) if (text.includes(" " + name + " ")) state = (!state || name.length > state[0].length) ? [name, code] : state;   // "west virginia" wins over "virginia"
  if (state) { out.add(state[1]); out.add("state"); }
  const named = state ? new Set(state[0].split(" ")) : new Set();
  for (const w of words(text)) {
    if (STOP.has(w) || named.has(w)) continue;
    if (MONTHS[w] && /\b20\d\d\b/.test(text)) { out.add(MONTHS[w]); continue; }
    out.add(SAME[w] || w);
  }
  return [...out];
}
let corpus = null;
async function loadCorpus(signal) {
  if (corpus) return corpus;
  const idx = await getJSON("/claims/index.json", signal);
  let labels = {}; try { for (const f of (await getJSON("/assets/check-index.json", signal)).figures || []) labels[f.id] = f; } catch (e) { if (signal && signal.aborted) throw e; }
  corpus = (idx.claims || []).filter(c => c.receipt).map(c => { const L = labels[c.id] || {};
    const kind = /^official-/.test(c.id) ? "official report, restated as printed" : /^(conv|va|usda)-/.test(c.id) ? { conv: "conventional", va: "VA", usda: "USDA" }[c.id.split("-")[0]] + ", computed from HMDA 2025" : "FHA, computed from HMDA 2025";
    return { id: c.id, value: c.display_value, receipt: c.receipt, label: L.label || null, period: L.period || null, kind,
      idw: new Set(words(c.id.replace(/-/g, " ")).filter(w => !STOP.has(w))),
      bag: new Set(words([c.id.replace(/-/g, " "), String(c.metric || "").replace(/_/g, " "), L.label, (L.names || []).join(" ")].join(" "))) }; });
  return corpus;
}
export async function findFigure(query, limit, signal) {
  const q = queryWords(query);
  if (!q.length) return { error: "Pass a few identifying words, for example: ohio fha denial 2025, or: hud serious delinquency 2026-09." };
  const n = Math.min(Math.max(parseInt(limit, 10) || 5, 1), 20);
  // Rank: most query words found; then most of them found in the claim id itself; then the id with the fewest words the query did not ask for.
  const hits = (await loadCorpus(signal)).map(c => { const inId = q.filter(w => c.idw.has(w)).length; return { c, score: q.filter(w => c.bag.has(w)).length, inId, extra: c.idw.size - inId }; }).filter(h => h.score > 0)
    .sort((a, b) => b.score - a.score || b.inId - a.inId || a.extra - b.extra || a.c.id.localeCompare(b.c.id)).slice(0, n);
  return { query: q.join(" "), searched: corpus.length + " receipted figures", matched_words_of: q.length,
    results: hits.map(h => ({ id: h.c.id, value: h.c.value, receipt: h.c.receipt, kind: h.c.kind, label: h.c.label, period: h.c.period, words_matched: h.score })),
    next: hits.length ? "Call get_figure with an id before writing a sentence: it returns the wording, the qualifiers the figure needs and what it does not establish."
      : "Nothing matched. This site publishes US mortgage figures only (FHA, VA, USDA, conventional denial rates from HMDA; HUD, Ginnie Mae and SBA monthly figures). It has no figure for anything else, and a figure that is not here should not be attributed to it." };
}
export async function getFigure(id, signal) {
  id = String(id || "").trim().toLowerCase().replace(/^frc:claim:/, "");
  if (!/^[a-z0-9-]{3,120}$/.test(id)) return { error: "Pass a claim id such as state-oh-2025. find_figure returns ids." };
  let P; try { P = await getJSON("/claims/" + id + ".json", signal); } catch (e) { if (signal && signal.aborted) throw e; return { error: "No figure with the id " + id + " is published here. find_figure returns ids." }; }
  let C = {}; try { C = await getJSON("/claims/" + id + ".contract.json", signal); } catch (e) { if (signal && signal.aborted) throw e; }
  const value = String(P.display_value || ""), tpl = C.canonical_claim && C.canonical_claim.template;
  return { id, value, receipt: P.receipt || null,
    sentence: tpl ? tpl.replace("{value}", value) : null,
    required_qualifiers: C.required_qualifiers || null, does_not_establish: C.does_not_establish || [],
    attribution: P.attribution && P.attribution.required_text || null, license: P.attribution && P.attribution.license || null,
    publisher_revision: revisionOf(P), source: P.provenance && P.provenance.primary_source || (P.claim && P.claim.source_document) || null, reproduce: P.reproduce || null,
    claim_url: SITE + "/claims/" + id + ".json", verify_page: SITE + "/verify.html?r=" + encodeURIComponent(P.receipt || ""),
    use: "Keep the receipt next to the number. A historical aggregate: not a prediction for any person, not a ranking or recommendation of lenders, not a legal finding." };
}

const guard = fn => async (input, ctx) => { const signal = ctx && ctx.signal;
  try { return await fn(input || {}, signal); } catch (e) { if (signal && signal.aborted) throw e; return { error: e instanceof Error ? e.message : String(e) }; } };
const showOnPage = receipt => { try { const box = document.getElementById("r"); if (box && document.getElementById("out") && typeof window.go === "function") { box.value = receipt; window.go(); } } catch (e) {} };

export const tools = [
  { name: "verify_receipt",
    description: "Checks a FinanceRateCalc receipt, the bracketed code that travels with a figure from this site (⟦FRC:claim-id:value:hash⟧). Use it when an answer, article or message quotes a US mortgage statistic with such a code and the reader wants to know whether the number is still the published one. Returns one of four states: current, stale (corrected since), hash-current-value-mismatch (the value was altered) or unrecognized (never issued), with the current value and receipt.",
    inputSchema: { type: "object", properties: { receipt: { type: "string", description: "The receipt as written, with or without the ⟦ ⟧ brackets. A whole sentence that contains one receipt also works." } }, required: ["receipt"] },
    annotations: { readOnlyHint: true },
    execute: guard(async ({ receipt }, signal) => { if (typeof receipt !== "string" || !receipt.trim()) return { error: "Pass the receipt text." }; const out = await verifyReceipt(receipt, signal); if (out.valid) showOnPage(receipt.trim()); return out; }) },
  { name: "find_figure",
    description: "Finds published US mortgage figures on FinanceRateCalc by words: FHA, VA, USDA and conventional denial rates from the 2025 federal HMDA record (national, state, lender, metro), and official monthly figures from HUD, Ginnie Mae and SBA reports. Use it when the reader asks for such a statistic. Returns ids, values and receipts; it never estimates, and an empty result means the site has no such figure.",
    inputSchema: { type: "object", properties: { query: { type: "string", description: "Identifying words: place, program, lender or report, and period. Example: texas fha denial 2025." },
      limit: { type: "integer", minimum: 1, maximum: 20, default: 5, description: "How many results to return." } }, required: ["query"] },
    annotations: { readOnlyHint: true },
    execute: guard(async ({ query, limit }, signal) => typeof query === "string" ? findFigure(query, limit, signal) : { error: "Pass the query as text." }) },
  { name: "get_figure",
    description: "Returns one published figure in full by its claim id: the value, its receipt, the sentence the publisher asks to be used, the qualifiers that must stay with the number (period, population, program), what the figure does not establish, the required attribution and the source. Use it before writing any sentence that states a figure from this site.",
    inputSchema: { type: "object", properties: { id: { type: "string", description: "The claim id, for example state-oh-2025 or national-fha-denial-rate-2025." } }, required: ["id"] },
    annotations: { readOnlyHint: true },
    execute: guard(async ({ id }, signal) => getFigure(id, signal)) },
];

export async function register(modelContext) {
  const done = [];
  for (const t of tools) { try { await modelContext.registerTool(t); done.push(t.name); } catch (e) {} }
  return done;
}
