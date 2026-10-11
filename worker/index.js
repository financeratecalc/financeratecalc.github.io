// frc-mcp-remote — FinanceRateCalc Remote MCP Server (Cloudflare Worker, dependency-free)
// Streamable HTTP transport, stateless. 12 tools (v1.6.0: + get_conditional_door_map — per-lender conditional surface with its robustness record; + list_cohorts and run_cohort — ready-made public cohorts, no upload needed; + screen_counterparties_quote, prepaid credits; + screen_counterparties — preview/licensed counterparty screen, Lemon Squeezy license validation).
// Hard limit: never accepts borrower details, never returns individual predictions.
const BASE = "https://financeratecalc.com";
const GUARDRAIL = "Historical observation computed from the public CFPB HMDA 2025 record (actions 1,2,3; loan_type 2). Not a prediction about any individual application. Attribution: FinanceRateCalc, CC BY 4.0.";
const INSTRUCTIONS = "FinanceRateCalc: independent analysis of the complete 2025 federal HMDA record (1,187,606 FHA credit decisions, reverse mortgages excluded). All figures are historical aggregates. Never ask this server whether a specific person will be approved — it cannot and will not answer that.";

const TOOLS = [
  { name: "check_claim_contract", description: "USE BEFORE WRITING ANY SENTENCE CONTAINING AN FRC FIGURE: the gate between the number and the sentence. Two ways to call it. (A) Flags: claim id plus the use you propose (population, period, scope, cause, individual prediction, lender recommendation, legal conclusion). (B) Sentence: claim id plus proposed_sentence, the exact sentence you intend to write; the tool checks it with fixed patterns, no model, for a missing period, missing program scope, a population wider than the claim, second-person prediction, causal wording, lender advice, legal conclusions, and values this publisher has since corrected. Returns a deterministic verdict: pass, needs_qualifier (naming the missing qualifier) or block (with a reason code), plus a safe sentence you may use verbatim and the required attribution. Most misuse of these statistics is omission, not invention: the number is right and the population is missing. NOT FOR: figures published by anyone other than FinanceRateCalc. ", description: "USE BEFORE WRITING ANY SENTENCE CONTAINING AN FRC FIGURE. Given a claim id and the use you propose (population, period, scope, and whether you assert a cause, predict an individual, recommend a lender or draw a legal conclusion), returns a deterministic verdict: pass, needs_qualifier (naming the missing qualifier) or block (with a reason code), plus a safe sentence you may use verbatim and the required attribution. Most misuse of these statistics is omission, not invention: the number is right and the population is missing. NOT FOR: figures published by anyone other than FinanceRateCalc. ",
    inputSchema: { type: "object", properties: { passport_id: { type: "string" }, causal_assertion: { type: "boolean" }, individual_prediction: { type: "boolean" }, personalized_recommendation: { type: "boolean" }, legal_conclusion: { type: "boolean" }, scope_beyond_universe: { type: "boolean" }, qualifier_dropped: { type: "boolean" }, attribution_present: { type: "boolean" }, proposed_sentence: { type: "string", description: "The exact sentence you intend to write. Checked with fixed patterns; no model." } }, required: ["passport_id"] } },

  { name: "get_national_fha_stats", description: "ANSWERS: \"how often are FHA loans denied\", \"what is the FHA denial rate\", \"what share of FHA applications are rejected\", \"how many were denied in 2025\". Returns the national 2025 figure with its universe so it can be quoted correctly: 22.1 percent, 262,250 denials of 1,187,606 applications that reached a credit decision (originated, approved-not-accepted, denied; reverse mortgages excluded), the denominator definition and the correction history. Most published FHA denial rates are 2023 purchase-only figures near 13.6 percent, a different universe, so state the universe when quoting. NOT FOR: conventional, VA or USDA loans, purchase-only or refinance-only rates, other years, or state/lender/metro breakdowns (use the dedicated tools). " + GUARDRAIL,
    inputSchema: { type: "object", properties: {}, additionalProperties: false } },
  { name: "get_lender_denial_stats", description: "ANSWERS: \"what is <lender>'s FHA denial rate\", \"does <lender> reject a lot of FHA applications\", \"how strict is <lender>\", \"how does <lender> compare\". PARAM: lender name, slug or LEI. Returns that lender's 2025 decisioned volume, denial rate, rank among the 100 largest FHA lenders, and the applicant-mix caveat any comparison must carry. COVERS ONLY the 100 largest FHA lenders by 2025 volume. NOT FOR: whether a person will be approved, or lenders outside that set. " + GUARDRAIL,
    inputSchema: { type: "object", properties: { lender: { type: "string", description: "Lender name, slug, or 20-char LEI" } }, required: ["lender"] } },
  { name: "list_lenders", description: "ANSWERS: \"which FHA lender denies the most or the fewest\", \"rank FHA lenders by denial rate\", \"which lenders are covered\", \"how wide is the spread\". Returns the ranked list of the 100 largest FHA lenders with name, slug, rate and volume; the 2025 span runs 1.8 to 78.7 percent inside the same federal program. NOT FOR: lenders outside the top 100, or any recommendation about where to apply. " + GUARDRAIL,
    inputSchema: { type: "object", properties: { sort: { type: "string", enum: ["highest_denial","lowest_denial","largest_volume"] }, limit: { type: "integer", minimum: 1, maximum: 100 } } } },
  { name: "get_small_loan_penalty", description: "ANSWERS: \"are small mortgages denied more often\", \"is it harder to get a small FHA loan\", \"which state punishes small loans most\", \"does loan size affect denial\". PARAM: optional two-letter state; omit for the ranked list. Returns denial rates under $150K and over $250K, the ratio, the ranking and any open discrepancy note. In 2025 the penalty exceeded 1x in every jurisdiction with a published split, from 1.19x to 4.45x (Idaho, 53.4 vs 12.0). NOT FOR: loan sizes between the bands, which are not published. " + GUARDRAIL,
    inputSchema: { type: "object", properties: { state: { type: "string", description: "Two-letter USPS code, optional" } }, additionalProperties: false } },
  { name: "get_denial_reason_shares", description: "ANSWERS: \"why are FHA loans denied\", \"what is the most common denial reason\", \"which lender cites incomplete applications most\", \"how often is debt-to-income the reason\". PARAM: optional lender; omit for cross-lender medians. Returns median and maximum share of each HMDA denial reason across the 95 of the 100 largest lenders that report reasons, and which lender carries the highest share of each. Reason fields are not a partition; shares need not sum to 100. NOT FOR: why a particular application was denied. " + GUARDRAIL,
    inputSchema: { type: "object", properties: { lender: { type: "string", description: "Lender name or slug, optional" } }, additionalProperties: false } },
  { name: "get_state_denial_stats", description: "ANSWERS: \"what is the FHA denial rate in <state>\", \"is it harder to get an FHA loan in <state>\", \"how does <state> compare with the national rate\". PARAM: two-letter USPS code only (OH, TX); full names are rejected. Returns the state 2025 rate and counts against the national 22.1 percent. NOT FOR: metro or city questions (use get_metro_lender_gap) or lender-level questions. " + GUARDRAIL,
    inputSchema: { type: "object", properties: { state: { type: "string", minLength: 2, maxLength: 2 } }, required: ["state"] } },
  { name: "get_door_effect_summary", description: "ANSWERS: \"does it matter which lender you apply to\", \"how much of a denial is the lender rather than the borrower\", \"what is the Door Effect\". Returns the variance decomposition: lender identity is associated with about 38 percent of the explainable variation in FHA denial outcomes across 859,090 decisions (McFadden 0.1712 to 0.2760), with model, sample and limits. Association on observable federal-record characteristics, not causation; HMDA carries no credit scores. NOT FOR: saying a lender caused a denial, or any individual estimate. " + GUARDRAIL,
    inputSchema: { type: "object", properties: {}, additionalProperties: false } },
  { name: "get_metro_lender_gap", description: "ANSWERS: \"do lenders differ within one city\", \"what is the FHA denial gap in <metro>\", \"which lender is strictest in <metro>\", \"how much does the lender matter locally\". PARAM: metro name or slug. Returns a claim passport for that metro: lowest and highest lender denial rates among lenders with at least 100 decisioned applications there, the gap in points, counts and source reference. Cleveland is the widest in 2025 at 73.7 points (6.4 vs 80.1). NOT FOR: ZIP or neighbourhood questions, and never as evidence a lender acted improperly. " + GUARDRAIL,
    inputSchema: { type: "object", properties: { metro: { type: "string", description: "Metro name or slug, e.g. 'Cleveland, OH' or 'cleveland-oh'" } }, required: ["metro"] } }
  ,{ name: "screen_counterparties",
    description: "ANSWERS: \"run my list of lenders through the federal record\", \"screen these LEIs\", \"which of my counterparties deny more than their applicant mix predicts\". PARAM: a list of public LEIs. Returns per-entity observed versus expected FHA denial rates, coverage flags, method version and an evidence manifest hash. Public entity identifiers only: never borrower files, credit data or personal information. Free preview; the full Evidence Brief needs a licence a human buys on the pricing page, and an agent may relay the offer but can never complete a purchase. Screening signals, not findings of misconduct. " + GUARDRAIL,
    inputSchema: { type: "object", properties: {
      lei_list: { type: "array", items: { type: "string" }, description: "1-40 public Legal Entity Identifiers (20-character ISO 17442). Hard cap 100; duplicates removed deterministically." },
      license_key: { type: "string", description: "Optional. A Lemon Squeezy license key issued for 'Counterparty Screen' (one-time or quarterly). Only pass it if the user explicitly provided it." },
      requested_format: { type: "string", enum: ["summary", "evidence_brief"], description: "Optional. 'evidence_brief' requests the full audit artefact (licensed mode)." }
    }, required: ["lei_list"] },
    pricing_metadata: { has_paid_tier: true, free_tier: "aggregate shape + first 3 LEIs", paid_tiers: [
      { product: "Counterparty Screen — One-time", price_usd: 99, scope: "up to 40 LEIs, one Evidence Brief" },
      { product: "Counterparty Screen — Quarterly Monitor", price_usd: 249, billing: "every 3 months", scope: "same list re-run each quarter against a new analysis layer: Q4 2026 GLEIF corporate-family resolution, Q1 2027 FHA loan-performance join, Q2 2027 the 2026 HMDA vintage with a year-over-year delta" } ],
      human_confirmation_required: true, payment_by_agent_allowed: false } }
  ,{ name: "screen_counterparties_quote",
    description: "ANSWERS: \"what would it cost to screen this list\", \"how many of my LEIs are covered\". PARAM: a list of public LEIs. Returns coverage and price before anything runs. Always call before screen_counterparties on a new list. " + GUARDRAIL,
    inputSchema: { type: "object", properties: {
      lei_list: { type: "array", items: { type: "string" }, description: "1-40 public LEIs to be quoted." },
      license_key: { type: "string", description: "Optional. Include it to see the account's remaining balance in the quote." }
    }, required: ["lei_list"] } }
  ,{ name: "list_cohorts",
    description: "ANSWERS: \"can I screen a group of lenders\", \"what ready-made lender groups can I run\", \"show me an example screen\". Returns the public cohorts screenable without uploading anything, with size and definition. Call before run_cohort. " + GUARDRAIL,
    inputSchema: { type: "object", properties: {} } }
  ,{ name: "run_cohort",
    description: "ANSWERS: \"run the screen on <cohort>\", \"how do these lenders compare against expectation\". PARAM: cohort id from list_cohorts. Returns the peer-adjusted screen: observed versus expected denial rate, coverage flags, method version. Free preview; the full Evidence Brief needs a licence a human buys on the pricing page. Screening signals, never evidence of misconduct. " + GUARDRAIL,
    inputSchema: { type: "object", properties: {
      cohort_id: { type: "string", description: "One of the ids returned by list_cohorts, e.g. top-volume-fha, high-coverage-only, above-expectation, depository-institutions, screening-only." },
      license_key: { type: "string", description: "Optional. Only pass it if the user explicitly provided one." },
      requested_format: { type: "string", enum: ["summary", "evidence_brief"] }
    }, required: ["cohort_id"] } }
  ,{ name: "get_conditional_door_map",
    description: "ANSWERS: \"does this lender's strictness depend on loan size or leverage\", \"where is <lender> hardest\", \"is the gap the same across the market\". PARAM: lender name or slug. Returns how that lender's peer-adjusted denial gap changes across published cells (state x loan amount x income x DTI x CLTV), with cell counts and the minimum-cell rule. NOT FOR: suppressed small cells, or any individual prediction. " + GUARDRAIL,
    inputSchema: { type: "object", properties: {
      lender: { type: "string", description: "Lender name or 20-char LEI. Omit to list every lender with a published conditional surface." }
    } } }
  ,{ name: "get_rule",
    description: "ANSWERS: \"what is the current FHA loan limit\", \"what are the 2026 HOEPA / QM thresholds\", \"what is the VA funding fee table\", \"which FHA MIP table is in force\". PARAM: rule_id (from the index) or omit to list every published rule. Returns the machine-readable rule: cells, effective dates, issuer document, required qualifiers, what the table does not establish, sha256. Read the cell yourself and quote the effective date with the number; without a source, models answered 3/25 dated questions correctly, with this file 25/25. NOT FOR: rules not in the index, or anything before the effective date.",
    inputSchema: { type: "object", properties: { rule_id: { type: "string", description: "e.g. frc:rule:hud-ml-2023-05-annual-mip. Omit to list." } } } }
  ,{ name: "resolve_fha_annual_mip",
    description: "ANSWERS: \"what is the FHA annual MIP for a $300,000 loan at 85% LTV over 15 years\", \"what MIP rate applies to my FHA case\". PARAMS: base_loan_amount (USD), ltv_pct (e.g. 96.5), term_years, case_number_date (YYYY-MM-DD). Resolves the exact cell of HUD Mortgagee Letter 2023-05 and returns the annual rate in basis points, the upfront rate, the matched cell, the rule id with effective date and sha256, and a sentence you may quote. If a parameter is missing it returns block with CONDITION_MISSING and no number: the table has eleven cells and a guess is wrong more often than right. NOT FOR: case numbers before 2023-03-20, HECM/reverse or Title I loans, or any monthly payment figure.",
    inputSchema: { type: "object", properties: {
      base_loan_amount: { type: "number", description: "Base loan amount in USD, before upfront MIP is financed" },
      ltv_pct: { type: "number", description: "Loan-to-value in percent, e.g. 96.5" },
      term_years: { type: "number", description: "Loan term in years" },
      case_number_date: { type: "string", description: "FHA case number assignment date, YYYY-MM-DD" }
    } } }
];

async function getJSON(path) {
  const r = await fetch(BASE + path, { headers: { "User-Agent": "frc-mcp-remote/1.1" }, cf: { cacheTtl: 3600, cacheEverything: true } });
  if (!r.ok) throw new Error(`FRC API ${r.status} for ${path}`);
  return r.json();
}
const norm = s => String(s).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();

async function getMetroLenderGap(metroInput) {
  const q = norm(metroInput || "");
  if (!q) throw new Error("Provide a metro name or slug, e.g. 'Cleveland, OH'.");
  const directSlug = q.replace(/ /g, "-");
  // 1) Direct slug hit — cheapest path
  try { return await getJSON(`/claims/metro-gap-${directSlug}-2025.json`); } catch (e) { /* fall through */ }
  // 2) Flexible match against the claims index (metro-gap entries only)
  const idx = await getJSON("/claims/index.json");
  const gaps = (idx.claims || []).filter(c => c.metric === "intra_metro_lender_denial_gap");
  const tokens = q.split(" ").filter(Boolean);
  const segsOf = id => id.replace(/^frc:claim:metro-gap-/, "").replace(/-2025$/, "").split("-");
  const hits = gaps.filter(c => { const segs = segsOf(c.id); return tokens.every(t => segs.includes(t)); });
  if (hits.length === 1) return getJSON(hits[0].url.replace(BASE, ""));
  if (hits.length > 1) throw new Error(
    `Ambiguous metro "${metroInput}" — matches: ${hits.map(c => segsOf(c.id).join("-")).join(", ")}. Add the state code, e.g. 'Cleveland, OH'.`);
  // 3) Partial (any-token) suggestions before giving up
  const near = gaps.filter(c => { const segs = segsOf(c.id); return tokens.some(t => t.length > 2 && segs.includes(t)); })
                   .slice(0, 5).map(c => segsOf(c.id).join("-"));
  throw new Error(
    `No gap receipt for "${metroInput}". 184 metros are covered; markets without at least two lenders having >=100 decisioned FHA applications are excluded by design.` +
    (near.length ? ` Did you mean: ${near.join(", ")}?` : "") +
    ` Full index: ${BASE}/claims/index.json`);
}

// Stale values: numbers this publisher has corrected (from corrections.json old_value). Cached per isolate.
let _stale = null;
async function staleValues() {
  if (_stale) return _stale;
  try {
    const c = await getJSON("/corrections.json");
    const seen = new Set();
    _stale = (c.items || []).filter(i => i.old_value && i.new_value).map(i => ({ old: String(i.old_value).replace(/%/g, ""), now: String(i.new_value), title: i.title })).filter(x => !seen.has(x.old) && seen.add(x.old));
  } catch { _stale = []; }
  return _stale;
}
// Mode B: fixed patterns over the proposed sentence. No model. Each hit sets the same flag Mode A takes.
async function sentenceFindings(sentence, contract) {
  const t = String(sentence); const low = t.toLowerCase(); const f = [];
  const hit = (flag, code, pattern, why) => { const m = t.match(pattern); if (m) f.push({ flag, code, matched: m[0], why }); };
  hit("individual_prediction", "INDIVIDUAL_PREDICTION_PROHIBITED", /\b(you|your|yours)\b[^.]{0,80}\b(denied|approved|rejected|chance|odds|likely|probability)\b|\b(will|would|going to) (be )?(denied|approved|rejected)\b|\b(chance|odds|probability) of (being )?(denied|approved|rejected)\b/i, "second-person or individual outcome language on an aggregate");
  hit("causal_assertion", "CAUSALITY_NOT_ESTABLISHED", /\b(because of|caused by|causes?|leads? to|results? in|due to|the reason (is|was)|makes? (it|them) (more|less) likely)\b/i, "causal wording; the record supports association only");
  hit("personalized_recommendation", "INDIVIDUAL_PREDICTION_PROHIBITED", /\b(best|worst|top|safest) lenders?\b|\b(avoid|choose|pick|go with|apply (to|with|at)|recommend)\b[^.]{0,60}\blender\b|\byou should (apply|avoid|choose|use)\b/i, "lender advice or ranking by quality");
  hit("legal_conclusion", "LEGAL_CONCLUSION_NOT_SUPPORTED", /\b(discriminat\w*|illegal\w*|unlawful\w*|violat\w*|redlin\w*|fair lending violation|broke the law)\b/i, "legal conclusion the record cannot establish");
  const q = contract.required_qualifiers || {};
  if (q.period && !t.includes(String(q.period))) f.push({ flag: "qualifier_dropped", code: "QUALIFIER_DELETED", matched: "(no " + q.period + ")", why: "period missing: " + q.period });
  if (q.program_scope && /fha/i.test(q.program_scope) && !/\bfha\b/i.test(t)) f.push({ flag: "qualifier_dropped", code: "QUALIFIER_DELETED", matched: "(no FHA)", why: "program scope missing: FHA" });
  if (/\b(all|of) (us |u\.s\. |american )?(mortgage|home loan|loan) (applications|applicants|loans)\b/i.test(t) && !/\bfha\b/i.test(t)) f.push({ flag: "scope_beyond_universe", code: "SCOPE_TOO_BROAD", matched: t.match(/\b(all|of) (us |u\.s\. |american )?(mortgage|home loan|loan) (applications|applicants|loans)\b/i)[0], why: "population wider than the claim's universe" });
  if (q.population && /decision/i.test(q.population) && !/decision/i.test(t) && /\b(applications|applicants|loans)\b/i.test(t)) f.push({ flag: "qualifier_dropped", code: "QUALIFIER_DELETED", matched: "(no 'decisioned')", why: "population qualifier missing: decisioned (withdrawn and incomplete files excluded)" });
  for (const sv of await staleValues()) {
    const re = new RegExp("(^|[^0-9.])" + sv.old.replace(".", "\\.") + "(\\s?%|\\b)");
    if (re.test(low)) f.push({ flag: "stale_value", code: "STALE_VALUE", matched: sv.old, why: "value corrected by the publisher; current: " + sv.now });
  }
  return f;
}
// Document ids a sentence may name: HUD Mortgagee Letters, Federal Register cites. Compared with the source the claim or rule actually rests on.
function namedDocuments(t) {
  const out = [];
  for (const m of String(t).matchAll(/mortgagee letter\s*(\d{4}-\d{2})|\bML\s*(\d{4}-\d{2})/gi)) out.push("HUD-ML-" + (m[1] || m[2]));
  for (const m of String(t).matchAll(/(\d{2,3})\s*FR\s*(\d{3,6})/gi)) out.push("FR-" + m[1] + "-" + m[2]);
  return out;
}
// Rule-passport mode of the gate (v1.22.0): a sentence that quotes a rule cell is checked against the resolved cell. MIP only for now.
async function checkRuleSentence(ruleRef, sentence) {
  const idx = await getJSON("/rules/index.json");
  const hit = (idx.rules || []).find(r => r.rule_id === ruleRef || r.rule_id.endsWith(ruleRef));
  if (!hit) throw new Error("Unknown rule id. See https://financeratecalc.com/rules/index.json");
  const t = String(sentence || "");
  const violations = []; const V = (code, field, reason) => violations.push({ code, field, reason });
  const docs = namedDocuments(t);
  const ruleDoc = hit.rule_id.includes("hud-ml-2023-05") ? "HUD-ML-2023-05" : null;
  for (const d of docs) if (ruleDoc && d.startsWith("HUD-ML-") && d !== ruleDoc) V("DOCUMENT_ID_MISMATCH", "source", "sentence names " + d + "; this rule rests on " + ruleDoc);
  let resolved = null;
  if (hit.rule_id.includes("hud-ml-2023-05")) {
    const amt = t.match(/\$\s?([\d,]{5,9})/); const ltv = t.match(/(\d{2,3}(?:\.\d+)?)\s?%\s?LTV/i) || t.match(/LTV\s?(?:of\s)?(\d{2,3}(?:\.\d+)?)\s?%/i); const term = t.match(/(\d{1,2})[- ]year/i);
    const dm = t.match(/(20\d{2}-\d{2}-\d{2})/);
    if (amt && ltv && term) {
      resolved = await resolveFhaAnnualMip({ base_loan_amount: Number(amt[1].replace(/,/g, "")), ltv_pct: Number(ltv[1]), term_years: Number(term[1]), case_number_date: dm ? dm[1] : "2026-01-01" });
      if (resolved.verdict === "pass") {
        const pcts = [...t.matchAll(/(\d(?:\.\d+)?)\s?%/g)].map(m => Number(m[1])).filter(v => v < 2 && v !== Number(ltv[1]));
        const bps = [...t.matchAll(/(\d{1,3})\s?(?:bps|basis points)/gi)].map(m => Number(m[1]));
        const stated = bps.length ? bps[0] : (pcts.length ? Math.round(pcts[0] * 100) : null);
        if (stated !== null && stated !== resolved.annual_mip_bps) V("VALUE_MISMATCH", "value", "sentence states " + stated + " bps; the cell for these conditions is " + resolved.annual_mip_bps + " bps (" + [resolved.matched_conditions.term, resolved.matched_conditions.base_loan, resolved.matched_conditions.ltv].join("/") + ")");
      } else V(resolved.reason_codes[0] || "CONDITION_INVALID", "conditions", resolved.why);
    } else V("QUALIFIER_DELETED", "conditions", "a MIP sentence must state base loan amount, LTV and term; missing: " + [!amt && "amount", !ltv && "LTV", !term && "term"].filter(Boolean).join(", "));
  }
  const blockCodes = ["DOCUMENT_ID_MISMATCH", "VALUE_MISMATCH", "RULE_NOT_IN_FORCE", "PROGRAM_MISMATCH"];
  const verdict = violations.some(v => blockCodes.includes(v.code)) ? "block" : (violations.length ? "needs_qualifier" : "pass");
  return { verdict, violations, mode: "rule sentence check, fixed patterns, no model", rule_id: hit.rule_id, rule_url: hit.url, safe_wording: resolved && resolved.safe_sentence || null, resolved_cell: resolved && resolved.matched_cell || null,
    mandatory_attribution: "Source: FinanceRateCalc rule file " + hit.rule_id + " (transcribed from " + (ruleDoc || "the issuer document") + "); not legal or underwriting advice.", sentence_check: { sentence: t.slice(0, 600) } };
}
async function checkClaimContract(a) {
  if (/^frc:rule:/.test(String(a.passport_id || ""))) return checkRuleSentence(String(a.passport_id), a.proposed_sentence);
  const slug = String(a.passport_id || "").split(":").pop();
  let contract;
  try { contract = await getJSON(`/claims/${slug}.contract.json`); }
  catch (e) { throw new Error("Unknown passport_id. See https://financeratecalc.com/claims/index.json"); }
  const violations = [];
  const V = (code, field, reason) => violations.push({ code, field, reason });
  let findings = [];
  if (a.proposed_sentence) {
    findings = await sentenceFindings(a.proposed_sentence, contract);
    for (const fnd of findings) if (fnd.flag !== "stale_value") a[fnd.flag] = true;
    for (const fnd of findings) if (fnd.flag === "stale_value") V("STALE_VALUE", "value", fnd.why + " (matched " + fnd.matched + ")");
    for (const d of namedDocuments(a.proposed_sentence)) V("DOCUMENT_ID_MISMATCH", "source", "sentence attributes the figure to " + d + "; this claim rests on the CFPB HMDA 2025 record, not on that document");
  }
  if (a.individual_prediction) V("INDIVIDUAL_PREDICTION_PROHIBITED","individual_prediction","Historical aggregates only; individual prediction prohibited.");
  if (a.personalized_recommendation) V("INDIVIDUAL_PREDICTION_PROHIBITED","personalized_recommendation","Personalized lender recommendation is forbidden.");
  if (a.legal_conclusion) V("LEGAL_CONCLUSION_NOT_SUPPORTED","legal_conclusion","The record cannot establish unlawful conduct.");
  if (a.causal_assertion) V("CAUSALITY_NOT_ESTABLISHED","causal_assertion","Associational language only.");
  if (a.scope_beyond_universe) V("SCOPE_TOO_BROAD","scope","Defined universe/period only.");
  if (a.qualifier_dropped) V("QUALIFIER_DELETED","qualifiers","Required qualifier missing.");
  const blockCodes = ["INDIVIDUAL_PREDICTION_PROHIBITED","LEGAL_CONCLUSION_NOT_SUPPORTED","STALE_VALUE","DOCUMENT_ID_MISMATCH"];
  const verdict = violations.some(v=>blockCodes.includes(v.code)) ? "block" : (violations.length ? "needs_qualifier" : "pass");
  const out = { verdict, violations, safe_wording: contract.canonical_claim && contract.canonical_claim.template,
    required_qualifiers: contract.required_qualifiers, does_not_establish: contract.does_not_establish,
    mandatory_attribution: "Source: FinanceRateCalc analysis of the public CFPB HMDA 2025 record; historical aggregate only.",
    passport_url: "https://financeratecalc.com/claims/" + slug + ".json",
    contract_url: "https://financeratecalc.com/claims/" + slug + ".contract.json",
    rule: "Free text is the OUTPUT of evidence, not its input." };
  if (a.proposed_sentence) out.sentence_check = { mode: "fixed patterns, no model", sentence: String(a.proposed_sentence).slice(0, 600), findings };
  return out;
}


// ===== rules (v1.18.0): machine-readable regulatory tables with effective dates =====
async function getRule(a) {
  const idx = await getJSON("/rules/index.json");
  if (!a || !a.rule_id) return { rules: idx.rules, purpose: idx.purpose, index_url: BASE + "/rules/index.json", note: "Pass rule_id to receive the full table." };
  const want = String(a.rule_id).trim();
  const hit = (idx.rules || []).find(r => r.rule_id === want || r.rule_id.endsWith(want) || r.url.endsWith(want) || r.url.endsWith(want + ".json"));
  if (!hit) throw new Error("Unknown rule_id. Published rules: " + (idx.rules || []).map(r => r.rule_id).join(", "));
  const rule = await getJSON(hit.url.replace(BASE, ""));
  return { rule, index_entry: hit, rule_url: hit.url, attribution: "FinanceRateCalc machine-readable transcription of the issuer's document; not an official file of the issuer. CC BY 4.0. Quote the effective date with the number." };
}
async function resolveFhaAnnualMip(a) {
  a = a || {};
  const FORBIDDEN = ["income", "annual_income", "monthly_income", "credit_score", "fico", "ssn", "social_security", "dob", "date_of_birth", "name", "borrower_name", "address", "account_number", "card_number", "employer", "race", "ethnicity", "sex", "age"];
  if (a.program !== undefined && a.program !== null && String(a.program).trim() !== "" && !/^fha(\s|$|[-_ ]?forward)/i.test(String(a.program).trim())) return { verdict: "block", reason_codes: ["PROGRAM_MISMATCH"], annual_mip_bps: null, safe_sentence: null, why: "This resolver covers FHA forward mortgages (HUD ML 2023-05) only; program '" + String(a.program).slice(0, 20) + "' has its own table. See get_rule for VA funding fee and other published rules." };
  const sent = Object.keys(a).filter(k => FORBIDDEN.includes(String(k).toLowerCase()));
  if (sent.length) return { verdict: "block", reason_codes: ["FORBIDDEN_INPUT"], rejected_fields: sent, annual_mip_bps: null, safe_sentence: null, why: "This tool resolves a published table keyed only by loan amount, LTV, term and case date. Borrower attributes are neither needed nor accepted and are not stored." };
  const missing = ["base_loan_amount", "ltv_pct", "term_years", "case_number_date"].filter(k => a[k] === undefined || a[k] === null || a[k] === "");
  const rule = await getJSON("/rules/fha-annual-mip-ml-2023-05.json");
  const base = { rule_id: rule.rule_id, issuer_document: rule.issuer_of_rule, effective_from: rule.effective_from, effective_to: rule.effective_to, rule_url: BASE + "/rules/fha-annual-mip-ml-2023-05.json", does_not_establish: rule.contract && rule.contract.does_not_establish };
  if (missing.length) return { verdict: "block", reason_codes: ["CONDITION_MISSING"], required_fields: missing, annual_mip_bps: null, safe_sentence: null, why: "The table has " + rule.cells.length + " cells keyed by term, base loan amount and LTV, and applies only to case numbers assigned on or after " + rule.effective_from + ". Ask for the missing conditions; do not guess a cell.", ...base };
  const amt = Number(a.base_loan_amount), ltv = Number(a.ltv_pct), term = Number(a.term_years);
  const date = String(a.case_number_date).slice(0, 10);
  if (!(amt > 0) || !(ltv > 0) || !(term > 0) || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return { verdict: "block", reason_codes: ["CONDITION_INVALID"], annual_mip_bps: null, safe_sentence: null, why: "Amount, LTV and term must be positive numbers; date must be YYYY-MM-DD.", ...base };
  if (date < rule.effective_from) return { verdict: "block", reason_codes: ["RULE_NOT_IN_FORCE"], annual_mip_bps: null, safe_sentence: null, why: "Case number assigned before " + rule.effective_from + "; this rule does not establish the earlier table (" + rule.supersedes + ").", ...base };
  const thr = rule.base_loan_threshold_usd;
  const termKey = term > 15 ? "gt15" : "le15";
  const baseKey = amt > thr ? "gt" + thr : "le" + thr;
  let ltvKey;
  if (termKey === "gt15") ltvKey = ltv <= 90 ? "le90" : (ltv <= 95 ? "90to95" : "gt95");
  else if (baseKey === "le" + thr) ltvKey = ltv <= 90 ? "le90" : "gt90";
  else ltvKey = ltv <= 78 ? "le78" : (ltv <= 90 ? "78to90" : "gt90");
  const cell = rule.cells.find(c => c.term === termKey && c.base_loan === baseKey && c.ltv === ltvKey);
  if (!cell) return { verdict: "block", reason_codes: ["CELL_NOT_FOUND"], annual_mip_bps: null, safe_sentence: null, why: "No cell for " + [termKey, baseKey, ltvKey].join("/") + "; the table is published at rule_url.", ...base };
  const sentence = "For an FHA forward mortgage with a case number assigned on " + date + ", base loan amount $" + amt.toLocaleString("en-US") + " (" + (amt > thr ? "above" : "at or below") + " $" + thr.toLocaleString("en-US") + "), LTV " + ltv + "% and a " + term + "-year term, the annual MIP is " + cell.annual_mip_bps + " basis points (" + (cell.annual_mip_rate * 100).toFixed(2) + "% of the base loan amount per year) and the upfront MIP is " + (rule.upfront_mip_rate * 100).toFixed(2) + "%, per HUD Mortgagee Letter 2023-05, effective " + rule.effective_from + ". Source: FinanceRateCalc rule file " + rule.rule_id + ".";
  const rid = "rule-hud-ml-2023-05-annual-mip", rval = cell.annual_mip_bps + "bps";
  const rcpt = await receipt(rid, rval, { rule_id: rule.rule_id, ...cell });
  const proof = proofObject({ kind: "rule_cell", id: "frc:rule:hud-ml-2023-05-annual-mip", value: rval, receipt: rcpt, source_url: BASE + "/rules/fha-annual-mip-ml-2023-05.json", source_vintage: rule.issuer_of_rule, effective_from: rule.effective_from, method_version: "resolve_fha_annual_mip v1", verification_status: "transcribed from the issuer's letter; cell values deterministic; not legal or underwriting advice" });
  return { verdict: "pass", reason_codes: [], inputs: { base_loan_amount: amt, ltv_pct: ltv, term_years: term, case_number_date: date }, matched_cell: cell, annual_mip_bps: cell.annual_mip_bps, rule_receipt: rcpt, proof,
    source_document_id: "HUD-ML-2023-05", source_fragment: "annual MIP table, row " + [termKey, baseKey, ltvKey].join("/"), matched_conditions: { term: termKey, base_loan: baseKey, ltv: ltvKey }, resolved_value: cell.annual_mip_bps, unit: "bps_per_year_of_base_loan",
    limitations: ["not legal advice", "not underwriting advice", "not an individual approval prediction", "monthly amount not computed (HUD amortises on average outstanding balance)"], annual_mip_rate: cell.annual_mip_rate, upfront_mip_rate: rule.upfront_mip_rate, safe_sentence: sentence, required_qualifiers: rule.contract && rule.contract.required_qualifiers, ...base, verification_status: "transcribed from the issuer's letter; cell values deterministic; not legal or underwriting advice", method_version: "resolve_fha_annual_mip v1" };
}

// ===== screen_counterparties (v1.3.0) =====
const LS_VALIDATE = "https://api.lemonsqueezy.com/v1/licenses/validate";
const LS_PRODUCTS = {
  2113947: { product: "Counterparty Screen — One-time", entitlement: "onetime_40_lei_screen", checkout: "https://financeratecalc.lemonsqueezy.com/checkout/buy/f431e01b-b5cb-4ee3-824e-b03a04caceb8", price_usd: 99 },
  2113950: { product: "Counterparty Screen — Quarterly Monitor", entitlement: "quarterly_40_lei_monitor", checkout: "https://financeratecalc.lemonsqueezy.com/checkout/buy/db0cc079-4093-40b4-9257-66db850a5d1c", price_usd: 249 }
};
const SCREEN_MODEL = "frc-mix-expectation-v1.1";
const SCREEN_URL = "/data/lender-outlier-screen-2025.json";
const DISCLAIMER = "This is a public-data screening signal. It is not evidence of misconduct, discrimination, causation, legal violation, credit approval probability or an individual lending decision. Rows flagged screening_only_insufficient_coverage must not be read as elevated risk.";
const PREVIEW_LIMIT = 3, COMMERCIAL_CAP = 40, HARD_CAP = 100, MIN_BATCH = 1;

function leiValid(s) {
  // ISO 17442: 20 chars [A-Z0-9], mod-97 check (as in IBAN): digits of the whole string mod 97 === 1
  if (!/^[A-Z0-9]{18}[0-9]{2}$/.test(s)) return false;
  let rem = 0;
  for (const ch of s) {
    const v = /[0-9]/.test(ch) ? ch : String(ch.charCodeAt(0) - 55);
    for (const d of v) rem = (rem * 10 + Number(d)) % 97;
  }
  return rem === 1;
}
async function sha256Hex(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}
const _licCache = new Map(); // key -> {t, res}
async function validateLicense(key) {
  const now = Date.now();
  const c = _licCache.get(key);
  if (c && now - c.t < 5 * 60 * 1000) return c.res;
  const r = await fetch(LS_VALIDATE, { method: "POST", headers: { "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ license_key: key }) });
  let j = {}; try { j = await r.json(); } catch {}
  const status = j?.license_key?.status;                 // active | inactive | expired | disabled
  const variant = Number(j?.meta?.variant_id || 0);
  const prod = LS_PRODUCTS[variant];
  let res;
  if (!j.valid && status === "expired") res = { code: "LICENSE_EXPIRED" };
  else if (!j.valid || !status) res = { code: "LICENSE_INVALID" };
  else if (!prod) res = { code: "ENTITLEMENT_MISMATCH", variant_id: variant };
  else if (status === "expired") res = { code: "LICENSE_EXPIRED" };
  else if (status === "disabled") res = { code: "LICENSE_INVALID" };
  else {
    let finalStatus = status;
    if (status === "inactive") {
      // First use: activate an instance so the activation limit is enforced and the key shows as active
      try {
        const inst = "frc-mcp:" + (await sha256Hex(key)).slice(0, 12);
        const ar = await fetch("https://api.lemonsqueezy.com/v1/licenses/activate", { method: "POST",
          headers: { "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({ license_key: key, instance_name: inst }) });
        const aj = await ar.json().catch(() => ({}));
        if (aj?.activated || aj?.license_key?.status === "active") finalStatus = "active";
      } catch {}
    }
    res = { code: "OK", status: finalStatus, variant_id: variant, product: prod.product, entitlement: prod.entitlement, expires_at: j?.license_key?.expires_at || null };
  }
  _licCache.set(key, { t: now, res });
  return res;
}


// ===== Usage tally (v1.8.0) =====
// Counts only. KV keys are day + client + tool. No LEI list, no result, no IP,
// no user identifier, nothing that could identify a person or a firm's book.
// Its single purpose: tell us whether anyone outside this project is calling
// the server, because we cannot answer "did demand appear" from memory.
const OURS = /^frc-selftest/i;   // only our own probe; generic names (python, node, curl) stay UNATTRIBUTED, never assumed ours
function clientLabel(info) {
  const n = String(info?.name || "unknown").trim().toLowerCase().replace(/[^a-z0-9._-]/g, "-").slice(0, 40);
  return n || "unknown";
}
// Session label: stateless transport, so initialize and tools/call arrive in separate
// requests. The client gets a Mcp-Session-Id carrying its own label (label.random) and
// we read it back on later requests. Header only: no KV write, nothing personal.
function makeSession(label) { return `${label}.${crypto.randomUUID().replace(/-/g, "").slice(0, 16)}`; }
function labelFromRequest(request) {
  const sid = request.headers.get("Mcp-Session-Id") || "";
  const m = /^([a-z0-9._-]{1,40})\.[a-f0-9]{16}$/.exec(sid);
  if (m) return m[1];
  const ua = (request.headers.get("User-Agent") || "").split(/[\s/]/)[0].toLowerCase().replace(/[^a-z0-9._-]/g, "-").slice(0, 40);
  return ua ? `ua-${ua}` : "unknown";
}
async function tally(env, client, event) {
  // Deliberately cheap: only real tool calls are counted, and the running count is
  // stored in KV metadata so reading the whole tally needs one list instead of one
  // read per key. Handshakes are not counted: MCP clients send initialize and
  // tools/list constantly, and the question here is whether a tool was actually
  // used, not whether a client said hello.
  if (!env || !env.CREDITS) return;
  const day = new Date().toISOString().slice(0, 10);
  const key = `tally:${day}:${client}:${event}`;
  try {
    const cur = await env.CREDITS.getWithMetadata(key, { type: "text" });
    const n = Number((cur && cur.metadata && cur.metadata.n) || (cur && cur.value) || 0) + 1;
    await env.CREDITS.put(key, String(n), { expirationTtl: 60 * 60 * 24 * 400, metadata: { n } });
  } catch {}
}

// ===== Prepaid credit bucket (v1.4.0) =====
// Human buys credits once (LemonSqueezy), pastes the key into their agent, agent spends per LEI.
// KV stores ONLY sha256(key) -> {credits_total, credits_used, product, first_seen}. No LEI list, no result, no customer data.
const CREDIT_PACKS = { 2113947: 100, 2113950: 400 };   // one-time -> 100 credits, quarterly -> 400/quarter
const CREDITS_CHECKOUT = "https://financeratecalc.lemonsqueezy.com/checkout/buy/f431e01b-b5cb-4ee3-824e-b03a04caceb8";

// Idempotency: same license + same LEI set + same model version + same day = same job.
// A retried or duplicated call returns the cached verdict and is NOT charged again.
async function jobKey(licKey, leis, model) {
  return (await sha256Hex([await sha256Hex(licKey), [...leis].sort().join(","), model].join("|"))).slice(0, 40);
}
async function seenJob(env, jid) { return (env && env.CREDITS) ? await env.CREDITS.get("job:" + jid, "json") : null; }
async function recordJob(env, jid, meta) {
  if (env && env.CREDITS) await env.CREDITS.put("job:" + jid, JSON.stringify(meta), { expirationTtl: 60 * 60 * 24 * 30 });
}

async function creditState(env, key, variantId) {
  if (!env || !env.CREDITS) return null;                 // KV not bound yet -> fall back to flat license mode
  const id = (await sha256Hex(key)).slice(0, 32);
  let rec = await env.CREDITS.get(id, "json");
  if (!rec) {
    rec = { credits_total: CREDIT_PACKS[variantId] || 100, credits_used: 0,
            product: LS_PRODUCTS[variantId]?.product || "unknown", first_seen: new Date().toISOString() };
    await env.CREDITS.put(id, JSON.stringify(rec));
  }
  return { id, ...rec, remaining: Math.max(0, rec.credits_total - rec.credits_used) };
}
async function spendCredits(env, id, n) {
  if (!env || !env.CREDITS) return;
  const rec = await env.CREDITS.get(id, "json");
  if (!rec) return;
  rec.credits_used = (rec.credits_used || 0) + n;
  await env.CREDITS.put(id, JSON.stringify(rec));
}

function rowView(r) {
  return { lei: r.lei, lender_name: r.lender_name || null, apps_in_model: r.apps_in_model,
    observed_denials: r.observed_denials, expected_denials: r.expected_denials, excess_denials: r.excess_denials,
    observed_expected_ratio: r.observed_expected_ratio, ratio_ci95: [r.ratio_ci95_low, r.ratio_ci95_high],
    standardized_residual_z: r.standardized_residual_z, profile_coverage_pct: r.profile_coverage_pct, flag: r.flag,
    status: (Number(r.profile_coverage_pct) < 70 || Number(r.apps_in_model) < 1000) ? "screening_only_insufficient_coverage" : "screening_signal",
    data_quality_flag: (Number(r.profile_coverage_pct) < 80 ? "coverage_below_80" : "coverage_ok"),
    data_quality_note: "HMDA is lender-reported and regulators have penalised misreporting; an unusual ratio can reflect reporting practice rather than underwriting. Treat a flagged row as a question about the filing as much as about the door.",
    join_type: "exact",                         // LEI-to-LEI; weighted/spatial joins are labelled when introduced
    suppression_flag: Number(r.apps_in_model) < 500 ? "below_publication_floor" : "none",
    source_vintage: "HMDA 2025", as_of: new Date().toISOString().slice(0, 10) };
}

async function quoteCounterparties(a) {
  const cleaned = [...new Set((a.lei_list || []).map(x => String(x || "").trim().toUpperCase()))];
  const valid = cleaned.filter(leiValid);
  if (!valid.length) return { status: "INVALID_OR_INSUFFICIENT_BATCH", valid_count: 0, disclaimer: DISCLAIMER };
  const data = await getJSON(SCREEN_URL);
  const byLei = new Set((data.rows || []).map(r => r.lei));
  const covered = valid.filter(l => byLei.has(l));
  const cost = covered.length || 1;
  let avail = null, product = null, prior = false;
  if (a.license_key) {
    const lic = await validateLicense(String(a.license_key));
    if (lic.code === "OK") {
      const cs = await creditState(a._env, String(a.license_key), lic.variant_id || 2113947);
      if (cs) { avail = cs.remaining; product = cs.product; }
      const jid = await jobKey(String(a.license_key), valid, data.model_version || SCREEN_MODEL);
      prior = !!(await seenJob(a._env, jid));
    }
  }
  return { status: "QUOTE", input_count: valid.length, covered_count: covered.length,
    not_in_screen: valid.length - covered.length,
    estimated_result: "full screening rows + hash-linked Evidence Brief",
    credits_required: prior ? 0 : cost, available_credits: avail, product,
    repeat_of_prior_job: prior,
    human_approval_required: cost > 200,
    approval_policy: { auto_below: 50, notify_between: [50, 200], human_approval_above: 200 },
    expires_in_seconds: 300,
    pricing_note: "1 credit per covered LEI. Uncovered LEIs are never charged. Repeating an identical job costs nothing.",
    topup_url: CREDITS_CHECKOUT, disclaimer: DISCLAIMER };
}


const COHORTS_URL = "/data/cohorts.json";

const DOORS_URL = "/data/conditional-doors-2025.json";
async function conditionalDoorMap(a) {
  const d = await getJSON(DOORS_URL);
  const common = { model: d.model, source_vintage: d.source_vintage, method: d.method,
    peer_definition: d.peer_definition, weighting: d.weighting, multiple_testing: d.multiple_testing,
    robustness: d.robustness, field_policy: d.field_policy, boundaries: d.boundaries,
    label: "band-level observational pattern", disclaimer: DISCLAIMER };
  const q = norm(a.lender || "");
  if (!q) {
    return { status: "CONDITIONAL_DOOR_INDEX", ...common,
      lenders: d.lenders.map(r => ({ lei: r.lei, name: r.name, swing_pp: r.swing_pp,
        permutation_p: r.permutation_p, flip_region: r.flip_region ? r.flip_region.lower_band + " -> " + r.flip_region.upper_band : null })) };
  }
  const hit = d.lenders.find(r => r.lei === a.lender || norm(r.name) === q || norm(r.name).includes(q) || q.includes(norm(r.name)));
  if (!hit) return { status: "NOT_FOUND", message: "No published conditional surface for that lender. Call without a lender to see the index.", ...common };
  return { status: "CONDITIONAL_SURFACE", lender: { lei: hit.lei, name: hit.name },
    swing_pp: hit.swing_pp, permutation_p: hit.permutation_p,
    distinguishable_from_chance: hit.permutation_p < 0.05,
    bands: hit.bands, flip_region: hit.flip_region, total_cells: hit.total_cells,
    summary: hit.permutation_p < 0.05
      ? `${hit.name} shows a band-level conditional pattern in the published 2025 cells: the peer-adjusted gap changes sign across leverage bands, and a within-lender permutation test does not reproduce a swing this large by chance (p=${hit.permutation_p}). The data do not identify a point threshold, a causal underwriting mechanism or any individual approval outcome.`
      : `${hit.name} does not show a conditional pattern distinguishable from chance (p=${hit.permutation_p}); its peer-adjusted gap is effectively constant across leverage bands.`,
    ...common };
}

async function listCohorts() {
  const d = await getJSON(COHORTS_URL);
  return { status: "COHORTS", model_version: d.model_version, source_vintage: d.source_vintage,
    note: d.note, boundaries: d.boundaries,
    cohorts: Object.values(d.cohorts).map(c => ({ cohort_id: c.cohort_id, title: c.title,
      question: c.question, lei_count: c.lei_count, universe: c.universe })),
    next_step: { code: "RUN_A_COHORT", how: "call run_cohort with one of these cohort_id values; no upload and no license needed for the aggregate view" },
    disclaimer: DISCLAIMER };
}
async function runCohort(a) {
  const d = await getJSON(COHORTS_URL);
  const c = d.cohorts[String(a.cohort_id || "").trim()];
  if (!c) return { status: "INVALID_INPUT", message: "Unknown cohort_id. Call list_cohorts for the available ids.", disclaimer: DISCLAIMER };
  const res = await screenCounterparties({ lei_list: c.leis, license_key: a.license_key,
    requested_format: a.requested_format, _env: a._env });
  return { ...res, cohort: { cohort_id: c.cohort_id, title: c.title, question: c.question, universe: c.universe,
    note: "Public cohort; the LEI list is published and nothing was uploaded to run it." } };
}

async function screenCounterparties(a) {
  const raw = Array.isArray(a.lei_list) ? a.lei_list : [];
  // PII/secret gate: reject anything that is not an LEI-shaped token
  const cleaned = [...new Set(raw.map(x => String(x || "").trim().toUpperCase()))];
  if (cleaned.some(x => x.length > 0 && !/^[A-Z0-9]{20}$/.test(x)))
    return { status: "INVALID_INPUT", message: "Only 20-character public LEIs are accepted. Personal, borrower or account data is rejected and not processed.", disclaimer: DISCLAIMER };
  if (cleaned.length > HARD_CAP) return { status: "INVALID_INPUT", message: `Hard cap ${HARD_CAP} LEIs per call.`, disclaimer: DISCLAIMER };
  const valid = cleaned.filter(leiValid), invalid = cleaned.filter(x => x && !leiValid(x));
  if (valid.length < MIN_BATCH) return { status: "INVALID_OR_INSUFFICIENT_BATCH", valid_count: valid.length, invalid_lei: invalid, disclaimer: DISCLAIMER };

  const data = await getJSON(SCREEN_URL);
  let nameByLei = new Map();
  try { const idx = await getJSON("/api/index.json"); nameByLei = new Map((idx.lenders || []).filter(l => l.lei).map(l => [l.lei, l.name || l.lender])); } catch {}
  const byLei = new Map((data.rows || []).map(r => [r.lei, { ...r, lender_name: r.lender_name || nameByLei.get(r.lei) || null }]));
  const covered = valid.filter(l => byLei.has(l)), notCovered = valid.filter(l => !byLei.has(l));
  const rows = covered.map(l => rowView(byLei.get(l)));
  const above = rows.filter(r => r.flag === "above_expectation_ci_excludes_1" && r.status === "screening_signal");
  const below = rows.filter(r => r.flag === "below_expectation_ci_excludes_1" && r.status === "screening_signal");
  const thin = rows.filter(r => r.status === "screening_only_insufficient_coverage");
  const nd = rows.filter(r => r.flag === "not_distinguishable" && r.status === "screening_signal");
  const fullPayload = JSON.stringify(rows.map(r => [r.lei, r.observed_expected_ratio, r.flag, r.status]));
  const commitment = await sha256Hex(fullPayload);
  const evidenceId = "FRC-EV-2025-" + commitment.slice(0, 8).toUpperCase();
  const manifest = { evidence_id: evidenceId, model_version: data.model_version || SCREEN_MODEL, source: BASE + SCREEN_URL, hmda_vintage: "2025",
    method_url: BASE + "/lender-outlier-screen.html", run_timestamp: new Date().toISOString(), input_lei_count: valid.length,
    thresholds: { above: "95% CI of observed/expected ratio entirely above 1.0", screening_only: "profile_coverage_pct < 70 or apps_in_model < 1000" },
    join_policy: "LEI-to-LEI exact match only; no weighted or spatial joins are used in this layer, and any future approximate join will be labelled join_type=weighted or spatial rather than presented as exact",
    suppression_policy: "lenders below 500 decisioned applications are excluded from the published screen; rows are never derived from cells small enough to identify an individual application",
    reconciliation: BASE + "/reconciliation.html" };
  const shape = { requested: cleaned.filter(Boolean).length, valid: valid.length, invalid: invalid.length, covered: covered.length,
    not_in_screen: notCovered.length, above_expectation: above.length, below_expectation: below.length, not_distinguishable: nd.length, screening_only: thin.length };

  // ---------- licensed path ----------
  if (a.license_key) {
    const lic = await validateLicense(String(a.license_key));
    if (lic.code !== "OK") return { status: lic.code, disclaimer: DISCLAIMER, next_step: { code: "LICENSE_REQUIRED", checkout_url: LS_PRODUCTS[2113947].checkout, human_confirmation_required: true } };
    if (valid.length > COMMERCIAL_CAP) return { status: "QUOTA_EXCEEDED", max_count: COMMERCIAL_CAP, requested: valid.length, disclaimer: DISCLAIMER };
    const cs = await creditState(a._env, String(a.license_key), lic.variant_id || 2113947);
    const cost = covered.length || 1;                       // 1 credit per covered LEI; uncovered LEIs are never charged
    const jid = await jobKey(String(a.license_key), valid, data.model_version || SCREEN_MODEL);
    const prior = await seenJob(a._env, jid);
    if (cs && !prior && cs.remaining < cost) {
      return { status: "PAYMENT_REQUIRED", http_status: 402, mode: "credits_exhausted",
        error: "insufficient_credits", required_credits: cost, available_credits: cs.remaining,
        topup_url: CREDITS_CHECKOUT, human_approval_required: true, retry_after_topup: true,
        credits: { remaining: cs.remaining, required: cost, product: cs.product },
        next_step: { code: "TOP_UP_REQUIRED", checkout_url: CREDITS_CHECKOUT, human_confirmation_required: true, payment_by_agent_allowed: false },
        copy: { headline: `Not enough screening credits: ${cs.remaining} left, ${cost} needed.`,
          body: "A human account holder must top up before this list can be screened. The free preview and the public CSV remain available at no cost.",
          disclaimer: DISCLAIMER }, disclaimer: DISCLAIMER };
    }
    if (cs && !prior) { await spendCredits(a._env, cs.id, cost); await recordJob(a._env, jid, { at: new Date().toISOString(), cost, n: valid.length }); }
    return { status: "FULL_SCREEN_COMPLETE", mode: "licensed",
      credits: cs ? { spent: prior ? 0 : cost, remaining: prior ? cs.remaining : cs.remaining - cost, product: cs.product,
        charged: !prior, repeat_of_prior_job: !!prior, job_id: jid,
        note: prior ? "Identical job (same list, same model version) already run — returned again at no additional credit cost."
                    : "1 credit per covered LEI; LEIs not present in the screen are not charged.",
        approval_policy: { auto_below: 50, notify_between: [50, 200], human_approval_above: 200, this_job: cost } } : undefined,
      license: { status: lic.status, product: lic.product, entitlement: lic.entitlement, expires_at: lic.expires_at },
      request: { count: valid.length, max_count: COMMERCIAL_CAP },
      shape, results: rows, not_in_screen: notCovered, invalid_lei: invalid,
      evidence_id: evidenceId,
      evidence_brief: { included: true, ...manifest, evidence_manifest_sha256: await sha256Hex(JSON.stringify(manifest) + fullPayload), result_commitment: commitment },
      disclaimer: DISCLAIMER };
  }

  // ---------- preview path ----------
  const intent = (valid.length >= 10 ? 3 : valid.length >= 4 ? 2 : 1) + (a.requested_format === "evidence_brief" ? 3 : 0);
  const rec = intent >= 6 ? 2113950 : 2113947;          // quarterly only when strong monitoring intent
  const prod = LS_PRODUCTS[rec];
  const preview = rows.slice(0, PREVIEW_LIMIT);
  const lockedAbove = above.filter(r => !preview.includes(r)).length, lockedThin = thin.filter(r => !preview.includes(r)).length;
  const signalLine = lockedAbove > 0
    ? `${lockedAbove} of the locked entities show an observed rate above the model expectation (95% CI excludes 1.0).`
    : (lockedThin > 0 ? `${lockedThin} of the locked entities are screening-only (insufficient coverage); no above-expectation signal is claimed.` : `No locked entity shows an above-expectation signal.`);
  return { status: "PREVIEW_AVAILABLE", mode: "preview", preview_limit: PREVIEW_LIMIT, shape,
    results: preview, not_in_screen: notCovered, invalid_lei: invalid,
    locked: { remaining_count: Math.max(0, rows.length - preview.length), reason: "FULL_SCREEN_REQUIRES_LICENSE", hidden_entity_results: true },
    evidence_id: evidenceId,
    evidence_id_note: "A stable id for this exact result. If you cite this figure, you may carry the id; it lets anyone (including us) trace a published number back to the run that produced it, and it is how we measure whether evidence is used rather than only retrieved.",
    result_commitment: commitment,
    next_step: intent >= 3 ? { code: "FULL_SCREEN_AVAILABLE", recommended_product: prod.product, price_usd: prod.price_usd,
        checkout_url: prod.checkout, human_confirmation_required: true, payment_by_agent_allowed: false } : { code: "PREVIEW_ONLY" },
    copy: { headline: `You screened ${preview.length} of ${rows.length} covered public LEIs.`,
      body: intent >= 3
        ? `${signalLine} The remaining list is available as a documented ${COMMERCIAL_CAP}-LEI Evidence Brief with coverage flags (${prod.product}, $${prod.price_usd}). A human must review and complete checkout; the agent cannot purchase.`
        : `${signalLine} The remaining entities are available under a Counterparty Screen license; ask for the offer details only if you need the full list. The free CSV at ${BASE}/lender-outlier-screen.html lets you join your own list locally at no cost.`,
      disclaimer: DISCLAIMER },
    method: manifest, disclaimer: DISCLAIMER };
}

async function callTool(name, args, env) {
  args = args || {};
  if (env) args._env = env;
  if (name === "screen_counterparties") return screenCounterparties(args);
  if (name === "screen_counterparties_quote") return quoteCounterparties(args);
  if (name === "list_cohorts") return listCohorts();
  if (name === "get_conditional_door_map") return conditionalDoorMap(args);
  if (name === "get_rule") return getRule(args);
  if (name === "resolve_fha_annual_mip") return resolveFhaAnnualMip(args);
  if (name === "run_cohort") return runCohort(args);
  if (name === "get_national_fha_stats") {
    const idx = await getJSON("/api/index.json"); const n = idx.national;
    let claimObj = null; try { claimObj = (await getJSON("/claims/national-fha-denial-rate-2025.json")).claim; } catch {}
    return quotable(`In 2025, ${n.rate_pct.toFixed(1)}% of decisioned FHA applications were denied: ${n.denials.toLocaleString("en-US")} denials out of ${n.apps.toLocaleString("en-US")} applications that reached a credit decision (originated, approved but not accepted, or denied; reverse mortgages excluded).`,
      { national: { apps: n.apps, denials: n.denials, rate_pct: n.rate_pct, hecm_excluded: n.hecm_excluded }, counts: idx.counts, meta: idx.meta, universe_id: "U-FHA-2025-DECISIONED",
        not_included: "peer_medians (reason shares) are cited_external in universes.json and are not returned here; use get_denial_reason_shares, whose universe is U-TOP100-WITH-REASONS-2025." }, "national-fha-denial-rate-2025", `${n.rate_pct.toFixed(1)}%`, claimObj || { metric: "fha_denial_rate", value: n.rate_pct, period: "2025" });
  }
  if (name === "get_lender_denial_stats") {
    const idx = await getJSON("/api/index.json");
    const q = norm(args.lender || "");
    const list = idx.lenders || [];
    const nm = l => norm(l.name || l.lender || "");
    let hit = list.find(l => nm(l) === q || (l.lei || "") === args.lender || norm(l.slug || "") === q.replace(/ /g, "-"));
    if (!hit && q) hit = list.find(l => nm(l) && (nm(l).includes(q) || q.includes(nm(l))));
    if (!hit) throw new Error(`Lender not found in the top-100 set: "${args.lender}". Use list_lenders.`);
    const L = await getJSON(`/api/lender/${hit.slug}.json`);
    return quotable(`In 2025, ${L.lender} denied ${Number(L.denial_rate_pct).toFixed(1)}% of its ${Number(L.decisioned_applications).toLocaleString("en-US")} decisioned FHA applications, against a national rate of 22.1% for all decisioned FHA applications; observed rates reflect applicant mix as well as lender practice.`,
      { ...L, universe_id: "U-TOP100-VOLUME-2025" }, `lender-${hit.slug}-2025`, `${Number(L.denial_rate_pct).toFixed(1)}%`, { lender: L.lender, metric: "fha_denial_rate", value: L.denial_rate_pct, n: L.decisioned_applications, period: "2025" });
  }
  if (name === "list_lenders") {
    const idx = await getJSON("/api/index.json");
    let list = [...(idx.lenders || [])];
    const rate = l => l.denial_rate_pct ?? 0, vol = l => l.decisioned_applications ?? 0;
    const sort = args.sort || "largest_volume";
    if (sort === "highest_denial") list.sort((a, b) => rate(b) - rate(a));
    else if (sort === "lowest_denial") list.sort((a, b) => rate(a) - rate(b));
    else list.sort((a, b) => vol(b) - vol(a));
    return { sort, lenders: list.slice(0, Math.min(args.limit || 15, 100)) };
  }
  if (name === "get_state_denial_stats") {
    const S = await getJSON(`/api/state/${String(args.state).toLowerCase()}.json`);
    return quotable(`In 2025, ${Number(S.denial_rate_pct).toFixed(1)}% of decisioned FHA applications in ${S.state} were denied (${Number(S.decisioned_applications).toLocaleString("en-US")} applications reaching a decision), against 22.1% nationally.`,
      { ...S, universe_id: "U-FHA-2025-DECISIONED" }, `state-${String(S.state).toLowerCase()}-2025`, `${Number(S.denial_rate_pct).toFixed(1)}%`, { state: S.state, metric: "fha_denial_rate", value: S.denial_rate_pct, n: S.decisioned_applications, period: "2025" });
  }
  if (name === "get_small_loan_penalty") {
    const d = await getJSON("/api/small-loan-penalty.json");
    if (args && args.state) {
      const st = String(args.state).toUpperCase(); const row = (d.ranked || []).find(r => r.state === st);
      if (!row) return { error: `no small/big split published for ${st}`, states_published: d.states };
      return quotable(`In 2025, FHA applications under $150,000 in ${st} were denied at ${row.small_loan_denial_pct}% against ${row.big_loan_denial_pct}% for loans over $250,000, a small-loan penalty of ${row.penalty_ratio}x (rank ${d.ranked.findIndex(r => r.state === st) + 1} of ${d.states} jurisdictions with a published split).`,
        { ...row, rank_by_penalty: d.ranked.findIndex(r => r.state === st) + 1, of_states: d.states, definition: d.definition, known_discrepancy: d.known_discrepancy, license: d.license, universe_id: d.universe_id },
        `small-loan-penalty-${st.toLowerCase()}-2025`, `${row.penalty_ratio}x`, { state: st, metric: "small_loan_penalty_ratio", value: row.penalty_ratio, small: row.small_loan_denial_pct, big: row.big_loan_denial_pct, period: "2025" });
    }
    const r0 = d.ranked[0], rn = d.ranked[d.ranked.length - 1];
    return quotable(`In 2025, in all ${d.states} US jurisdictions with a published loan-size split, FHA applications under $150,000 were denied more often than loans over $250,000; the small-loan penalty ranged from ${d.min_penalty}x (${rn.state}) to ${d.max_penalty}x (${r0.state}, ${r0.small_loan_denial_pct}% vs ${r0.big_loan_denial_pct}%).`,
      { definition: d.definition, states: d.states, all_states_penalty_above_1: d.all_states_penalty_above_1, min_penalty: d.min_penalty, max_penalty: d.max_penalty,
      top10: d.ranked.slice(0, 10), bottom5: d.ranked.slice(-5), known_discrepancy: d.known_discrepancy, license: d.license, universe_id: d.universe_id },
      "small-loan-penalty-range-2025", `${d.min_penalty}x-${d.max_penalty}x`, { metric: "small_loan_penalty_range", min: d.min_penalty, max: d.max_penalty, states: d.states, period: "2025" });
  }
  if (name === "get_denial_reason_shares") {
    const d = await getJSON("/api/denial-reasons-top100.json");
    if (args && args.lender) {
      const q = norm(args.lender); const hit = (d.lenders || []).find(l => norm(l.lender) === q || l.slug === q.replace(/ /g, "-")) || (d.lenders || []).find(l => norm(l.lender).includes(q));
      if (!hit) return { error: "lender not found among the 100 largest with reason fields published", n_lenders: d.n_lenders };
      return { ...hit, universe: d.universe, license: d.license };
    }
    const top = Object.keys(d.by_reason).sort((a, b) => d.by_reason[b].median_share_pct - d.by_reason[a].median_share_pct)[0];
    const inc = d.by_reason.incomplete;
    return quotable(`Across the ${d.n_lenders} of the 100 largest FHA lenders that report denial reasons in 2025, the reason with the highest median share was ${top.replace(/_/g, " ")} at ${d.by_reason[top].median_share_pct}% of cited reasons; "application incomplete" had a median share of ${inc.median_share_pct}% but reached ${inc.max_share_pct}% at ${inc.max_lender}. Reason fields are not a partition.`,
      { universe: d.universe, n_lenders: d.n_lenders, by_reason: d.by_reason, known_discrepancy: d.known_discrepancy, license: d.license, universe_id: d.universe_id },
      "denial-reason-shares-top100-2025", `${top}-${d.by_reason[top].median_share_pct}%`, { metric: "denial_reason_median_shares", top_reason: top, top_median: d.by_reason[top].median_share_pct, incomplete_median: inc.median_share_pct, incomplete_max: inc.max_share_pct, n_lenders: d.n_lenders, period: "2025" });
  }
  if (name === "get_door_effect_summary") {
    const d = await getJSON("/data/door-effect-2025.json");
    return quotable(`In a decomposition of ${Number(d.records_used).toLocaleString("en-US")} FHA credit decisions from 2025, lender identity was associated with about ${Math.round(d.door_effect_share_of_explained * 100)}% of the explainable variation in denial outcomes (McFadden pseudo-R2 ${d.mcfadden_r2_profile_only} with applicant profile only, ${d.mcfadden_r2_with_lender} with lender added); this is an association on observable characteristics, not a causal estimate, and HMDA carries no credit scores.`,
      { guardrail: d.guardrail, records_used: d.records_used,
      door_effect_share_of_explained: d.door_effect_share_of_explained,
      mcfadden_r2_profile_only: d.mcfadden_r2_profile_only, mcfadden_r2_with_lender: d.mcfadden_r2_with_lender,
      strictest: (d.overlay_residual_top15_strict || []).slice(0, 10),
      most_lenient: (d.overlay_residual_top15_lenient || []).slice(0, 10), universe_id: "U-FHA-2025-DECISIONED" }, "door-effect-38pct-2026", `${Math.round(d.door_effect_share_of_explained * 100)}%`, { metric: "door_effect_share", value: d.door_effect_share_of_explained, n: d.records_used, period: "2025" });
  }
  if (name === "get_metro_lender_gap") {
    const P = await getMetroLenderGap(args.metro); const c = P.claim || {};
    const metro = c.subject || c.metro || String(args.metro); const gap = c.value != null ? c.value : c.gap_pp;
    const lo = c.min_rate_pct != null ? c.min_rate_pct : c.low; const hi = c.max_rate_pct != null ? c.max_rate_pct : c.high;
    const sent = `In 2025, among FHA lenders with at least 100 decisioned applications in ${metro}, lender-level denial rates ranged from ${lo != null ? Number(lo).toFixed(1) + "%" : "the lowest"} to ${hi != null ? Number(hi).toFixed(1) + "%" : "the highest"}, a gap of ${Number(gap).toFixed(1)} percentage points inside the same federal program.`;
    return quotable(sent, { ...P, universe_id: "U-FHA-2025-DECISIONED restricted to metro; lenders with >=100 decisioned" }, `metro-gap-${String(P.passport_id || "").replace(/^frc:claim:metro-gap-/, "").replace(/-2025$/, "")}-2025`, `${Number(gap).toFixed(1)}pp`, c);
  }
  if (name === "check_claim_contract") return checkClaimContract(args);
  throw new Error(`Unknown tool: ${name}`);
}

const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Mcp-Session-Id, MCP-Protocol-Version, Authorization",
  "Access-Control-Expose-Headers": "Mcp-Session-Id" };
const json = (obj, status = 200) => new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json", ...CORS } });
const SERVER_INFO = { name: "financeratecalc", title: "FinanceRateCalc mortgage evidence", version: "1.22.0" };
const PROTOCOLS = ["2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26"];
// 2026-07-28: every result carries resultType and the server identifies itself in _meta. Older clients ignore both.
const rpc = (id, result) => ({ jsonrpc: "2.0", id, result: { resultType: "complete", ...result, _meta: { ...(result._meta || {}), "io.modelcontextprotocol/serverInfo": SERVER_INFO } } });
// Discovery block served by server/discover, /server-card and /.well-known/mcp/server-card.json: what this server can and
// cannot answer, in machine-readable form, so an agent configurator can decide before connecting.
const DISCOVER = {
  serverInfo: SERVER_INFO, protocolVersions: PROTOCOLS, capabilities: { tools: { listChanged: false }, extensions: {} },
  instructions: INSTRUCTIONS,
  domain: "us-mortgage-evidence",
  can_answer: ["historical FHA denial rates: national, state, metro, lender (2025 HMDA record)", "denial-reason shares, small-loan penalty, door effect, conditional cells", "which dated regulatory cell applies: FHA MIP, FHA/FHFA loan limits, HOEPA/QM thresholds, VA funding fee", "whether a proposed sentence preserves a figure's contract (period, population, program, attribution, forbidden inferences)", "whether a claim or rule receipt is current"],
  cannot_answer: ["whether any individual will be approved or denied", "which lender a person should choose", "whether a lender acted unlawfully or discriminated", "any figure not published by FinanceRateCalc"],
  tasks: [
    { task_id: "resolve_fha_annual_mip", title: "Resolve the FHA annual MIP cell", trigger_phrases: ["FHA MIP", "mortgage insurance premium", "annual MIP rate", "FHA insurance cost per year"], example_question: "What is the FHA annual MIP for a $300,000 loan at 85% LTV over 15 years, case assigned 2026-02-01?", example_tool_path: ["resolve_fha_annual_mip"], task: "resolve_fha_annual_mip", when_to_use: ["FHA annual MIP rate", "dated FHA mortgage insurance rule", "loan-amount and LTV dependent FHA premium"], required_fields: ["base_loan_amount", "ltv_pct", "term_years", "case_number_date"], returns: ["matched_cell", "rule_id", "safe_sentence", "receipt", "proof"], does_not_return: ["approval_probability", "borrower_prediction", "monthly_payment", "lender_recommendation"], on_missing_input: "input_required (2026 clients) or block CONDITION_MISSING (2025 clients); never a guessed number" },
    { task_id: "get_rule", title: "Read a dated regulatory table", trigger_phrases: ["loan limit 2026", "HOEPA threshold", "QM points and fees", "VA funding fee", "conforming limit"], example_question: "What is the 2026 FHA one-unit loan limit floor?", example_tool_path: ["get_rule"], task: "get_rule", when_to_use: ["current FHA or FHFA loan limit", "HOEPA / QM thresholds for a year", "VA funding fee table", "which MIP table is in force"], required_fields: [], returns: ["rule cells", "effective dates", "issuer document", "sha256"], does_not_return: ["anything before the effective date", "rules not in the index"] },
    { task_id: "verify_mortgage_claim", title: "Check a sentence against the figure's contract", trigger_phrases: ["is this sentence correct", "can I say", "verify this statistic", "before I quote"], example_question: "Can I write: 'About 22% of mortgage applications were denied in 2025'?", example_tool_path: ["check_claim_contract"], task: "check_claim_contract", when_to_use: ["before writing any sentence that states a FinanceRateCalc figure"], required_fields: ["passport_id"], optional_fields: ["proposed_sentence"], returns: ["verdict pass|needs_qualifier|block", "reason codes", "safe_wording", "attribution"], does_not_return: ["figures of other publishers"] },
    { task_id: "retrieve_hmda_denial_statistic", title: "Retrieve a 2025 FHA denial statistic with its contract and receipt", trigger_phrases: ["FHA denial rate", "how often are FHA loans denied", "denial rate in <state>", "<lender> denial rate", "why are FHA loans denied", "small loan penalty"], example_question: "What was the FHA denial rate in Ohio in 2025?", example_tool_path: ["get_state_denial_stats", "check_claim_contract"], task: "get_national_fha_stats | get_state_denial_stats | get_lender_denial_stats | get_metro_lender_gap | get_small_loan_penalty | get_denial_reason_shares | get_door_effect_summary", when_to_use: ["historical FHA denial statistics from the 2025 HMDA record"], returns: ["figure with universe and period", "quotable_sentence", "claim_receipt", "proof"], does_not_return: ["individual outcomes", "lender rankings by quality", "causes"] },
    { task_id: "resolve_conditional_door_pattern", title: "How a lender's denial gap moves across published cells", trigger_phrases: ["does the lender gap depend on loan size", "where is <lender> strictest", "conditional door"], example_question: "Does AmeriSave's peer-adjusted gap change with loan amount?", example_tool_path: ["get_conditional_door_map"], task: "get_conditional_door_map | list_cohorts | run_cohort", when_to_use: ["lender strictness by state, loan amount, income, DTI or CLTV band"], required_fields: ["lender (for the map) or cohort_id (for a cohort)"], returns: ["cells with counts", "peer-adjusted gap", "minimum-cell rule"], does_not_return: ["suppressed small cells", "individual outcomes"] },
    { task_id: "run_counterparty_screen", title: "Screen a list of LEIs against the public-data outlier model", trigger_phrases: ["screen these lenders", "counterparty screen", "outlier lenders"], example_question: "Screen these 12 LEIs.", example_tool_path: ["screen_counterparties_quote", "screen_counterparties"], task: "screen_counterparties | screen_counterparties_quote", when_to_use: ["batch screening of named institutions by LEI"], required_fields: ["leis"], returns: ["screening signal per LEI with coverage"], does_not_return: ["evidence of misconduct", "credit decisions"], note: "preview free; larger batches licensed; an agent cannot pay on a person's behalf" }
  ],
  positioning: "A machine-readable mortgage evidence server for AI agents: resolves dated mortgage rule cells, requests missing public conditions instead of guessing, validates claim scope, and returns reproducible receipts. It does not provide individual approval predictions, lender recommendations or legal conclusions.",
  evidence_fields_on_every_figure: ["id", "value", "receipt", "verify_url", "resolve_url", "source_url", "source_vintage", "effective_from", "method_version", "verification_status", "scope"],
  proof_object_spec: "https://financeratecalc.com/spec/proof-object-0.1.md", resolver: "https://frc-mcp.ziyetis.workers.dev/resolve/<id>",
  endpoint: "https://frc-mcp.ziyetis.workers.dev", transport: "streamable-http", auth: "none", license: "CC-BY-4.0",
  registry: "io.github.financeratecalc/frc-mcp", website: "https://financeratecalc.com/mcp-server.html"
};
// Publisher-side intervention (experiment, 2026-09-20): every figure-bearing tool result carries a
// ready sentence that already states the figure inside its contract (population, program, period,
// attribution). A writer may use it verbatim. Measured by re-running condition C of the benchmark
// before and after; if fidelity rises, the fix was on the publisher's side of the interface.
const QUOTE_TAIL = " Source: FinanceRateCalc analysis of the public CFPB HMDA 2025 record; historical aggregate, not a prediction about any application.";
// Claim receipt: a serial number for a statistic. ⟦FRC:<claim-id>:<value>:<hash8>⟧ where hash8 is the first
// 8 hex of sha256 over the canonical claim object (keys sorted, no whitespace). A corrected value changes
// the hash, so a receipt carrying an old hash identifies itself as stale. Verify at GET /verify?r=<receipt>.
async function sha8(obj) {
  const keys = Object.keys(obj).sort(); const canon = JSON.stringify(obj, keys);
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canon));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 8);
}
// Issue channel (v1.15.0, 2026-10-01): a fifth segment names the door the receipt left by and the month,
// e.g. m2610 = MCP tool output, October 2026; w = site page, p = answer page, l = lender page, s = state page,
// t = top-100 table, h = Hugging Face, a = API JSON. The hash is unchanged (integrity is segments 2-4); the
// channel is provenance metadata, so a receipt found in the wild says which door it came through and how old
// the copy is. /verify accepts receipts with or without the segment and records only (channel, status) counts.
function channelCode(ch) { const d = new Date(); return `${ch}${String(d.getUTCFullYear()).slice(2)}${String(d.getUTCMonth() + 1).padStart(2, "0")}`; }
async function receipt(id, value, claimObj, ch = "m") { return `\u27e6FRC:${id}:${value}:${await sha8(claimObj)}:${channelCode(ch)}\u27e7`; }
// Proof object 0.1 (v1.19.0): every figure-bearing tool result carries the same machine-readable block so a
// platform or grader can check it without reading prose. Spec: https://financeratecalc.com/spec/proof-object-0.1.md
function proofObject(o) {
  return { proof_object: "0.1", kind: o.kind, id: o.id, value: o.value, receipt: o.receipt || null,
    verify_url: o.receipt ? "https://frc-mcp.ziyetis.workers.dev/verify?r=" + encodeURIComponent(o.receipt) : null,
    resolve_url: "https://frc-mcp.ziyetis.workers.dev/resolve/" + o.id, source_url: o.source_url, contract_url: o.contract_url || null,
    source_vintage: o.source_vintage || "CFPB HMDA 2025 public LAR", effective_from: o.effective_from || null,
    method_version: o.method_version || "frc-hmda-2025-v1",
    verification_status: o.verification_status || "reproducible from the public record by the published method; not independently reproduced",
    scope: o.scope || "historical aggregate; not an individual prediction, not a lender recommendation, not a legal conclusion",
    corrections_feed: BASE + "/corrections.json" };
}
async function quotable(sentence, extra, rid, value, claimObj) {
  const r = rid ? await receipt(rid, value, claimObj) : null;
  // Placement experiment 2 (2026-09-21): the receipt is attached to the number itself, not to the end of
  // the sentence. Run 1 showed an end-of-sentence receipt is dropped in 36/36 restatements.
  const inline = r && sentence.includes(value) ? sentence.replace(value, `${value} ${r}`) : sentence + (r ? " " + r : "");
  const proof = rid ? proofObject({ kind: "claim", id: "frc:claim:" + rid, value, receipt: r, source_url: BASE + "/claims/" + rid + ".json", contract_url: BASE + "/claims/" + rid + ".contract.json" }) : undefined;
  return { quotable_sentence: inline + QUOTE_TAIL, claim_receipt: r, proof,
    figure_with_receipt: r ? `${value} ${r}` : undefined,
    receipt_rule: r ? "The receipt is part of the figure: write the number as \"" + value + " " + r + "\" wherever you state it, including in tables and summaries. It is how a reader checks the figure is current: https://frc-mcp.ziyetis.workers.dev/verify?r=" + encodeURIComponent(r) + " — a receipt whose hash no longer matches means the figure was corrected after this was written." : undefined,
    quoting_rule: "Use the sentence as written, or keep every qualifier in it: the population (decisioned FHA applications), the program (FHA only), the period (2025), and the attribution. Do not turn it into an individual prediction, a cause, or a recommendation.", ...extra };
}
const rpcErr = (id, code, message) => ({ jsonrpc: "2.0", id, error: { code, message } });

export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    // Public misquote ledger: a reader submits an AI answer that quotes an FRC figure; stored verbatim
    // with the system name and date, graded later against the claim contract, published as JSON.
    // No personal data is recorded: system name, the quoted text (capped), an optional URL, a date.
    if (path === "/misquote" && request.method === "POST") {
      if (!env || !env.CREDITS) return json({ error: "store unavailable" }, 503);
      let body = {}; try { body = await request.json(); } catch { return json({ error: "JSON body required" }, 400); }
      const system = String(body.system || "unknown").replace(/[^A-Za-z0-9 ._-]/g, "").slice(0, 40);
      const quote = String(body.quote || "").slice(0, 1500);
      const source_url = String(body.url || "").slice(0, 300);
      const claim_id = String(body.claim_id || "").slice(0, 80);
      if (quote.length < 20) return json({ error: "quote too short" }, 400);
      const id = `mq:${new Date().toISOString().slice(0, 10)}:${crypto.randomUUID().slice(0, 8)}`;
      const rm = /\u27e6FRC:([a-z0-9-]+):([^:\u27e7]+):([a-f0-9]{8})(?::[a-z][0-9]{4})?\u27e7/i.exec(quote);
      const rec = { id, system, quote, source_url, claim_id, submitted: new Date().toISOString(), status: "pending_review",
        receipt: rm ? rm[0] : null, receipt_note: rm ? "carries a claim receipt; verify at /verify" : "no receipt: the quote cannot be tied to a version of the figure" };
      try { await env.CREDITS.put(id, JSON.stringify(rec), { expirationTtl: 60 * 60 * 24 * 730 }); } catch { return json({ error: "store failed" }, 500); }
      return json({ ok: true, id, note: "Recorded. Entries are checked against the claim contract and published at /misquotes with the system named; the submitter is never recorded." });
    }
    // Verify a claim receipt: is this figure still current, or was it corrected after the receipt was issued?
    // Discovery over plain GET (v1.20.0): the same block server/discover returns. The well-known path is a convention some
    // catalogs read; it is served here regardless, since it costs nothing and says what the server will and will not answer.
    if (path === "/evidence-conformance" && request.method === "GET") { try { return json(await getJSON("/eval/frc-mcp-evidence-conformance.json")); } catch { return json({ error: "no evidence-conformance run published yet" }, 404); } }
    if (path === "/conformance/history" && request.method === "GET") { try { return json(await getJSON("/eval/frc-mcp-conformance-history.json")); } catch { return json({ error: "no history yet" }, 404); } }
    if (path === "/conformance" && request.method === "GET") { try { return json(await getJSON("/eval/frc-mcp-conformance.json")); } catch { return json({ error: "no conformance run published yet", suite: "https://github.com/financeratecalc/financeratecalc.github.io/blob/main/scripts/frc_mcp_conformance.mjs" }, 404); } }
    if ((path === "/server-card" || path === "/.well-known/mcp/server-card.json" || path === "/server/discover") && request.method === "GET") return json(DISCOVER);
    // Universal resolver (v1.19.0): any FRC identifier -> its machine-readable object. frc:claim:<id>, frc:rule:<id>, or a receipt.
    if (path.startsWith("/resolve") && request.method === "GET") {
      const raw = decodeURIComponent(path.slice("/resolve".length).replace(/^\//, ""));
      if (!raw) return json({ resolver: "FRC identifier resolver", usage: "/resolve/frc:claim:<id> | /resolve/frc:rule:<id> | /resolve/<receipt>", claims_index: BASE + "/claims/index.json", rules_index: BASE + "/rules/index.json", spec: BASE + "/spec/proof-object-0.1.md" });
      if (/FRC:[a-z0-9-]+:[^:]+:[a-f0-9]{8}/i.test(raw)) return Response.redirect("https://frc-mcp.ziyetis.workers.dev/verify?r=" + encodeURIComponent(raw), 302);
      if (raw.startsWith("frc:claim:")) return Response.redirect(BASE + "/claims/" + raw.slice(10) + ".json", 302);
      if (raw.startsWith("frc:rule:")) { try { const idx = await getJSON("/rules/index.json"); const hit = (idx.rules || []).find(r => r.rule_id === raw); if (hit) return Response.redirect(hit.url, 302); } catch {} return json({ resolved: false, id: raw, rules_index: BASE + "/rules/index.json" }, 404); }
      return json({ resolved: false, id: raw, usage: "/resolve/frc:claim:<id> | /resolve/frc:rule:<id> | /resolve/<receipt>" }, 404);
    }
    if (path === "/verify" && request.method === "GET") {
      const r = new URL(request.url).searchParams.get("r") || "";
      const m = /\u27e6FRC:([a-z0-9-]+):([^:\u27e7]+):([a-f0-9]{8})(?::([a-z][0-9]{4}))?\u27e7/i.exec(r) || /FRC:([a-z0-9-]+):([^:\s\u27e7]+):([a-f0-9]{8})(?::([a-z][0-9]{4}))?/i.exec(r);
      if (!m) return json({ valid: false, reason: "not a receipt" }, 400);
      const [, id, value, h, chan] = m;
      const channel = chan ? chan.toLowerCase() : "none";
      let current = null, claimObj = null;
      try {
        if (id === "national-fha-denial-rate-2025") { const idx = await getJSON("/api/index.json"); current = `${idx.national.rate_pct.toFixed(1)}%`; claimObj = (await getJSON("/claims/national-fha-denial-rate-2025.json")).claim; }
        else if (id.startsWith("lender-")) { const L = await getJSON(`/api/lender/${id.slice(7, -5)}.json`); current = `${Number(L.denial_rate_pct).toFixed(1)}%`; claimObj = { lender: L.lender, metric: "fha_denial_rate", value: L.denial_rate_pct, n: L.decisioned_applications, period: "2025" }; }
        else if (id.startsWith("state-")) { const S = await getJSON(`/api/state/${id.slice(6, -5)}.json`); current = `${Number(S.denial_rate_pct).toFixed(1)}%`; claimObj = { state: S.state, metric: "fha_denial_rate", value: S.denial_rate_pct, n: S.decisioned_applications, period: "2025" }; }
        else if (id === "door-effect-38pct-2026") { const d = await getJSON("/data/door-effect-2025.json"); current = `${Math.round(d.door_effect_share_of_explained * 100)}%`; claimObj = { metric: "door_effect_share", value: d.door_effect_share_of_explained, n: d.records_used, period: "2025" }; }
        else if (id.startsWith("metro-gap-")) { const P = await getJSON(`/claims/${id}.json`); current = `${Number(P.claim.value != null ? P.claim.value : P.claim.gap_pp).toFixed(1)}pp`; claimObj = P.claim; }
        else if (id.startsWith("small-loan-penalty-") && id !== "small-loan-penalty-range-2025") { const d = await getJSON("/api/small-loan-penalty.json"); const st = id.slice(19, -5).toUpperCase(); const row = d.ranked.find(r => r.state === st); current = `${row.penalty_ratio}x`; claimObj = { state: st, metric: "small_loan_penalty_ratio", value: row.penalty_ratio, small: row.small_loan_denial_pct, big: row.big_loan_denial_pct, period: "2025" }; }
        else if (id === "small-loan-penalty-range-2025") { const d = await getJSON("/api/small-loan-penalty.json"); current = `${d.min_penalty}x-${d.max_penalty}x`; claimObj = { metric: "small_loan_penalty_range", min: d.min_penalty, max: d.max_penalty, states: d.states, period: "2025" }; }
        else if (id === "denial-reason-shares-top100-2025") { const d = await getJSON("/api/denial-reasons-top100.json"); const top = Object.keys(d.by_reason).sort((a, b) => d.by_reason[b].median_share_pct - d.by_reason[a].median_share_pct)[0]; const inc = d.by_reason.incomplete; current = `${top}-${d.by_reason[top].median_share_pct}%`; claimObj = { metric: "denial_reason_median_shares", top_reason: top, top_median: d.by_reason[top].median_share_pct, incomplete_median: inc.median_share_pct, incomplete_max: inc.max_share_pct, n_lenders: d.n_lenders, period: "2025" }; }
        else if (id === "rule-hud-ml-2023-05-annual-mip") { const rule = await getJSON("/rules/fha-annual-mip-ml-2023-05.json"); let found = null; for (const c of rule.cells) { if (await sha8({ rule_id: rule.rule_id, ...c }) === h) { found = c; break; } } current = found ? found.annual_mip_bps + "bps" : null; claimObj = found ? { rule_id: rule.rule_id, ...found } : { rule_id: rule.rule_id, changed: true }; }
        else return json({ valid: false, reason: "unknown claim id", id });
      } catch (e) { return json({ valid: false, reason: "lookup failed" }, 502); }
      const nowHash = await sha8(claimObj);
      const status = nowHash === h ? (current === value ? "current" : "hash-current-value-mismatch") : "stale";
      const CH = { m: "MCP tool output", w: "site page", p: "answer page", l: "lender page", s: "state page", t: "top-100 table", h: "Hugging Face dataset", a: "API JSON", r: "RL environment" };
      const issued = chan ? { channel: channel[0], channel_meaning: CH[channel[0]] || "unknown channel", issued_month: "20" + channel.slice(1, 3) + "-" + channel.slice(3, 5) } : { channel: "none", channel_meaning: "receipt issued before channel tagging (pre-October 2026) or segment dropped in copying" };
      try { await tally(env, "verify", `${channel}:${status}`); } catch {}
      // Pull model: a stale receipt routes whoever checks it to the correction itself (corrections.json, spec 7d).
      let correction = null;
      if (status !== "current") {
        try {
          const feed = await getJSON("/corrections.json");
          const hits = (feed.items || []).filter(it => (it.claim_ids || []).includes(id) && it.date).sort((a, b) => (a.date < b.date ? 1 : -1));
          correction = hits.length ? { date: hits[0].date, title: hits[0].title, old_value: hits[0].old_value, new_value: hits[0].new_value, url: hits[0].url, feed: "https://financeratecalc.com/corrections.json" }
                                   : { note: "no dated correction names this claim id; the value changed with a data rebuild", feed: "https://financeratecalc.com/corrections.json" };
        } catch { correction = { feed: "https://financeratecalc.com/corrections.json" }; }
      }
      return json({ receipt: `\u27e6FRC:${id}:${value}:${h}${chan ? ":" + channel : ""}\u27e7`, id, quoted_value: value, current_value: current, status, issued, correction,
        meaning: status === "current" ? "This figure is current and unchanged since the receipt was issued." : status === "stale" ? "The figure was corrected after this receipt was issued; the quoted value may be superseded. See corrections.html." : "The receipt hash matches but the quoted value does not; the quote was altered.",
        corrections: "https://financeratecalc.com/corrections.html", license: "CC BY 4.0",
        transparency: { note: "The snapshot of every claim's value and hash is signed with Sigstore by the publisher's repository workflow and timestamped in the public Rekor log; verify the receipt against it without this server.",
          snapshot: "https://financeratecalc.com/rl-env/frc_citation/receipts-snapshot.json", bundle: "https://financeratecalc.com/transparency/receipts-snapshot.sigstore.json", log: "https://financeratecalc.com/transparency/log.json" } });
    }
    if (path === "/misquotes" && request.method === "GET") {
      if (!env || !env.CREDITS) return json({ error: "store unavailable" }, 503);
      const out = []; let cursor;
      do {
        const list = await env.CREDITS.list({ prefix: "mq:", limit: 1000, cursor });
        for (const k of list.keys) { try { const v = await env.CREDITS.get(k.name); if (v) out.push(JSON.parse(v)); } catch {} }
        cursor = list.list_complete ? undefined : list.cursor;
      } while (cursor);
      out.sort((a, b) => (a.submitted < b.submitted ? 1 : -1));
      return json({ count: out.length, entries: out, note: "Public misquote ledger: AI answers quoting a FinanceRateCalc figure, submitted by readers, graded against the claim contract. Screening signals about AI systems, never about the submitter, who is not recorded.", license: "CC BY 4.0" });
    }
    if (path === "/usage") {
      if (!env || !env.CREDITS) return json({ error: "tally unavailable" }, 503);
      // paginate: the tally passed 1,000 keys in September (directory probes create keys), which cut /usage off at 2026-09-26
      const keys = []; let cursor;
      do { const page = await env.CREDITS.list({ prefix: "tally:", limit: 1000, cursor }); keys.push(...page.keys); cursor = page.list_complete ? undefined : page.cursor; } while (cursor);
      const rows = {};
      for (const k of keys) {
        const [, day, client, ...ev] = k.name.split(":");
        const event = ev.join(":");
        const v = Number((k.metadata && k.metadata.n) || 0);
        rows[day] = rows[day] || {};
        rows[day][client] = rows[day][client] || {};
        rows[day][client][event] = v;
      }
      return json({ generated: new Date().toISOString(),
        note: "Counts of MCP tool calls by day, by the client name reported at initialize, and by tool. Handshakes are not counted. No IP, no user, no submitted data — only counts. Published openly because we ask others to be measurable and should be measurable ourselves.",
        self_test_clients: "clients matching frc-selftest, curl, node, python, postman or insomnia are our own probes",
        days: rows });
    }

    // Authless by design: no OAuth metadata — 404 on well-known and any non-root path
    if (path !== "/" && path !== "") return json({ error: "not found" }, 404);
    if (request.method === "DELETE") return new Response(null, { status: 204, headers: CORS });
    if (request.method === "GET" && (request.headers.get("Accept") || "").includes("text/event-stream"))
      return new Response("SSE stream not offered; POST JSON-RPC to /", { status: 405, headers: CORS });
    if (request.method === "GET")
      return json({ name: "financeratecalc", transport: "streamable-http", endpoint: "POST /", tools: TOOLS.map(t => t.name),
        note: "Remote MCP server. " + INSTRUCTIONS, docs: "https://financeratecalc.com/mcp-server.html" });
    if (request.method !== "POST") return json({ error: "POST JSON-RPC 2.0 messages to /" }, 405);

    let body;
    try { body = await request.json(); } catch { return json(rpcErr(null, -32700, "Parse error"), 400); }
    const msgs = Array.isArray(body) ? body : [body];
    let clientName = labelFromRequest(request);
    let newSession = null;
    const out = [];
    for (const m of msgs) {
      if (!m || m.jsonrpc !== "2.0") { out.push(rpcErr(m && m.id, -32600, "Invalid request")); continue; }
      if (m.method === "initialize") {
        clientName = clientLabel(m.params?.clientInfo);
        newSession = makeSession(clientName);
        out.push(rpc(m.id, { protocolVersion: m.params?.protocolVersion || "2025-06-18",
          capabilities: { tools: {} }, serverInfo: SERVER_INFO, instructions: INSTRUCTIONS }));
      }
      else if (m.method === "notifications/initialized" || (m.method && m.method.startsWith("notifications/"))) { /* ack silently */ }
      else if (m.method === "ping") out.push(rpc(m.id, {}));
      else if (m.method === "server/discover") out.push(rpc(m.id, DISCOVER));
      else if (m.method === "tools/list") out.push(rpc(m.id, { tools: TOOLS, ttlMs: 3600000, cacheScope: "public" }));
      else if (m.method === "tools/call") {
        try {
          // 2026-07-28 stateless clients identify themselves per request in _meta; use it for the tally label when present.
          const meta = m.params?._meta || {};
          const ci = meta["io.modelcontextprotocol/clientInfo"]; if (ci && !m.params?.clientInfo) clientName = clientLabel(ci);
          await tally(env, clientName, "call:" + String(m.params?.name || "unknown").slice(0, 40));
          let args = { ...(m.params?.arguments || {}) };
          // MRTR retry: a client that answered an elicitation sends inputResponses on the retried request; merge accepted content.
          const responses = m.params?.inputResponses || meta.inputResponses;
          if (Array.isArray(responses)) for (const r of responses) if (r && r.action === "accept" && r.content && typeof r.content === "object") args = { ...args, ...r.content };
          const elicit = meta["io.modelcontextprotocol/clientCapabilities"]?.elicitation;
          const mrtr = elicit !== undefined && (elicit.form !== undefined || Object.keys(elicit).length === 0);
          const result = await callTool(m.params?.name, args, env);
          // MRTR: when the tool blocked on missing public conditions and the client can show a form, ask for exactly those fields
          // (never income, score, SSN or any credential; only the parameters the published table is keyed by).
          if (mrtr && result && result.verdict === "block" && Array.isArray(result.reason_codes) && result.reason_codes.includes("CONDITION_MISSING") && Array.isArray(result.required_fields)) {
            const FIELDS = { base_loan_amount: { type: "number", title: "Base loan amount (USD)", minimum: 1 }, ltv_pct: { type: "number", title: "Loan-to-value (%)", minimum: 1, maximum: 200 }, term_years: { type: "integer", title: "Loan term (years)", minimum: 1, maximum: 40 }, case_number_date: { type: "string", title: "FHA case number assignment date", format: "date" } };
            const props = {}; for (const f of result.required_fields) if (FIELDS[f]) props[f] = FIELDS[f];
            out.push({ jsonrpc: "2.0", id: m.id, result: { resultType: "input_required", requestState: "frc:" + String(m.params?.name) + ":" + Date.now().toString(36),
              inputRequests: [{ method: "elicitation/create", params: { mode: "form", message: "To resolve the exact rule cell I need the public loan parameters the table is keyed by; I do not guess them. No income, score or identifiers are requested.", requestedSchema: { type: "object", properties: props, required: Object.keys(props) } } }],
              _meta: { "io.modelcontextprotocol/serverInfo": SERVER_INFO } } });
            continue;
          }
          out.push(rpc(m.id, { content: [{ type: "text", text: JSON.stringify({ ...result, note: GUARDRAIL }, null, 1) }] }));
        } catch (e) {
          out.push(rpc(m.id, { content: [{ type: "text", text: String(e.message || e) }], isError: true }));
        }
      }
      else if (m.id !== undefined) out.push(rpcErr(m.id, -32601, `Method not found: ${m.method}`));
    }
    // ?mode=raw — experimental control: strip the publisher-side intervention fields (quotable sentence,
    // receipt, quoting rules) so the same worker can serve the pre-intervention condition for comparison.
    if (new URL(request.url).searchParams.get("mode") === "raw") {
      const strip = o => { if (o && typeof o === "object") { for (const k of ["quotable_sentence", "claim_receipt", "figure_with_receipt", "receipt_rule", "quoting_rule"]) delete o[k]; } return o; };
      for (const m of out) { try { const c = m.result && m.result.content && m.result.content[0]; if (c && c.text) c.text = JSON.stringify(strip(JSON.parse(c.text))); } catch {} }
    }
    const extra = newSession ? { "Mcp-Session-Id": newSession } : {};
    if (out.length === 0) return new Response(null, { status: 202, headers: { ...CORS, ...extra } });
    const res = json(Array.isArray(body) ? out : out[0]);
    if (newSession) res.headers.set("Mcp-Session-Id", newSession);
    return res;
  }
};
