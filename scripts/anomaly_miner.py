#!/usr/bin/env python3
"""FRC Anomaly Miner — ML as editor, not writer.
Scans the real data space for statistical outliers = headline candidates.
Every output is a verifiable fact from _data/. Run: python3 scripts/anomaly_miner.py"""
import json, numpy as np

stories = []
def add(score, headline, detail):
    stories.append((round(float(score),2), headline, detail))

# ── KAYNAK 1: Karar yüzeyleri — hücre uzayındaki tuhaflıklar
_ds = json.load(open('_data/decision_surfaces_2025.json'))
surf = _ds['surfaces']; DTI_AXIS = _ds['dti_axis']
def val(x): return x['denial'] if isinstance(x, dict) else x
CLTV_BANDS = _ds['cltv_bands']
for L, mat in surf.items():
    for bi, row in enumerate(mat):
        band = CLTV_BANDS[bi]
        pairs = [(d, v) for d, v in zip(DTI_AXIS, row) if v is not None]
        if len(pairs) < 6: continue
        xs = [p[0] for p in pairs]; vs = [p[1] for p in pairs]
        slope = np.polyfit(xs, vs, 1)[0]
        if slope < -0.5:
            add(abs(slope)*10, f"{L} @ CLTV {band}: denial FALLS as DTI rises ({vs[0]:.0f}%\u2192{vs[-1]:.0f}%)",
                f"slope {slope:.2f}pp/DTI \u2014 inverse of textbook underwriting")
        for k in range(1, len(pairs)):
            if pairs[k][0] - pairs[k-1][0] == 1:
                jump = pairs[k][1] - pairs[k-1][1]
                if jump > 25:
                    add(jump, f"{L} @ CLTV {band}: +{jump:.0f}pp cliff between DTI {pairs[k-1][0]} and {pairs[k][0]} ({pairs[k-1][1]:.0f}%\u2192{pairs[k][1]:.0f}%)",
                        "single-step denial cliff")

# ── KAYNAK 2: Lender panel tarihi — davranış kırılmaları
lsi = json.load(open('_data/lender_stress_index.json'))
hist = {L: d['denial_history'] for L, d in lsi.items() if 'denial_history' in d}
for L, h in hist.items():
    yrs = sorted(h.keys())
    vs = [h[y] for y in yrs]
    # a) tek yılda en sert U-dönüşü
    for i in range(1, len(vs)):
        d1 = vs[i]-vs[i-1]
        if abs(d1) > 15:
            add(abs(d1), f"{L}: {'+' if d1>0 else ''}{d1:.1f}pp in a single year ({yrs[i-1]}→{yrs[i]}: {vs[i-1]:.0f}%→{vs[i]:.0f}%)",
                "sharpest single-year behavioral break")
    # b) 8 yıllık toplam dönüşüm
    tot = vs[-1]-vs[0]
    if abs(tot) > 25:
        add(abs(tot)*0.9, f"{L} transformed: {vs[0]:.0f}% (2018) → {vs[-1]:.0f}% (2025), {'+' if tot>0 else ''}{tot:.0f}pp in 8 years",
            "identity-level shift")
# c) lender çifti: aynı yıl zıt yönlere koşanlar
Ls = list(hist.keys())
for i in range(len(Ls)):
    for j in range(i+1, len(Ls)):
        a, b = hist[Ls[i]], hist[Ls[j]]
        for y1, y2 in zip(sorted(a)[:-1], sorted(a)[1:]):
            if y2 in b and y1 in b:
                da, db = a[y2]-a[y1], b[y2]-b[y1]
                if da*db < 0 and abs(da)>8 and abs(db)>8:
                    add(abs(da-db)*0.8, f"{y1}→{y2}: same market, opposite doors — {Ls[i]} {'+' if da>0 else ''}{da:.0f}pp while {Ls[j]} {'+' if db>0 else ''}{db:.0f}pp",
                        "divergence pair — kills the 'market conditions' excuse")

# ── KAYNAK 3: Eyalet HPI — 51 eyaletin tuhaflıkları
hpi = json.load(open('_data/hpi_state_annual.json'))
yy = hpi['yoy_pct']
latest = '2026'
vals = {s: v[latest] for s, v in yy.items() if latest in v}
mu, sd = np.mean(list(vals.values())), np.std(list(vals.values()))
for s, v in vals.items():
    z = (v-mu)/sd
    if abs(z) > 2:
        add(abs(z)*6, f"{s} {latest}: {'+' if v>=0 else ''}{v:.1f}%/yr — {abs(z):.1f}σ from the 51-state mean ({mu:+.1f}%)",
            "state price outlier")
# 50 yılın en sert eyalet-yılı düşüşleri hala hangi eyalette taze?
def _clean(v):
    return {y: x for y, x in v.items() if int(y) >= 1995 and abs(x) <= 35}
yy = {s: _clean(v) for s, v in yy.items()}
neg = {s: min(v.values()) for s, v in yy.items() if v}
worst = sorted(neg.items(), key=lambda kv: kv[1])[:3]
for s, v in worst:
    yr = [y for y, x in yy[s].items() if x == v][0]
    add(abs(v)*0.7, f"{s}'s worst year on record: {v:.1f}% ({yr}) — 52 years of FHFA data",
        "historical extreme")

stories.sort(key=lambda x: -x[0])
print(f"{'='*70}\nFRC ANOMALY MINER — {len(stories)} bulgu, en güçlü 12:\n{'='*70}")
for sc, h, d in stories[:12]:
    print(f"[{sc:6.1f}] {h}\n         ↳ {d}")
json.dump([{"score":s,"headline":h,"detail":d} for s,h,d in stories[:40]],
          open('_data/anomaly_stories.json','w'), indent=1)
print(f"\n✓ İlk 40 hikâye _data/anomaly_stories.json'a yazıldı")
