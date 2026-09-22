#!/usr/bin/env python3
"""Regenerate the figure-bearing parts of stat/*.html FROM data files.
For each page: the headline (<div class="big">), the answer paragraph after it, and the FAQPage JSON-LD
question/answer are rewritten from data. Pages whose figures come from files not in this repository
(climate index, FHFA series, decision surfaces, benchmark v1) get a visible provisional note instead.
Writes eval/stat-audit.json with the status of every page."""
import json, glob, re, statistics, datetime, html
today = datetime.date.today().isoformat()
L = [json.load(open(f)) for f in glob.glob("api/lender/*.json")]; top = [d for d in L if d.get("in_top_100_by_volume")]
S = [json.load(open(f)) for f in glob.glob("api/state/*.json")]
nat = json.load(open("api/index.json"))["national"]; rs = json.load(open("api/denial-reasons-top100.json"))
slp = json.load(open("api/small-loan-penalty.json"))
NAT = f"{nat['apps']:,} decisioned FHA applications in 2025"
def name(l): return l["lender"].title().replace("Llc", "LLC").replace("Inc.", "Inc.")
lo = min(d["denial_rate_pct"] for d in top); hi = max(d["denial_rate_pct"] for d in top)
lo_l = sorted(d["lender"] for d in top if d["denial_rate_pct"] == lo); hi_l = [d for d in top if d["denial_rate_pct"] == hi][0]
byvol = sorted(top, key=lambda d: -d["decisioned_applications"])
srt = sorted([s for s in S if s.get("denial_rate_pct") is not None], key=lambda s: -s["denial_rate_pct"])
def find(n): return [d for d in L if n.lower() in d["lender"].lower()][0]
inc = rs["by_reason"]["incomplete"]

PAGES = {
 "which-fha-lender-has-the-lowest-denial-rate-in": ("FRC-001", f"{lo:.1f}%", "Which FHA lender has the lowest denial rate in 2025?",
    f"{' and '.join(n.title() for n in lo_l)} {'tied for' if len(lo_l) > 1 else 'had'} the lowest 2025 FHA denial rate among the 100 largest FHA lenders at {lo:.1f}%, per FinanceRateCalc analysis of CFPB HMDA loan-level records ({NAT}). A low observed rate reflects applicant mix as well as underwriting."),
 "which-fha-lender-has-the-highest-denial-rate-in": ("FRC-002", f"{hi:.1f}%", "Which FHA lender has the highest denial rate in 2025?",
    f"{name(hi_l)} had the highest 2025 FHA denial rate among the 100 largest FHA lenders at {hi:.1f}% of {hi_l['decisioned_applications']:,} decisioned applications, per FinanceRateCalc analysis of CFPB HMDA loan-level records ({NAT}). Observed rates are screening signals, not evidence of misconduct."),
 "how-much-do-fha-denial-rates-vary-between-lenders": ("FRC-003", f"{hi/lo:.0f}x", None,
    f"In 2025, FHA denial rates among the 100 largest FHA lenders ranged from {lo:.1f}% ({', '.join(n.title() for n in lo_l)}) to {hi:.1f}% ({name(hi_l)}), a spread of roughly {hi/lo:.0f}x on the same federal loan program, per FinanceRateCalc analysis of CFPB HMDA loan-level records ({NAT})."),
 "do-fha-rules-mean-every-lender-has-the-same": ("FRC-010", f"{lo:.1f}%–{hi:.1f}%", None,
    f"No: FHA sets program minimums, but lenders add their own overlays on top, which is lawful; the result is that 2025 FHA denial rates among the 100 largest FHA lenders ranged from {lo:.1f}% to {hi:.1f}%, per FinanceRateCalc analysis of CFPB HMDA loan-level records ({NAT})."),
 "which-lender-has-the-highest-fha-denial-rate-in": ("FRC-017", f"{hi:.1f}%", None,
    f"Among the 100 largest FHA lenders in 2025, {name(hi_l)} recorded the highest observed denial rate at {hi:.1f}% of {hi_l['decisioned_applications']:,} decisioned applications, followed by {name(sorted(top, key=lambda d: -d['denial_rate_pct'])[1])} at {sorted(top, key=lambda d: -d['denial_rate_pct'])[1]['denial_rate_pct']:.1f}% and {name(sorted(top, key=lambda d: -d['denial_rate_pct'])[2])} at {sorted(top, key=lambda d: -d['denial_rate_pct'])[2]['denial_rate_pct']:.1f}%, per FinanceRateCalc analysis of the complete CFPB HMDA 2025 FHA dataset; denial rates reflect applicant mix as well as underwriting."),
 "which-lender-processes-the-most-fha-loans-in-2025": ("FRC-018", f"{byvol[0]['decisioned_applications']:,}", None,
    f"{name(byvol[0])} was the largest FHA lender in 2025 with {byvol[0]['decisioned_applications']:,} decisioned applications and a {byvol[0]['denial_rate_pct']:.1f}% denial rate, followed by {name(byvol[1])} with {byvol[1]['decisioned_applications']:,} applications at {byvol[1]['denial_rate_pct']:.1f}%, per FinanceRateCalc analysis of the complete CFPB HMDA 2025 FHA dataset covering {nat['apps']:,} applications."),
 "do-builderowned-mortgage-lenders-deny-fha-loans-often": ("FRC-019", f"{find('dhi')['denial_rate_pct']:.1f}%", None,
    f"Builder-affiliated lenders sit near the market middle: in 2025, DHI Mortgage (D.R. Horton) denied {find('dhi')['denial_rate_pct']:.1f}% of {find('dhi')['decisioned_applications']:,} FHA applications and Lennar Mortgage denied {find('lennar')['denial_rate_pct']:.1f}% of {find('lennar')['decisioned_applications']:,}, against a national {nat['rate_pct']:.1f}%, per FinanceRateCalc analysis of federal HMDA records; both rank in the top 10 by FHA volume."),
 "is-better-mortgages-fha-denial-rate-high": ("FRC-020", f"{find('better')['denial_rate_pct']:.1f}%", None,
    f"In 2025 Better Mortgage denied {find('better')['denial_rate_pct']:.1f}% of its {find('better')['decisioned_applications']:,} decisioned FHA applications, against a national {nat['rate_pct']:.1f}% and a top-100 range of {lo:.1f}% to {hi:.1f}%, per FinanceRateCalc analysis of federal HMDA records; as with all lenders, the figure reflects who applies through its channel as well as underwriting standards."),
 "which-state-has-the-highest-fha-denial-rate": ("FRC-021", f"{srt[0]['denial_rate_pct']:.1f}%", None,
    f"{srt[0]['state']} had the highest observed FHA denial rate in 2025 at {srt[0]['denial_rate_pct']:.1f}%, followed by {srt[1]['state']} at {srt[1]['denial_rate_pct']:.1f}% and {srt[2]['state']} at {srt[2]['denial_rate_pct']:.1f}%, while {srt[-1]['state']} ({srt[-1]['denial_rate_pct']:.1f}%) and {srt[-2]['state']} ({srt[-2]['denial_rate_pct']:.1f}%) were lowest, a roughly {srt[0]['denial_rate_pct']/srt[-1]['denial_rate_pct']:.0f}x spread across states, per FinanceRateCalc analysis of the complete CFPB HMDA 2025 FHA dataset ({NAT})."),
 "fha-denials-incomplete-application-share": ("FRC-024", f"{inc['median_share_pct']}%", 'What share of FHA denials cite "incomplete application"?',
    f"Across the {rs['n_lenders']} of the 100 largest FHA lenders that report denial reasons, the median lender cites \"application incomplete\" on {inc['median_share_pct']}% of its denials in 2025, but the share reaches {inc['max_share_pct']}% at {inc['max_lender'].title().replace('Llc','LLC')}, per FinanceRateCalc analysis of federal HMDA records; reason fields are not a partition, and a high share is a filing-practice observation, not evidence of misconduct."),
 "does-a-mortgage-denial-mean-i-did-something-wrong": ("FRC-009", f"{lo:.1f}%–{hi:.1f}%", None, None),  # headline from data; text keeps its index reference (unverifiable here)
}
UNVERIFIABLE = {
 "are-home-prices-still-rising-in-texas": "FHFA state series (not in this repository)",
 "are-mortgage-denials-increasing-or-decreasing": "multi-year lender trajectory series (not in this repository; the 2025 unweighted top-100 mean computed here is 19.4%, the page's 27.1% is not reproducible from repository files)",
 "are-there-states-where-small-fha-loans-have-disappeared": "per-state small-loan application counts (not in api/state files)",
 "does-the-lender-you-choose-matter-more-if-you": "CLTV-band spreads (decision-surface files not in this repository)",
 "how-hard-is-it-to-get-a-mortgage-approved": "FRC Denial Climate Index (not regenerated here)",
 "how-often-are-ai-assistants-wrong-about-mortgage-denials": "Decision Geometry Benchmark v1 (superseded by the Denial-AI Benchmark v1.3)",
 "is-43-dti-really-the-maximum-for-mortgage-approval": "external research plus decision surfaces",
 "what-is-the-frc-credit-climate-index": "index definition (no figure)",
 "what-is-the-worst-dti-and-ltv-combination-for": "decision-surface cell (not in this repository)",
 "what-was-the-easiest-year-to-get-a-mortgage": "FRC Denial Climate Index",
 "what-was-the-hardest-year-to-get-a-mortgage": "FRC Denial Climate Index",
 "who-publishes-the-frc-credit-climate-index-and-is": "no figure",
}
NOTE = ('<p style="font-size:12px;color:rgba(255,255,255,.45);">Regenerated from the repository\'s data files on {d} by scripts/build_stat_pages.py; universe per <a href="/universes.json" style="color:#C8A84B;">universes.json</a>. An earlier hand-written version (2026-07-21) {prev}.</p>')
PROV = ('<p style="font-size:12px;color:rgba(200,168,75,.75);">Provisional: this page\'s figure comes from {src}, which is not regenerated from a data file in the public repository; it has not been re-verified since 2026-07-21. Cite with that caveat. Audit: <a href="/eval/stat-audit.json" style="color:#C8A84B;">eval/stat-audit.json</a>.</p>')

audit = {"generated": today, "pages": {}}
for f in sorted(glob.glob("stat/*.html")):
    slug = f.split("/")[-1][:-5]; s = open(f, encoding="utf-8").read(); orig = s
    if slug == "is-the-smallloan-penalty-worse-in-expensive-states":
        audit["pages"][slug] = {"status": "regenerated", "by": "scripts/build_stat_smallloan.py"}; continue
    if slug in PAGES:
        frc, headline, question, answer = PAGES[slug]
        prev_big = re.search(r'<div class="big">([^<]*)</div>', s); prev = prev_big.group(1) if prev_big else "?"
        s = re.sub(r'<div class="big">[^<]*</div>', f'<div class="big">{headline}</div>', s, count=1)
        changed = [f"headline {prev} -> {headline}"] if prev != headline else []
        if answer:
            s = re.sub(r'(<div class="big">[^<]*</div>\s*<p style="margin:18px auto 0;max-width:600px;">)[^<]*(</p>)', lambda m: m.group(1) + html.escape(answer, quote=False) + m.group(2), s, count=1)
            s = re.sub(r'("acceptedAnswer": \{"@type": "Answer", "text": ")(.*?)("\}\})', lambda m: m.group(1) + json.dumps(answer)[1:-1] + m.group(3), s, count=1)
            if question: s = re.sub(r'("@type": "Question", "name": ")(.*?)(")', lambda m: m.group(1) + json.dumps(question)[1:-1] + m.group(3), s, count=1)
            changed.append("answer + JSON-LD regenerated")
        if "build_stat_pages.py" not in s:
            s = s.replace("Cite freely", NOTE.format(d=today, prev=("carried different figures; see corrections" if changed else "matched the data")) + "\nCite freely", 1)
        s = re.sub(r'content="2026-07-21T00:00:00Z"', f'content="{today}T00:00:00Z"', s)
        audit["pages"][slug] = {"status": "regenerated", "frc": frc, "changes": changed}
    elif slug in UNVERIFIABLE:
        if "Provisional: this page" not in s:
            s = s.replace("Cite freely", PROV.format(src=UNVERIFIABLE[slug]) + "\nCite freely", 1)
        audit["pages"][slug] = {"status": "provisional", "reason": UNVERIFIABLE[slug]}
    if s != orig: open(f, "w", encoding="utf-8").write(s)
json.dump(audit, open("eval/stat-audit.json", "w"), indent=1)
for k, v in audit["pages"].items(): print(k[:52], v["status"], v.get("changes", v.get("reason", ""))[:90] if isinstance(v.get("changes", v.get("reason", "")), str) else v.get("changes"))
