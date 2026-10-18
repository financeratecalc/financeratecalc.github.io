#!/usr/bin/env node
// Finds public repositories that carry superseded US mortgage rule constants (old FHA limits, pre-2023 MIP), using GitHub
// code search. Deterministic, no model. Output: eval/stale-constants-scan.json and .md — a list for a human to pick from.
// Nothing is posted, no PR is opened. Run in GitHub Actions (needs GITHUB_TOKEN) or locally with GH_TOKEN.
import fs from "node:fs";
const TOKEN = process.env.GH_TOKEN || process.env.GITHUB_TOKEN; if (!TOKEN) { console.error("GH_TOKEN required"); process.exit(1); }
const QUERIES = [
  { q: '"524,225" FHA', stale: "$524,225", num: 524225, year: 2025, meaning: "2025 FHA one-unit floor", current: "$541,287 (2026, HUD ML 2025-23)", current_num: 541287, source: "https://www.hud.gov/news/hud-no-25-145", rule: "frc:rule:fha-forward-loan-limits-2026", repair_case: "RP05" },
  { q: '"498,257" FHA', stale: "$498,257", num: 498257, year: 2024, meaning: "2024 FHA one-unit floor", current: "$541,287 (2026, HUD ML 2025-23)", current_num: 541287, source: "https://www.hud.gov/news/hud-no-25-145", rule: "frc:rule:fha-forward-loan-limits-2026", repair_case: "RP05" },
  { q: '"472,030" FHA', stale: "$472,030", num: 472030, year: 2023, meaning: "2023 FHA one-unit floor", current: "$541,287 (2026, HUD ML 2025-23)", current_num: 541287, source: "https://www.hud.gov/news/hud-no-25-145", rule: "frc:rule:fha-forward-loan-limits-2026", repair_case: "RP05" },
  { q: '"1,209,750" FHA', stale: "$1,209,750", num: 1209750, year: 2025, meaning: "2025 FHA/conforming ceiling", current: "$1,249,125 (2026)", current_num: 1249125, source: "https://www.hud.gov/news/hud-no-25-145", rule: "frc:rule:fha-forward-loan-limits-2026", repair_case: "RP03" },
  { q: '"806,500" conforming', stale: "$806,500", num: 806500, year: 2025, meaning: "2025 conforming baseline", current: "$832,750 (2026, FHFA 2025-11-25)", current_num: 832750, source: "https://www.fhfa.gov/news/news-release/fhfa-announces-conforming-loan-limit-values-for-2026", rule: "frc:rule:fhfa-conforming-loan-limits-2026", repair_case: "RP05" },
  { q: '"766,550" conforming', stale: "$766,550", num: 766550, year: 2024, meaning: "2024 conforming baseline", current: "$832,750 (2026, FHFA 2025-11-25)", current_num: 832750, source: "https://www.fhfa.gov/news/news-release/fhfa-announces-conforming-loan-limit-values-for-2026", rule: "frc:rule:fhfa-conforming-loan-limits-2026", repair_case: "RP05" },
  { q: '"726,200" "loan limit"', stale: "$726,200 used as a loan limit", num: 726200, year: 2023, role_check: true, meaning: "2023 conforming baseline / FHA MIP base-loan threshold", current: "2026 limits: FHA floor $541,287, conforming baseline $832,750; $726,200 remains only the MIP threshold", current_num: 832750, source: "https://www.hud.gov/news/hud-no-25-145", rule: "frc:rule:hud-ml-2023-05-annual-mip", repair_case: "RP02" },
  { q: '"0.85" "annual MIP" FHA', stale: "0.85% annual MIP", num: 0.85, year: 2022, meaning: "pre-2023-03-20 rate", current: "0.55% for the >15y, <=$726,200, >95% LTV cell since ML 2023-05", current_num: 0.55, source: "https://www.hud.gov/sites/dfiles/OCHCO/documents/2023-05hsgml.pdf", rule: "frc:rule:hud-ml-2023-05-annual-mip", repair_case: "RP01" },
  { q: '"2.30" "funding fee" VA', stale: "2.30% VA funding fee", num: 2.3, year: 2022, meaning: "2020-2023 first-use rate", current: "2.15% since 2023-04-07", current_num: 2.15, source: "https://www.va.gov/housing-assistance/home-loans/funding-fee-and-closing-costs/", rule: "frc:rule:va-funding-fee-2023-04-07", repair_case: "RP01" },
];
// STALE_SET=2026 (the pre-registered 2027-01-02 re-scan): the 2026 values are the stale set; the 2027 values are read from rules/index.json if present.
if (process.env.STALE_SET === "2026") {
  QUERIES.length = 0;
  QUERIES.push(
    { q: '"832,750" conforming', stale: "$832,750", num: 832750, year: 2026, meaning: "2026 conforming baseline", current: "the 2027 value (rules/fhfa-conforming-loan-limits-2027.json)", current_num: 0, source: "https://www.fhfa.gov/", rule: "frc:rule:fhfa-conforming-loan-limits-2027", repair_case: "RP05" },
    { q: '"541,287" FHA', stale: "$541,287", num: 541287, year: 2026, meaning: "2026 FHA one-unit floor", current: "the 2027 value (rules/fha-forward-loan-limits-2027.json)", current_num: 0, source: "https://www.hud.gov/", rule: "frc:rule:fha-forward-loan-limits-2027", repair_case: "RP05" },
    { q: '"1,249,125" FHA', stale: "$1,249,125", num: 1249125, year: 2026, meaning: "2026 FHA/conforming ceiling", current: "the 2027 value", current_num: 0, source: "https://www.hud.gov/", rule: "frc:rule:fha-forward-loan-limits-2027", repair_case: "RP03" });
}
const OUT = process.env.SCAN_OUT || "eval/stale-constants-scan";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const hits = [];
for (const Q of QUERIES) {
  const r = await fetch("https://api.github.com/search/code?per_page=30&q=" + encodeURIComponent(Q.q), { headers: { Authorization: "Bearer " + TOKEN, Accept: "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28" } });
  const j = await r.json();
  if (!r.ok) { console.error(Q.q, r.status, j.message); hits.push({ query: Q.q, error: j.message }); await sleep(7000); continue; }
  console.log(Q.q, "->", j.total_count);
  for (const it of j.items || []) hits.push({ query: Q.q, stale: Q.stale, meaning: Q.meaning, current: Q.current, rule: Q.rule, repo: it.repository.full_name, path: it.path, url: it.html_url, repo_url: it.repository.html_url, fork: it.repository.fork, private: it.repository.private });
  await sleep(7000); // code search: 10 requests/min
}
// Context resolution: fetch the file, find the lines that carry the constant, classify each deterministically.
// Classes: dated_correct (labelled with its own year: historical, correct, no action) · presented_as_current ("current",
// "2026", "today", or an unlabelled code constant) · test_or_mock (test/fixture/mock/benchmark path: an external-claim
// mismatch, not necessarily a bug in the project) · changelog (the current value appears beside it) · role_misuse_candidate
// ($726,200 called a loan limit) · unresolved (no year, no signal). Only presented_as_current and role_misuse_candidate get a draft.
const fmt = n => Number.isInteger(n) ? n.toLocaleString("en-US") : String(n);
function classify(line, ctx, Q, path) {
  const win = ctx.toLowerCase(); const l = line.toLowerCase();
  const isTest = /(^|\/)(test|tests|fixtures?|mocks?|__tests__|spec|bench|benchmark|tasks|eval|samples?)(\/|$)|\.(test|spec)\./i.test(path) || /mock|fixture|benchmark/.test(win);
  const yearsLine = [...line.matchAll(/\b(20\d{2})\b/g)].map(m => Number(m[1]));
  const yearsNear = [...ctx.matchAll(/\b(20\d{2})\b/g)].map(m => Number(m[1]));
  const ownYearLine = yearsLine.includes(Q.year) || (Q.role_check && yearsLine.includes(2023));
  const ownYear = ownYearLine || yearsNear.includes(Q.year);
  const NY = Q.year + 1; const currentLine = new RegExp("\\b(current|currently|today|now|this year|as of " + NY + "|for " + NY + "|in " + NY + "|" + NY + ")\\b").test(l);
  const laterYear = yearsNear.some(y => y > Q.year), currentWord = currentLine || /\b(current|currently|today|now|this year)\b/.test(win);
  const hasCurrentValue = ctx.replace(/,/g, "").includes(String(Q.current_num).replace(/,/g, ""));
  if (hasCurrentValue) return { cls: "changelog", why: "the current value appears beside the old one" };
  // a figure labelled with its own year on the same line is historical and correct, unless that same line calls it current
  if (ownYearLine && !currentLine) return { cls: "dated_correct", why: "labelled with its own year (" + (Q.role_check ? 2023 : Q.year) + ") on the same line: historical and correct" };
  if (Q.role_check) { if (/\b(loan limit|lending limit|max(imum)? loan|borrow up to)\b/.test(win) && !/\b(mip|mortgage insurance|threshold|premium)\b/.test(win)) return { cls: "role_misuse_candidate", why: "$726,200 named as a loan limit; it is the MIP base-loan threshold (and the 2023 conforming baseline)" }; return { cls: "unresolved", why: "$726,200 present; role not clear from context" }; }
  if (isTest) return { cls: "test_or_mock", why: "test, fixture, mock, benchmark or sample path: external-claim mismatch, not necessarily a project bug" + (currentWord || laterYear ? "; labelled as current/2026" : "") };
  if (ownYear && !currentWord && !laterYear) return { cls: "dated_correct", why: "labelled with its own year (" + Q.year + ") nearby: historical and correct" };
  if (currentLine) return { cls: "presented_as_current", why: "the line calls the " + Q.year + " value current or 2026; official " + Q.current };
  if (currentWord || laterYear) return { cls: "presented_as_current", why: (laterYear ? "2026 appears beside the " + Q.year + " value" : "called current nearby") + "; official " + Q.current, confidence: "lower" };
  if (/[=:]\s*\$?\s*['"]?\$?\s*[\d,.]+\s*['"]?\s*[,;)]?\s*$/.test(line.trim()) && !ownYear) return { cls: "presented_as_current", why: "unlabelled constant in code; the running value is the " + Q.year + " figure" };
  return { cls: "unresolved", why: "no year label and no currency signal in the surrounding lines" };
}
for (const h of hits.filter(h => h.repo)) {
  const Q = QUERIES.find(q => q.q === h.query);
  try {
    const raw = h.url.replace("https://github.com/", "https://raw.githubusercontent.com/").replace("/blob/", "/");
    const r = await fetch(raw); if (!r.ok) { h.context = { cls: "unresolved", why: "file not fetchable (" + r.status + ")" }; continue; }
    const text = (await r.text()).slice(0, 400000); const lines = text.split(/\r?\n/);
    const needle = Q.num >= 1000 ? new RegExp("\\b" + fmt(Q.num).replace(/,/g, ",?") + "\\b") : new RegExp("\\b" + String(Q.num).replace(".", "\\.") + "0?\\b");
    const idx = lines.findIndex(x => needle.test(x));
    if (idx < 0) { h.context = { cls: "unresolved", why: "constant not found in fetched file (search index may be stale)" }; continue; }
    const ctx = lines.slice(Math.max(0, idx - 2), idx + 3).join("\n");
    const L = lines[idx]; const mpos = L.search(needle); const seg = L.length > 300 ? L.slice(Math.max(0, mpos - 140), mpos + 160) : L;
    h.line = idx + 1; h.excerpt = seg.trim().slice(0, 300); h.context = classify(seg, L.length > 300 ? seg : ctx, Q, h.path);
    h.evidence = { stale_value: h.stale, stale_year: Q.year, official_current: Q.current, official_source: Q.source, frc_rule: Q.rule, repair_case: Q.repair_case };
    if (h.context.cls === "presented_as_current" || h.context.cls === "role_misuse_candidate") h.draft = { title: "Update " + (Q.role_check ? "the $726,200 figure: it is the FHA MIP threshold, not a loan limit" : Q.meaning + " to the 2026 value"), body: "Line " + h.line + " of " + h.path + " reads: `" + h.excerpt + "`. " + (Q.role_check ? "$726,200 is the base-loan threshold in HUD Mortgagee Letter 2023-05 (FHA annual MIP table) and the 2023 conforming baseline; it is not a current loan limit. 2026: FHA one-unit floor $541,287, conforming baseline $832,750." : "That is the " + Q.year + " figure (" + Q.meaning + "). For 2026 the official value is " + Q.current + ".") + " Source: " + Q.source + ". Machine-readable table with effective dates: https://financeratecalc.com/rules/index.json (" + Q.rule + "). If the page is meant to describe " + Q.year + ", a year label beside the figure would make that clear and this note can be closed." };
    await sleep(300);
  } catch (e) { h.context = { cls: "unresolved", why: "fetch error: " + e.message }; }
}
const byRepo = {};
for (const h of hits.filter(h => h.repo)) { byRepo[h.repo] = byRepo[h.repo] || { repo: h.repo, repo_url: h.repo_url, files: [] }; byRepo[h.repo].files.push({ path: h.path, url: h.url, line: h.line || null, excerpt: h.excerpt || null, class: h.context ? h.context.cls : "unresolved", why: h.context ? h.context.why : "", stale: h.stale, meaning: h.meaning, current: h.current, evidence: h.evidence || null, draft: h.draft || null }); }
const ORDER = { presented_as_current: 0, role_misuse_candidate: 1, test_or_mock: 2, unresolved: 3, changelog: 4, dated_correct: 5 };
for (const r of Object.values(byRepo)) { r.files.sort((a, b) => ORDER[a.class] - ORDER[b.class]); r.top_class = r.files[0].class; }
const repos = Object.values(byRepo).sort((a, b) => ORDER[a.top_class] - ORDER[b.top_class] || b.files.length - a.files.length);
const counts = {}; for (const r of repos) for (const f of r.files) counts[f.class] = (counts[f.class] || 0) + 1;
const out = { scan: "stale-mortgage-constants", generated: new Date().toISOString(), method: "GitHub code search for superseded FHA/FHFA/MIP/VA constants, then each file is fetched and the carrying line classified deterministically (dated_correct / presented_as_current / test_or_mock / changelog / role_misuse_candidate / unresolved) against the official value and source. No model. Nothing is posted; drafts exist only for presented_as_current and role_misuse_candidate, and a human reads the file before any draft leaves this repository.", classes: counts, queries: QUERIES.map(q => q.q), total_hits: hits.filter(h => h.repo).length, repos_with_hits: repos.length, errors: hits.filter(h => h.error), repos };
fs.mkdirSync("eval", { recursive: true });
fs.writeFileSync(OUT + ".json", JSON.stringify(out, null, 1) + "\n");
const md = [`# Stale mortgage constants in public code — scan ${out.generated.slice(0, 10)}`, ``, `${out.total_hits} hits in ${repos.length} repositories. Each line classified from the file itself; nothing posted. Classes: ${Object.entries(counts).map(([k, v]) => k + " " + v).join(" · ")}.`, ``,
  `- **presented_as_current**: an old figure called current / 2026, or an unlabelled constant in code. A draft note exists in the JSON; a human reads the file before it goes anywhere.`, `- **role_misuse_candidate**: $726,200 named as a loan limit.`, `- **test_or_mock**: in a test, fixture, mock or benchmark path: an external-claim mismatch, not necessarily a project bug.`, `- **dated_correct**: labelled with its own year; historical and correct; no action.`, `- **changelog**: the current value sits beside the old one.`, `- **unresolved**: no signal either way.`, ``,
  `| class | repo | file:line | excerpt | stale → official |`, `|---|---|---|---|---|`];
for (const r of repos) for (const f of r.files) md.push(`| ${f.class} | [${r.repo}](${r.repo_url}) | [${f.path.split("/").pop()}${f.line ? ":" + f.line : ""}](${f.url}) | ${(f.excerpt || f.why).replace(/\|/g, "\\|").slice(0, 120)} | ${f.stale} → ${f.current} |`);
fs.writeFileSync(OUT + ".md", md.join("\n") + "\n");
console.log(`${out.total_hits} hits, ${repos.length} repos -> eval/stale-constants-scan.{json,md}`);
