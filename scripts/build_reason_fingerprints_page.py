#!/usr/bin/env python3
"""Rebuild the body of fha-denial-reasons-by-lender.html from api/lender/*.json (share-of-denials-citing basis).

    python3 scripts/build_reason_fingerprints_page.py [--check]

The page shell (head, nav, footer) is kept; everything between the markers is regenerated, and the FAQ structured
data is re-read from the same figures. No number is typed here. --check exits 1 if the committed page differs.
"""
import glob
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "fha-denial-reasons-by-lender.html")
LABEL = {"dti": "DTI", "credit_history": "Credit history", "collateral": "Collateral", "insufficient_cash": "Insufficient cash",
         "incomplete": "Incomplete application", "unverifiable_info": "Unverifiable info", "employment": "Employment",
         "mortgage_insurance_denied": "Mortgage insurance denied", "other": "Other"}


REG = json.load(open(os.path.join(ROOT, "data", "release-day-registry.json"), encoding="utf-8"))["lenders"]


def name(l):
    r = REG.get(l["lei"]) or {}
    n = r.get("lender") or l["lender"]
    n = n if n.upper() != n else n.title().replace("Llc", "LLC").replace(" Na", " NA")
    return n.replace("Crosscountry", "CrossCountry").replace("Amerisave", "AmeriSave").replace("Loandepot", "loanDepot").replace("Pennymac", "PennyMac").replace("Newrez", "NewRez")


def main():
    check = "--check" in sys.argv
    L = sorted([json.load(open(f, encoding="utf-8")) for f in glob.glob(os.path.join(ROOT, "api", "lender", "*.json"))], key=lambda l: -l["decisioned_applications"])
    fp = [l for l in L if l.get("denial_reason_shares_pct")]
    S = json.load(open(os.path.join(ROOT, "api", "denial-reasons-top100.json"), encoding="utf-8"))
    med = {k: v["median_share_pct"] for k, v in S["by_reason"].items()}
    nat = json.load(open(os.path.join(ROOT, "api", "index.json"), encoding="utf-8"))["national"]
    top20 = fp[:20]

    def sh(l, k):
        return l["denial_reason_shares_pct"].get(k, 0.0)

    def top3(l):
        return sorted(l["denial_reason_shares_pct"].items(), key=lambda kv: -kv[1])[:3]

    def find(s):
        return next(l for l in fp if s.lower() in l["lender"].lower())

    rocket, carrington, amerisave, better, lennar, dhi = (find(s) for s in ("rocket", "carrington", "amerisave", "better mortgage", "lennar", "dhi"))
    low = [l for l in top20 if l["denial_rate_pct"] < 10]
    low_names = ", ".join(name(l).split(" ")[0] for l in low[:3])
    low_dti_med = sorted(sh(l, "dti") for l in low)[len(low) // 2]
    low_ch_med = sorted(sh(l, "credit_history") for l in low)[len(low) // 2]
    link = lambda l: f'<a href="{html.escape(l["page"])}" style="color:#C8A84B;text-decoration:none">{html.escape(name(l))}</a>'

    rows = ""
    for l in top20:
        inc = sh(l, "incomplete")
        rc = ' style="color:#e94560"' if inc >= 30 else ' style="color:rgba(255,255,255,.75)"'
        reasons = " &middot; ".join(f"{LABEL[k]} <span class=\"mono\">{v}%</span>" for k, v in top3(l))
        rows += f'<tr><td style="font-weight:700">{link(l)}</td><td class="mono"{rc}>{l["denial_rate_pct"]}%</td><td style="font-size:12.5px;color:rgba(255,255,255,.7)">{reasons}</td></tr>'

    body = f'''<!-- fingerprints:begin -->
<div style="font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:rgba(200,168,75,.8);margin-bottom:8px;">Direct answer &middot; rebuilt from the lender receipts</div>
<p style="font-size:14.5px;color:rgba(255,255,255,.72)"><b style="color:#fff">Two lenders can post the same denial rate for different reasons &mdash; and the federal record shows each lender&rsquo;s stated-reason fingerprint.</b> In 2025, among the 20 largest FHA lenders, the ones with the lowest observed denial rates ({html.escape(low_names)}, under 10%) cited mostly <b>underwriting math</b>: debt-to-income on about {low_dti_med}% of their denials, credit history on about {low_ch_med}%. The lenders with the highest rates cited <b>incomplete applications</b> far more often: <span class="mono" style="color:#e94560">{sh(carrington, "incomplete")}%</span> of {name(carrington)}&rsquo;s denials, <span class="mono" style="color:#e94560">{sh(amerisave, "incomplete")}%</span> of {name(amerisave)}&rsquo;s, <span class="mono" style="color:#e94560">{sh(better, "incomplete")}%</span> of {name(better)}&rsquo;s, against a median of {med["incomplete"]}% across the 100 largest. Part of the denial-rate spread records what happened to the file, not a judgement of the applicant. Source: {nat["apps"]:,} decisioned FHA applications, CFPB HMDA 2025.</p>
</div>
<h2>The fingerprint table</h2>
<p style="font-size:12.5px;color:rgba(255,255,255,.4)">The 20 largest FHA lenders by 2025 decisioned volume. <b style="color:rgba(255,255,255,.6)">Basis:</b> each share is the percentage of the lender&rsquo;s denials whose stated reasons (up to four) include that reason &mdash; not a partition, so a lender&rsquo;s shares need not sum to 100. Red rate = incomplete cited on &ge;30% of denials. Every lender name links to the page that carries its receipt.</p>
<table><tr><th>Lender</th><th>Denial rate</th><th>Most-cited reasons (share of denials)</th></tr>{rows}</table>
<p style="font-size:12px;color:rgba(255,255,255,.4)">All {len(fp)} lenders with fingerprints, machine-readable: <a href="/api/denial-reasons-top100.json" style="color:#C8A84B">api/denial-reasons-top100.json</a> &middot; medians across lenders: DTI {med["dti"]}%, credit history {med["credit_history"]}%, collateral {med["collateral"]}%, insufficient cash {med["insufficient_cash"]}%, unverifiable information {med["unverifiable_info"]}%, employment {med["employment"]}%, incomplete {med["incomplete"]}%, other {med["other"]}%. Receipt for the medians: <span class="mono">&#x27E6;FRC:denial-reason-shares-top100-2025:dti-{med["dti"]}%:17654e94&#x27E7;</span>.</p>
<h2>Three patterns in the record</h2>
<p><b style="color:#fff">&#9312; Where rates are low, denials look like underwriting.</b> Among the low-rate lenders in the table, debt-to-income and credit history lead the stated reasons. Where rates are highest, the leading reason is often that the file was closed incomplete. A denial code records the outcome, not the cause: an incomplete file may reflect applicant abandonment, documentation timelines or channel design.</p>
<p><b style="color:#fff">&#9313; {name(rocket)}&rsquo;s leading reason is the property.</b> Collateral appears on {sh(rocket, "collateral")}% of its denials, ahead of incomplete ({sh(rocket, "incomplete")}%) and debt-to-income ({sh(rocket, "dti")}%).</p>
<p><b style="color:#fff">&#9314; Builder-affiliated lenders cite the math.</b> Debt-to-income appears on {sh(lennar, "dti")}% of {name(lennar)}&rsquo;s denials and {sh(dhi, "dti")}% of {name(dhi)}&rsquo;s, while collateral is near zero ({sh(lennar, "collateral")}% and {sh(dhi, "collateral")}%) &mdash; consistent with new construction clearing appraisal.</p>
<h2>What this is not</h2>
<p>Reason codes are filed by lenders under federal reporting rules; shares describe reporting patterns, not intent, negligence or service quality, and they partly reflect applicant, product and channel mix. A high incomplete share is an observation about funnel outcomes, not an accusation. Nothing here ranks lenders by quality or recommends one. Context: <a href="/fha-denial-rates-top-100.html" style="color:#C8A84B">the top-100 table</a> &middot; <a href="/denial-code-ecoa-18.html" style="color:#C8A84B">what a DTI denial means</a> &middot; <a href="/corrections.html#2026-11-07-hf-fingerprints-basis" style="color:#C8A84B">basis change, 2026-11-07</a>.</p>
<div class="legal">Source: CFPB HMDA 2025 public loan-level file, FHA forward loans ({nat["apps"]:,} decisioned applications; reverse mortgages excluded); denial reasons 1&ndash;4 as filed; shares = denials citing the reason / denials, for the 100 largest lenders with at least 50 stated-reason denials. Historical observations &mdash; not financial, legal or mortgage advice, not ratings, not predictions about any application. CC BY 4.0.</div>
<!-- fingerprints:end -->'''

    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": f"Why does {name(rocket)} deny FHA loans?", "acceptedAnswer": {"@type": "Answer", "text": f"In 2025 the most-cited stated reason on {name(rocket)}'s denied FHA applications was collateral, on {sh(rocket, 'collateral')}% of denials, followed by incomplete application ({sh(rocket, 'incomplete')}%) and debt-to-income ({sh(rocket, 'dti')}%), per FinanceRateCalc's tabulation of CFPB HMDA 2025 denial-reason fields; a denial may cite up to four reasons, so shares need not sum to 100."}},
        {"@type": "Question", "name": "Do high FHA denial rates mean strict underwriting?", "acceptedAnswer": {"@type": "Answer", "text": f"Not necessarily. In the 2025 record, large FHA lenders with the lowest observed denial rates cited debt-to-income and credit history most often, while several of the highest-rate lenders cited incomplete application on most of their denials ({sh(carrington, 'incomplete')}% at {name(carrington)}, {sh(amerisave, 'incomplete')}% at {name(amerisave)}), against a median of {med['incomplete']}% across the 100 largest lenders. Part of the spread records what happened to the file rather than a judgement of the applicant. Shares partly reflect applicant, product and channel mix."}},
        {"@type": "Question", "name": "Why do builder-affiliated lenders deny FHA loans?", "acceptedAnswer": {"@type": "Answer", "text": f"Mostly on debt-to-income: it appears on {sh(lennar, 'dti')}% of {name(lennar)}'s 2025 FHA denials and {sh(dhi, 'dti')}% of {name(dhi)}'s, while collateral is near zero, consistent with new-construction properties clearing appraisal. Historical observation, not a rating of any lender."}}]}

    s = open(PAGE, encoding="utf-8").read()
    if "<!-- fingerprints:begin -->" in s:
        new = re.sub(r"<!-- fingerprints:begin -->.*?<!-- fingerprints:end -->", lambda m: body, s, flags=re.S)
    else:
        a = s.index('<div style="font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:rgba(200,168,75,.8);margin-bottom:8px;">Direct answer')
        b = s.index("</div>", s.index('<div class="legal">')) + len("</div>")
        new = s[:a] + body + s[b:]
    new = re.sub(r'<script type="application/ld\+json">\{"@context": "https://schema.org", "@type": "FAQPage".*?</script>',
                 lambda m: '<script type="application/ld+json">' + json.dumps(faq, ensure_ascii=False) + "</script>", new, count=1, flags=re.S)
    new = re.sub(r'<meta name="description" content="[^"]*">',
                 lambda m: f'<meta name="description" content="Which reasons each of the 20 largest FHA lenders stated on its 2025 denials, from the CFPB HMDA record: share of denials citing DTI, credit history, collateral, incomplete application and more. Median DTI share {med["dti"]}%; incomplete up to {sh(carrington, "incomplete")}% at one lender. Basis stated; every figure receipted.">', new, count=1)
    if check:
        print("fingerprints page:", "current" if new == s else "STALE"); sys.exit(0 if new == s else 1)
    open(PAGE, "w", encoding="utf-8").write(new)
    print(f"wrote fha-denial-reasons-by-lender.html: {len(top20)} rows, basis share-of-denials-citing")


if __name__ == "__main__":
    main()
