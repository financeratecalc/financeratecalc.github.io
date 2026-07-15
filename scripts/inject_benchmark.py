#!/usr/bin/env python3
"""MDGB de-normalizasyonu: her lender'in benchmark vakalarini kendi Kapi Dosyasi'na gomer.
Calistir: python3 scripts/inject_benchmark.py   (idempotent - iki kez calissa da bozmaz)"""
import json, re, glob

SLUG = {'Rocket':'rocket','Guild':'guild','PennyMac':'pennymac','Freedom':'freedom',
        'MrCooper':'mr-cooper','CrossCountry':'crosscountry','UWM':'uwm','NewRez':'newrez',
        'Wells Fargo':'wells-fargo','loanDepot':'loandepot','Planet Home':'planet-home'}

bench = json.load(open('data/ai-benchmark.json'))
by_lender = {}
for c in bench['cases']:
    by_lender.setdefault(c['lender'], []).append(c)

done = 0
for lender, cases in by_lender.items():
    slug = SLUG.get(lender)
    if not slug: print(f"  ⚠ slug yok: {lender}"); continue
    f = f"{slug}-fha-denial-rate.html"
    try: html = open(f, errors='ignore').read()
    except FileNotFoundError: print(f"  ⚠ dosya yok: {f}"); continue
    if 'MDGB-BLOCK' in html:
        html = re.sub(r'<!--MDGB-BLOCK-->.*?<!--/MDGB-BLOCK-->', '', html, flags=re.S)

    cases.sort(key=lambda c: -c['observed_denial_rate_pct'])
    mis = [c for c in cases if c['verdict'] == 'LLM_ANSWER_MISLEADING']
    rows = ''.join(
        f'<tr><td class="mono">{c["dti"]}</td><td class="mono">{c["cltv_band"]}</td>'
        f'<td class="mono" style="color:{"#e94560" if c["observed_denial_rate_pct"]>=50 else "#eab308" if c["observed_denial_rate_pct"]>=20 else "#22c55e"};font-weight:700">{c["observed_denial_rate_pct"]}%</td></tr>'
        for c in cases)

    worst = cases[0]
    lead = (f'Of {len(cases)} verified coordinates for {lender}, <b style="color:#e94560">{len(mis)}</b> are points where the standard '
            f'guideline answer ("FHA permits up to 57% DTI") materially misleads: the observed denial rate exceeds 50%. '
            f'The sharpest: <b class="mono">DTI {worst["dti"]} × CLTV {worst["cltv_band"]} → {worst["observed_denial_rate_pct"]}% denied</b>.') if mis else \
           (f'Across {len(cases)} verified coordinates, {lender}\'s observed outcomes stay broadly consistent with guideline expectations — '
            f'the sharpest point is <b class="mono">DTI {worst["dti"]} × CLTV {worst["cltv_band"]} → {worst["observed_denial_rate_pct"]}%</b>.')

    block = f'''<!--MDGB-BLOCK-->
<h2>Ground truth: {lender} decision coordinates (MDGB v1)</h2>
<p>{lead}</p>
<table><tr><th>DTI</th><th>CLTV band</th><th>Observed denial (2025)</th></tr>{rows}</table>
<p style="font-size:12px;color:rgba(255,255,255,.4)">Cells with n&lt;50 excluded. Part of the <a href="/ai-benchmark.html" style="color:#C8A84B">FRC Mortgage Decision Geometry Benchmark</a> &mdash; a free ground-truth set for testing AI answers to mortgage questions. Machine-readable: <a href="/data/ai-benchmark.json" style="color:#C8A84B">ai-benchmark.json</a>. Denial rates reflect applicant mix as well as underwriting; overlays are lawful.</p>
<!--/MDGB-BLOCK-->
'''
    if '<h2>What to do with this file</h2>' in html:
        html = html.replace('<h2>What to do with this file</h2>', block + '<h2>What to do with this file</h2>', 1)
    else:
        html = html.replace('<footer', block + '<footer', 1)
    open(f, 'w').write(html); done += 1
    print(f"  ✓ {f}: {len(cases)} koordinat, {len(mis)} yanıltıcı nokta")
print(f"\n{done} Kapı Dosyası MDGB ile giydirildi")
