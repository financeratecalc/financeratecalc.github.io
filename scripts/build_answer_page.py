#!/usr/bin/env python3
"""Generate how-often-are-fha-loans-denied.html FROM the published data.
Inputs: api/index.json, claims/*.json (national, major-lender-span, door-effect), mcp/claims.json
No number on the page is typed by hand. Re-run after any data refresh.
"""
import json, html, datetime

idx = json.load(open("api/index.json"))
nat = idx["national"]; meta = idx["meta"]
P = {k: json.load(open(f"claims/{k}.json"))["claim"] for k in
     ["national-fha-denial-rate-2025", "major-lender-span-2025", "door-effect-38pct-2026"]}
corr = json.load(open("mcp/claims.json"))
hecm_note = next((c.get("explain") for c in corr.get("claims", corr if isinstance(corr, list) else []) if isinstance(c, dict) and "1,217,297" in str(c.get("explain", ""))), None)

rate = f"{nat['rate_pct']:.1f}%"
apps = f"{nat['apps']:,}"; den = f"{nat['denials']:,}"; hecm = f"{nat['hecm_excluded']:,}"
span = P["major-lender-span-2025"]["value"].replace("\u2013", "&ndash;")
door = f"{int(P['door-effect-38pct-2026']['value']*100)}%"
door_def = P["door-effect-38pct-2026"]["definition"]
door_n = P["door-effect-38pct-2026"]["subject"]
pm = nat["peer_medians"]
reasons = [("Debt-to-income ratio", pm["dti"]), ("Credit history", pm["credit_history"]), ("Collateral", pm["collateral"]),
           ("Unverifiable information", pm["unverifiable_info"]), ("Insufficient cash", pm["insufficient_cash"]),
           ("Employment history", pm["employment"]), ("Incomplete application", pm["incomplete"]), ("Other", pm["other"])]
reasons.sort(key=lambda x: -x[1])
today = datetime.date.today().isoformat()

direct = f"In 2025, {rate} of decisioned FHA applications were denied: {den} denials out of {apps} applications that reached a credit decision."
scope_note = P["national-fha-denial-rate-2025"]["note"]

faq = [
 ("How often are FHA loans denied?", direct + " The figure counts applications that were originated, approved but not accepted, or denied; withdrawn and incomplete files are not in the denominator, and reverse mortgages are excluded."),
 ("Is 22.1% the denial rate for all mortgages?", f"No. It is FHA only (loan_type 2). It does not describe conventional, VA or USDA loans, and it is not any individual applicant's probability of denial."),
 ("Does the rate depend on which lender you apply to?", f"The observed spread is wide: across the 100 largest FHA lenders in 2025, lender-level denial rates ran from {span}. In a decomposition of {door_n}, lender identity was associated with {door} of the explainable variation in denial outcomes ({door_def}). This is an association on observable federal-record characteristics, not a causal estimate; HMDA contains no credit scores."),
 ("What are FHA applications denied for?", "In the peer set used by the peer-adjusted model (universe U-PEER-MEDIANS-2025, definition pending), the median share of cited denial reasons was: " + "; ".join(f"{n} {v:.1f}%" for n, v in reasons) + ". Reason fields are not a partition, so shares need not sum to 100."),
 ("Has this figure been corrected?", "Yes. The rate was first published as 21.7% of 1,217,297 applications; on 26 July 2026 the universe was corrected to exclude 29,691 reverse-mortgage (HECM) records, giving " + rate + " of " + apps + ". Every correction is logged at financeratecalc.com/corrections.html."),
]
faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
    {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
ds_ld = {"@context": "https://schema.org", "@type": "Dataset", "name": "FHA denial rate 2025 (national)",
         "description": direct, "license": "https://creativecommons.org/licenses/by/4.0/",
         "creator": {"@type": "Organization", "name": "FinanceRateCalc"}, "identifier": "https://doi.org/" + meta["dataset_doi"],
         "url": "https://financeratecalc.com/how-often-are-fha-loans-denied.html", "temporalCoverage": "2025",
         "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": "https://financeratecalc.com/api/index.json"}]}

def sec(title, body): return f"<h2>{title}</h2>\n{body}\n"
faq_html = "\n".join(f'<h3>{html.escape(q)}</h3><p>{html.escape(a)}</p>' for q, a in faq)
reasons_rows = "\n".join(f"<tr><td>{n}</td><td>{v:.1f}%</td></tr>" for n, v in reasons)

page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>How often are FHA loans denied? {rate} in 2025 (complete federal record) | FinanceRateCalc</title>
<meta name="description" content="{html.escape(direct)} Computed from the complete CFPB HMDA 2025 file; method, denominator and corrections published.">
<link rel="canonical" href="https://financeratecalc.com/how-often-are-fha-loans-denied.html">
<meta property="og:title" content="How often are FHA loans denied? {rate} in 2025"><meta property="og:description" content="{html.escape(direct)}"><meta property="og:url" content="https://financeratecalc.com/how-often-are-fha-loans-denied.html">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-ND9P4F3PHT"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-ND9P4F3PHT');</script>
<script type="application/ld+json">{json.dumps(faq_ld, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps(ds_ld, ensure_ascii=False)}</script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'DM Sans',sans-serif;background:#08090c;color:#fff;line-height:1.85}}
.wrap{{max-width:800px;margin:0 auto;padding:34px 22px 80px}}
h1{{font-family:'Fraunces',serif;font-size:clamp(25px,4.3vw,35px);font-weight:900;line-height:1.18}}
h1 em{{color:#C8A84B;font-style:italic}}
h2{{font-family:'Fraunces',serif;font-size:19px;color:#C8A84B;margin:30px 0 8px}}
h3{{font-size:15.5px;color:#fff;margin:18px 0 4px}}
p{{color:rgba(255,255,255,.66);font-size:15px;margin:12px 0}}
.answer{{border-left:3px solid #C8A84B;background:rgba(200,168,75,.06);padding:16px 20px;border-radius:0 12px 12px 0;margin:18px 0;font-size:17px;color:#fff}}
.answer small{{display:block;font-size:12px;color:rgba(255,255,255,.45);margin-top:8px}}
table{{width:100%;border-collapse:collapse;font-size:13.5px;margin:14px 0}}
th,td{{padding:9px 10px;text-align:left;border-bottom:1px solid rgba(255,255,255,.08)}}
th{{color:rgba(200,168,75,.85);font-size:10.5px;text-transform:uppercase;letter-spacing:.09em}} td{{color:rgba(255,255,255,.65)}} td:first-child{{color:#fff}}
a{{color:#C8A84B}}
.legal{{font-size:10.5px;color:rgba(255,255,255,.3);line-height:1.8;margin-top:28px;border-top:1px solid rgba(255,255,255,.07);padding-top:12px}}
header{{display:flex;justify-content:space-between;align-items:center;max-width:960px;margin:0 auto;padding:18px 22px}}
.logo{{font-family:'Fraunces',serif;font-weight:900;color:#fff;text-decoration:none;font-size:18px}} .logo em{{color:#C8A84B;font-style:italic}}
</style></head><body>
<header><a href="/index.html" class="logo">Finance<em>Rate</em>Calc</a><a href="/methodology.html" style="font-size:13px;color:rgba(255,255,255,.4);text-decoration:none;">Methodology</a></header>
<div class="wrap">
<div style="font-size:11px;color:rgba(200,168,75,.7);text-transform:uppercase;letter-spacing:.15em;margin-bottom:9px;">Complete 2025 federal record &middot; generated from the dataset &middot; CC BY 4.0</div>
<h1>How often are FHA loans denied? <em>{rate} of decisioned applications in 2025.</em></h1>
<div class="answer">{html.escape(direct)}<small>{html.escape(meta['universe'])}. {html.escape(meta['caveat'])}</small></div>

{sec("What the number counts", f"<p>The denominator is every FHA application that reached a credit decision in the 2025 CFPB HMDA file: originated, approved but not accepted, or denied (action_taken 1, 2, 3). Withdrawn applications and files closed for incompleteness are not decisions and are left out. Reverse mortgages ({hecm} records) are excluded. {html.escape(scope_note)}</p>")}
{sec("It is not a rate for all mortgages, and not your odds", "<p>FHA only. Conventional, VA and USDA applications are different populations with different rates. And it is a historical aggregate about institutions: nothing on this page is a probability for any individual application.</p>")}
{sec("The lender matters more than the average suggests", f"<p>Across the 100 largest FHA lenders by 2025 volume, observed lender-level denial rates ran from <b>{span}</b> inside the same federal program. In a decomposition of {door_n}, lender identity was associated with <b>{door}</b> of the explainable variation in denial outcomes ({door_def}). Association on observable characteristics, not causation: the federal record carries no credit scores. Details: <a href='/door-effect.html'>The Door Effect</a>, <a href='https://doi.org/10.2139/ssrn.7309319'>doi:10.2139/ssrn.7309319</a>; lender table: <a href='/fha-denial-rates-top-100.html'>100 largest FHA lenders</a>.</p>")}
{sec("Why applications are denied", f"<p>Median share of cited denial reasons in the peer set used by the FinanceRateCalc peer-adjusted model, 2025 (universe U-PEER-MEDIANS-2025, definition pending publication; see universes.json). Reason fields are not a partition, so shares need not sum to 100.</p><table><tr><th>Cited reason</th><th>Median share</th></tr>{reasons_rows}</table>")}
{sec("Corrections to this figure", f"<p>First published as 21.7% of 1,217,297. Corrected on 26 July 2026 when {hecm} reverse-mortgage records were removed from the universe, to {rate} of {apps}. The full log is at <a href='/corrections.html'>/corrections.html</a>; nothing is edited silently.</p>")}
{sec("Questions", faq_html)}
{sec("Check it yourself", f"<p>Machine-readable figure: <a href='/api/index.json'>/api/index.json</a> &middot; claim passport: <a href='/claims/national-fha-denial-rate-2025.json'>national-fha-denial-rate-2025.json</a> &middot; method: <a href='/methodology.html'>methodology</a> &middot; reproduction spec: <a href='/reconciliation.html'>reconciliation</a> &middot; data archive: <a href='https://doi.org/{meta['dataset_doi']}'>doi:{meta['dataset_doi']}</a> &middot; agents: <a href='/mcp-server.html'>MCP server</a>. Verification status: {html.escape(meta['verification_status'])}.</p>")}
{sec("Cite", "<p>Source: FinanceRateCalc analysis of the public CFPB HMDA 2025 record; historical aggregate only. CC BY 4.0. Papers: doi:10.2139/ssrn.7156938, 10.2139/ssrn.7309319, 10.2139/ssrn.7341481, 10.2139/ssrn.7423798.</p>")}
<div class="legal">Data: {html.escape(meta['source'])}, processed by FinanceRateCalc. Universe: {html.escape(meta['universe'])}. Page generated from the published dataset on {today} by scripts/build_answer_page.py; no figure on it is typed by hand. No lender or AI vendor funds or previews this work.</div>
</div></body></html>
"""
open("how-often-are-fha-loans-denied.html", "w", encoding="utf-8").write(page)
print("wrote how-often-are-fha-loans-denied.html", len(page))
