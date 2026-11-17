#!/usr/bin/env python3
"""Bring the 2026-05 template layer under the site's present rules (run once, 2026-11-16; kept as the record).

  market/<zip>.html      estimated market figures with no dated source, lender lists ordered by rate, routing links.
                         Replaced by a short notice that points to the audited metro page (or the metro index).
  identity/*.html        profession salaries with no source. Replaced by a notice pointing to the salary example
                         for the same city.
  salary/*.html          rebuilt as one worked example: the assumptions are named as assumptions, the arithmetic is
                         recomputed here, the state's FHA denial rate enters with its receipt, credit-score rules with
                         their sources. Verdict labels, neighbourhood advice, unsourced market statistics, routing links,
                         the newsletter box, the leftover commission disclosure and the risk-tier box are removed.

    python3 scripts/retire_old_layer.py            # rewrite
    python3 scripts/retire_old_layer.py --check    # fail if any page of the three folders still carries a removed element
"""
import glob
import html as H
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
TODAY = "2026-11-16"
STATE = {"AZ": "Arizona", "CA": "California", "CO": "Colorado", "FL": "Florida", "GA": "Georgia", "IL": "Illinois", "MA": "Massachusetts", "MN": "Minnesota",
         "NC": "North Carolina", "NV": "Nevada", "NY": "New York", "OR": "Oregon", "PA": "Pennsylvania", "TN": "Tennessee", "TX": "Texas", "WA": "Washington",
         "DC": "the District of Columbia", "OH": "Ohio", "MI": "Michigan", "MO": "Missouri", "UT": "Utah", "VA": "Virginia", "MD": "Maryland", "IN": "Indiana"}
BANNED = ["World First", "Real Bank Math", "may earn a commission", "Which lenders approve most", "Apply to more than one", "Get the Dispatch",
          "Orange Tier", "NOT AFFORDABLE", "Best neighborhoods", "Local Market Intelligence", "Market data is estimated", "HOT</", "Seller's market"]
SAL = re.compile(r"can-i-afford-house-on-(\d+)k-salary-in-(.+)-([a-z]{2})\.html$")
IDN = re.compile(r"can-(.+)-afford-house-in-(.+)-([a-z]{2})\.html$")


def money(x):
    return f"${x:,.0f}"


def stub(title, lead, target, target_label, why, day=None):
    day = day or TODAY
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="robots" content="noindex,follow">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{H.escape(title)} | FinanceRateCalc</title>
<link rel="canonical" href="https://financeratecalc.com{target}">
<link rel="icon" href="/favicon.ico">
<style>body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;max-width:640px;margin:12vh auto;padding:0 20px;line-height:1.6;color:#1b1f24;background:#fbfaf7}}a{{color:#0b4f8a}}.s{{font-size:14px;color:#555}}</style>
</head>
<body>
<p class="s"><a href="/">FinanceRateCalc</a></p>
<h1 style="font-size:24px;line-height:1.25">{H.escape(title)}</h1>
<p>{lead}</p>
<p><a href="{target}"><b>{H.escape(target_label)}</b></a></p>
<p class="s">{why} Retired {day}; recorded in the <a href="/corrections.html">corrections log</a>.</p>
</body>
</html>
"""


def retire_market():
    n = 0
    for f in sorted(glob.glob("market/*.html")):
        s = open(f, encoding="utf-8").read()
        if "Retired " + TODAY in s:
            n += 1; continue
        m = re.search(r'href="(/metro/[^"]+\.html)"', s)
        t = re.search(r"<title>([^<|]+)", s)
        name = re.sub(r"\s+", " ", H.unescape(t.group(1))).strip(" —-") if t else "Housing market page"
        if f.endswith("index.html") or not m or not os.path.exists(m.group(1)[1:]):
            target, label = "/metro-gaps.html", "FHA denial rates by metro, each with a receipt"
        else:
            mt = re.search(r"<title>([^<|]+)", open(m.group(1)[1:], encoding="utf-8").read())
            target, label = m.group(1), re.sub(r"\s+", " ", H.unescape(mt.group(1))).strip() if mt else "The metro's FHA record"
        open(f, "w", encoding="utf-8").write(stub(name + ": page retired",
            "This page showed a market score, a median price and days on market that were estimates with no dated source, next to figures from the federal mortgage record. The estimates have been withdrawn.",
            target, label, "What remains is the part that can be checked: the metro's FHA figures from the 2025 HMDA record, each with a receipt."))
        n += 1
    return n


def retire_identity(cities):
    n = 0
    for f in sorted(glob.glob("identity/*.html")):
        s = open(f, encoding="utf-8").read()
        if "Retired " + TODAY in s:
            n += 1; continue
        m = IDN.search(f)
        t = re.search(r"<title>([^<|]+)", s)
        name = re.sub(r"\s+", " ", H.unescape(t.group(1))).strip(" —-") if t else "Profession page"
        target, label = "/salary/index.html", "Worked examples by income and city"
        if m and (m.group(2), m.group(3)) in cities:
            sal = re.search(r"\$(\d{2,3}),000/yr", s)
            want = int(sal.group(1)) if sal else 80
            k = min(cities[(m.group(2), m.group(3))], key=lambda v: abs(v - want))
            target = f"/salary/can-i-afford-house-on-{k}k-salary-in-{m.group(2)}-{m.group(3)}.html"
            label = f"Worked example: a ${k},000 income in {m.group(2).replace('-', ' ').title()}"
        open(f, "w", encoding="utf-8").write(stub(name + ": page retired",
            "This page built its answer on a salary figure for a profession that carried no source, and on program advice written for a job title. Both have been withdrawn.",
            target, label, "The arithmetic does not depend on the job; the worked example for the same city shows it with every assumption named."))
        n += 1
    return n


# Second pass, 2026-11-18: every other family of May 2026 template pages already marked noindex.
FAMILIES = ["dream-home-city", "dream-home-mountain", "dream-home-suburban", "dream-home-beachfront", "how-much-house", "can-i-get", "salary-to-buy", "salary-to-afford",
            "monthly-payment-on", "down-payment-for", "down-payment-on", "income-needed-for", "should-i-refinance", "mortgage-zip-", "neighborhood-", "can-i-afford", "blog-"]
SALARY_LIKE = ("how-much-house", "can-i-afford", "salary-to-buy", "salary-to-afford", "monthly-payment-on", "down-payment-for", "down-payment-on", "income-needed-for")
DAY2 = "2026-11-18"
USPS = set("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split())


def family_pages():
    out = []
    for f in sorted(glob.glob("*.html")):
        if "calculator" in f or f in ("can-i-get-a-loan.html", "can-i-get-approved-for-mortgage.html", "mortgage-evidence-for-ai.html"):
            continue   # interactive tools and one-off pages are reviewed separately
        fam = next((p for p in FAMILIES if f.startswith(p)), None)
        if not fam and re.match(r"sell-\d", f):
            fam = "sell-N-buy"
        st = re.search(r"-([a-z]{2})\.html$", f)
        if not fam and f.startswith("mortgage-") and st and st.group(1).upper() in USPS:
            fam = "mortgage-city"
        if fam:
            out.append((f, fam))
    out += [(f, "city/") for f in sorted(glob.glob("city/*.html"))] + [(f, "employer/") for f in sorted(glob.glob("employer/*.html"))]
    return out


def retire_families():
    n = kept = 0
    for f, fam in family_pages():
        s = open(f, encoding="utf-8", errors="ignore").read()
        if re.search(r"Retired \d{4}-\d{2}-\d{2};", s):
            n += 1; continue
        t = re.search(r"<title>([^<|]+)", s)
        name = re.sub(r"\s+", " ", H.unescape(t.group(1))).strip(" —-") if t else "Page"
        name = re.sub(r"^[^\w$(]+", "", name)
        fn = re.search(r"FRC-FOOTNOTE:([a-z0-9-]+?)-*-->", s)
        cid = fn.group(1) if fn else ""
        mslug = re.match(r"metro-gap-(.+)-2025$", cid)
        if fam in SALARY_LIKE:
            target, label = "/salary/index.html", "Worked examples by income and city, every assumption named"
        elif mslug and os.path.exists(f"metro/{mslug.group(1)}.html"):
            target, label = f"/metro/{mslug.group(1)}.html", "This metro's FHA record, with receipts"
        elif cid.startswith("state-"):
            target, label = "/fha-denial-rates-by-state.html", "FHA denial rates by state, each with a receipt"
        else:
            target, label = "/", "What this site publishes, and how to check it"
        open(f, "w", encoding="utf-8").write(stub(name + ": page retired",
            "This page was written from a template in May 2026. The prices, payments, scores and local details on it were examples or estimates with no dated source, shown beside figures from the federal record. It has been withdrawn.",
            target, label, "This site now prints a number only if it carries a receipt or is named as an assumption.", DAY2))
        n += 1
    return n, kept


def pmt(loan, rate_pct, years=30):
    r = rate_pct / 100 / 12
    return loan * r / (1 - (1 + r) ** (-years * 12))


def rebuild_salary(cities):
    nat = json.load(open("claims/national-fha-denial-rate-2025.json", encoding="utf-8"))
    n, diffs = 0, 0
    for f in sorted(glob.glob("salary/*.html")):
        m = SAL.search(f)
        if not m:
            continue
        s = open(f, encoding="utf-8").read()
        k, slug, st = int(m.group(1)), m.group(2), m.group(3).upper()
        if 'data-frc-rebuilt="' in s:   # already rebuilt: only make sure the head carries no old description or keywords
            t = re.sub(r'<meta\s+content="[^"]*"\s+name="(?:description|keywords)"\s*/?>\n?', "", s)
            t = re.sub(r'<meta\s+(?:property="og:description"|name="twitter:description")\s+content="[^"]*"\s*/?>\n?|<meta\s+content="[^"]*"\s+(?:property="og:description"|name="twitter:description")\s*/?>\n?', "", t)
            if t != s:
                open(f, "w", encoding="utf-8").write(t)
            n += 1; continue
        city = H.unescape(re.search(r"<h1>.*?<em>([^<]+)</em>", s, re.S).group(1)).strip()
        rows = dict((H.unescape(a).strip(), H.unescape(b).strip()) for a, b in re.findall(r'<span class="br-label">([^<]+)</span><span class="br-val[^"]*"[^>]*>([^<]+)</span>', s))
        num = lambda v: float(re.sub(r"[^\d.]", "", v))
        price = num(rows["Median Home Price"])
        down_pct = next(float(re.match(r"(\d+(?:\.\d+)?)%", a).group(1)) for a in rows if "Down Payment" in a)
        rate = next(float(re.search(r"\((\d+(?:\.\d+)?)%\)", a).group(1)) for a in rows if a.startswith("Principal"))
        tax_pct = next(float(re.search(r"\((\d+(?:\.\d+)?)%/yr\)", a).group(1)) for a in rows if a.startswith("Property Tax"))
        ins = num(rows["Homeowners Insurance"])
        old_piti = num(rows["Total PITI"])
        income = k * 1000
        loan = price * (1 - down_pct / 100)
        pi, tax = pmt(loan, rate), price * tax_pct / 100 / 12
        piti = pi + tax + ins
        share = 100 * piti / (income / 12)
        if abs(piti - old_piti) > 2:
            diffs += 1
        kf = pmt(1, rate) * (1 - down_pct / 100) + tax_pct / 100 / 12
        p28, p36 = (0.28 * income / 12 - ins) / kf, (0.36 * income / 12 - ins) / kf
        sd = json.load(open(f"claims/state-{st.lower()}-2025.json", encoding="utf-8"))
        stname = STATE[st]
        head = s[:s.index("</head>")]
        head = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="Worked example: a {money(income)} gross income and a {money(price)} home price in {H.escape(city)}, {st}. Every assumption is named, the arithmetic is shown, and the state FHA denial rate carries a receipt.">', head)
        head = re.sub(r'<meta name="keywords"[^>]*>\n?', "", head)
        head = re.sub(r'<meta\s+content="[^"]*"\s+name="(?:description|keywords)"\s*/?>\n?', "", head)
        head = re.sub(r'<meta\s+(?:property="og:description"|name="twitter:description")\s+content="[^"]*"\s*/?>\n?|<meta\s+content="[^"]*"\s+(?:property="og:description"|name="twitter:description")\s*/?>\n?', "", head)
        head = head.replace('"datePublished":"2026-05-25"', f'"datePublished":"2026-05-25","dateModified":"{TODAY}"').replace('"jobTitle":"Senior Banking Consultant"', '"jobTitle":"Bank credit, 23 years"')
        header = s[s.index("<header"):s.index('<div class="wrap">')]
        foot = s[s.index("<!--FRC-FOOTNOTE"):s.index("<!--/FRC-FOOTNOTE-->") + len("<!--/FRC-FOOTNOTE-->")] if "<!--FRC-FOOTNOTE" in s else ""
        chip = 'style="display:inline-block;padding:6px 12px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:6px;font-size:12px;color:rgba(255,255,255,0.6);text-decoration:none;margin:3px;"'
        others = "".join(f'<a href="/salary/can-i-afford-house-on-{v}k-salary-in-{slug}-{st.lower()}.html" {chip}>${v}K</a>' for v in sorted(cities[(slug, st.lower())]) if v != k)
        a = 'style="color:inherit;text-decoration:underline"'
        row = lambda l, v, g="": f'    <div class="br-row"><span class="br-label">{l}</span><span class="br-val{g}">{v}</span></div>\n'
        body = f"""<div class="wrap" data-frc-rebuilt="{TODAY}">
  <div style="font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(255,255,255,0.3);margin-bottom:10px;">Worked example &middot; assumptions named &middot; arithmetic rechecked {TODAY}</div>
  <h1>Can I Afford a House in <em>{H.escape(city)}</em><br>on a ${k}K Salary?</h1>
  <div class="byline">By Ziya Y. &middot; 23 years in bank credit</div>

  <p>This page is one worked example. It takes a gross income of {money(income)} a year and a home price of {money(price)}, applies the assumptions listed below, and shows the arithmetic. It is not a market report and it says nothing about any one buyer or any one application. Change an assumption and the result changes.</p>

  <div class="data-grid">
    <div class="data-card"><div class="data-label">Gross income (example)</div><div class="data-val green">{money(income)}/yr</div></div>
    <div class="data-card"><div class="data-label">Home price (assumed)</div><div class="data-val gold">{money(price)}</div></div>
    <div class="data-card"><div class="data-label">Monthly payment</div><div class="data-val gold">{money(piti)}/mo</div></div>
    <div class="data-card"><div class="data-label">Share of gross income</div><div class="data-val gold">{share:.1f}%</div></div>
  </div>

  <div class="breakdown">
    <h2 style="margin-top:0;">The arithmetic</h2>
{row("Home price (assumed)", money(price))}{row(f"Down payment ({down_pct:g}%, assumed)", money(price - loan))}{row("Loan amount", money(loan))}{row(f"Principal and interest (30-year fixed at {rate:g}%, assumed)", money(pi) + "/mo")}{row(f"Property tax ({tax_pct:g}% of price a year, assumed)", money(tax) + "/mo")}{row("Homeowners insurance (assumed)", money(ins) + "/mo")}{row("Monthly payment", money(piti) + "/mo", " gold")}{row("Gross income per month", money(income / 12) + "/mo")}{row("Payment as a share of gross income", f"{share:.1f}%")}  </div>

  <h2>What is assumed</h2>
  <p>The home price was chosen as an example for {H.escape(city)} when this page was first written in May 2026. It is not a current median and this page does not tie it to a dated dataset. The {rate:g}% rate is an assumption, not a quote. Property tax and insurance are round assumptions. The example leaves out mortgage insurance, association dues, closing costs and every other debt the household carries, any of which raises the real figure.</p>

  <h2>The 28 / 36 convention</h2>
  <p>A common rule of thumb puts housing costs near 28% of gross income and all debt payments near 36%. It is a convention; loan programs and underwriting systems apply their own limits and look at far more than this ratio. Under the assumptions above, a payment equal to 28% of this income corresponds to a home price of about {money(max(p28, 0))}, and 36% to about {money(max(p36, 0))}.</p>

  <h2>What the federal record says about {H.escape(stname)}</h2>
  <p>Arithmetic shows what a payment would be. It does not show how applications ended. In 2025, {sd["display_value"]} {sd["receipt"]} of FHA applications that reached a decision in {H.escape(stname)} were denied ({sd["claim"]["n"]:,} decisions), against {nat["display_value"]} {nat["receipt"]} nationally. Both figures cover every loan purpose, refinances included, and describe applications already decided; neither is a forecast for anyone. Source: FinanceRateCalc analysis of the public CFPB HMDA 2025 record; historical aggregate only. <a {a} href="{sd["verify_url"]}">Check the state figure</a> &middot; <a {a} href="/denominator-diagnosis.html">which denominator a quoted rate uses</a></p>

  <h2>Credit score rules, with their sources</h2>
  <p>FHA: a minimum decision credit score of 580 for maximum financing, and 500 to 579 with at least 10% down (HUD Mortgagee Letter 2010-29). Fannie Mae: no fixed minimum score for loans run through its automated underwriting system for casefiles created on or after 16 November 2025; the earlier floor was 620 (<a {a} href="/rules/fannie-du-minimum-credit-score-2025-11-16.json">rule file with the issuer's documents</a>). Individual lenders may set higher requirements of their own.</p>

  <div class="nearby">
    <h3>Same city, different income</h3>
    <div>{others}</div>
    <h3>Related</h3>
    <div><a href="/salary/index.html" {chip}>All worked examples</a><a href="/door-report.html" {chip}>FHA outcomes by state, loan size and purpose</a><a href="/corrections.html" {chip}>Corrections log</a><a href="/methodology.html" {chip}>Method</a></div>
  </div>

  <p class="disc">Not financial advice and not a prediction. Rebuilt {TODAY}: market statistics without a dated source, neighbourhood suggestions and affordability verdicts that this page carried were removed; see the <a {a} href="/corrections.html">corrections log</a>.</p>
</div>
"""
        open(f, "w", encoding="utf-8").write(head + "</head>\n<body>\n" + header + body + foot + "\n</body>\n</html>\n")
        n += 1
    return n, diffs


def main():
    cities = {}
    for f in glob.glob("salary/*.html"):
        m = SAL.search(f)
        if m:
            cities.setdefault((m.group(2), m.group(3)), []).append(int(m.group(1)))
    if "--check" in sys.argv:
        bad = []
        for f in glob.glob("market/*.html") + glob.glob("identity/*.html") + glob.glob("salary/*.html"):
            if f == "salary/index.html":
                continue
            s = open(f, encoding="utf-8").read()
            hit = [b for b in BANNED if b in s]
            if hit or not (re.search(r"Retired \d{4}-\d{2}-\d{2};", s) or 'data-frc-rebuilt="' in s):
                bad.append((f, hit))
        for f, fam in family_pages():
            s = open(f, encoding="utf-8", errors="ignore").read()
            if not re.search(r"Retired \d{4}-\d{2}-\d{2};", s):
                bad.append((f, ["template page not retired"]))
        print("old layer:", "clean" if not bad else f"{len(bad)} pages not converted, e.g. {bad[:3]}")
        sys.exit(1 if bad else 0)
    print("market notices:", retire_market())
    print("template families retired (and hub pages left for review):", retire_families())
    print("identity notices:", retire_identity(cities))
    print("salary examples rebuilt (pages whose old payment differed from the recomputed one by more than $2):", rebuild_salary(cities))


if __name__ == "__main__":
    main()
