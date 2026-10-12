#!/usr/bin/env node
// Finds public repositories that carry superseded US mortgage rule constants (old FHA limits, pre-2023 MIP), using GitHub
// code search. Deterministic, no model. Output: eval/stale-constants-scan.json and .md — a list for a human to pick from.
// Nothing is posted, no PR is opened. Run in GitHub Actions (needs GITHUB_TOKEN) or locally with GH_TOKEN.
import fs from "node:fs";
const TOKEN = process.env.GH_TOKEN || process.env.GITHUB_TOKEN; if (!TOKEN) { console.error("GH_TOKEN required"); process.exit(1); }
const QUERIES = [
  { q: '"524,225" FHA', stale: "$524,225", meaning: "2025 FHA one-unit floor", current: "$541,287 (2026, HUD ML 2025-23)", rule: "frc:rule:fha-forward-loan-limits-2026" },
  { q: '"498,257" FHA', stale: "$498,257", meaning: "2024 FHA one-unit floor", current: "$541,287 (2026, HUD ML 2025-23)", rule: "frc:rule:fha-forward-loan-limits-2026" },
  { q: '"472,030" FHA', stale: "$472,030", meaning: "2023 FHA one-unit floor", current: "$541,287 (2026, HUD ML 2025-23)", rule: "frc:rule:fha-forward-loan-limits-2026" },
  { q: '"1,209,750" FHA', stale: "$1,209,750", meaning: "2025 FHA/conforming ceiling", current: "$1,249,125 (2026)", rule: "frc:rule:fha-forward-loan-limits-2026" },
  { q: '"806,500" conforming', stale: "$806,500", meaning: "2025 conforming baseline", current: "$832,750 (2026, FHFA 2025-11-25)", rule: "frc:rule:fhfa-conforming-loan-limits-2026" },
  { q: '"766,550" conforming', stale: "$766,550", meaning: "2024 conforming baseline", current: "$832,750 (2026, FHFA 2025-11-25)", rule: "frc:rule:fhfa-conforming-loan-limits-2026" },
  { q: '"726,200" "loan limit"', stale: "$726,200 used as a loan limit", meaning: "2023 conforming baseline / FHA MIP base-loan threshold", current: "2026 limits: FHA floor $541,287, conforming baseline $832,750; $726,200 remains only the MIP threshold", rule: "frc:rule:hud-ml-2023-05-annual-mip" },
  { q: '"0.85" "annual MIP" FHA', stale: "0.85% annual MIP", meaning: "pre-2023-03-20 rate", current: "0.55% for the >15y, <=$726,200, >95% LTV cell since ML 2023-05", rule: "frc:rule:hud-ml-2023-05-annual-mip" },
  { q: '"2.30" "funding fee" VA', stale: "2.30% VA funding fee", meaning: "2020-2023 first-use rate", current: "2.15% since 2023-04-07", rule: "frc:rule:va-funding-fee-2023-04-07" },
];
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
const byRepo = {};
for (const h of hits.filter(h => h.repo)) { byRepo[h.repo] = byRepo[h.repo] || { repo: h.repo, repo_url: h.repo_url, files: [] }; byRepo[h.repo].files.push({ path: h.path, url: h.url, stale: h.stale, meaning: h.meaning, current: h.current, rule: h.rule }); }
const repos = Object.values(byRepo).sort((a, b) => b.files.length - a.files.length);
const out = { scan: "stale-mortgage-constants", generated: new Date().toISOString(), method: "GitHub code search for superseded FHA/FHFA/MIP/VA constants; deterministic; no model; nothing posted. A hit is a candidate, not a confirmed bug: the file may be historical, a test, or a changelog. A human reads the file before anything is proposed.", queries: QUERIES.map(q => q.q), total_hits: hits.filter(h => h.repo).length, repos_with_hits: repos.length, errors: hits.filter(h => h.error), repos };
fs.mkdirSync("eval", { recursive: true });
fs.writeFileSync("eval/stale-constants-scan.json", JSON.stringify(out, null, 1) + "\n");
const md = [`# Stale mortgage constants in public code — scan ${out.generated.slice(0, 10)}`, ``, `${out.total_hits} hits in ${repos.length} repositories. Candidates only; a hit may be historical text, a test fixture or a changelog. Nothing is posted; a human picks.`, ``, `| repo | files | stale constant | what it was | current |`, `|---|---|---|---|---|`];
for (const r of repos.slice(0, 60)) md.push(`| [${r.repo}](${r.repo_url}) | ${r.files.map(f => `[${f.path.split("/").pop()}](${f.url})`).join(", ")} | ${[...new Set(r.files.map(f => f.stale))].join("; ")} | ${[...new Set(r.files.map(f => f.meaning))].join("; ")} | ${[...new Set(r.files.map(f => f.current))].join("; ")} |`);
fs.writeFileSync("eval/stale-constants-scan.md", md.join("\n") + "\n");
console.log(`${out.total_hits} hits, ${repos.length} repos -> eval/stale-constants-scan.{json,md}`);
