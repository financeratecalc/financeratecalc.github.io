#!/usr/bin/env python3
"""FRC Credit Climate Engine — HONEST ML LAYER
Computes (a) Credit Climate Index: market-wide tightening pressure composite,
(b) per-lender OFI: regression sensitivity of lender denial behavior to that climate.
NOT an individual approval-probability model. n=8 annual observations —
outputs are climate readouts, methodology-bound, hypothesis-grade.
Run: python3 scripts/credit_climate.py  → writes _data/climate_scores.json"""
import json, numpy as np

macro = json.load(open('_data/macro_annual.json'))['series']
lsi   = json.load(open('_data/lender_stress_index.json'))
YRS = [str(y) for y in range(2018, 2026)]

def z(series):
    v = np.array([series.get(y, np.nan) for y in YRS], float)
    m, s = np.nanmean(v), np.nanstd(v)
    return (v - m) / s if s else v*0

# Climate = tightening pressure: high denial, high SLOOS tightening,
# wide spread, weak HPI all push the index UP.
comp = np.nanmean(np.vstack([
    z(macro['fha_denial_avg']['data']),
    z(macro['sloos_net_tightening_mortgage']['data']),
    z(macro['mortgage_treasury_spread']['data']),
    -z(macro['hpi_yoy']['data']),
]), axis=0)
climate = 50 + 20*comp                      # merkez 50, ±1σ = ±20
climate = np.clip(climate, 0, 100)

# Lender OFI: slope of lender denial (z) on climate (z) — macro-sensitivity, 0–100
cz = (comp - np.nanmean(comp)) / np.nanstd(comp)
ofi = {}
for L, d in lsi.items():
    h = d.get('denial_history', {})
    y = np.array([h.get(yy, np.nan) for yy in YRS], float)
    mask = ~np.isnan(y) & ~np.isnan(cz)
    if mask.sum() < 5: continue
    yz = (y[mask]-y[mask].mean())/(y[mask].std() or 1)
    beta = float(np.polyfit(cz[mask], yz, 1)[0])          # standardize edilmiş eğim
    ofi[L] = {"ofi": round(np.clip(50 + 35*beta, 0, 100), 1),
              "beta": round(beta, 3), "n_years": int(mask.sum())}

out = {
  "generated": "2026-07-06",
  "methodology": "Climate = mean z-score composite of [FHA denial avg, SLOOS net tightening, mortgage-Treasury spread, -HPI YoY], scaled 50±20/σ. OFI = standardized OLS slope of lender denial on climate, scaled 50±35/β. Annual n=8; hypothesis-grade market readouts — NOT individual approval probabilities.",
  "climate_index": {y: round(float(c),1) for y,c in zip(YRS, climate) if not np.isnan(c)},
  "current": {"year": "2025", "climate": round(float(climate[-1]),1),
              "label": ("RESTRICTIVE" if climate[-1]>=65 else "TIGHTENING" if climate[-1]>=55
                        else "NEUTRAL" if climate[-1]>=45 else "ACCOMMODATIVE")},
  "lender_ofi": dict(sorted(ofi.items(), key=lambda kv:-kv[1]["ofi"])),
  "disclaimer": "Educational market climate readout. Not financial advice, not an approval predictor."
}
json.dump(out, open('_data/climate_scores.json','w'), indent=1)
print(f"CLIMATE 2018→2025: {[out['climate_index'][y] for y in YRS if y in out['climate_index']]}")
print(f"2025: {out['current']['climate']} — {out['current']['label']}")
print("OFI sıralaması:", {k:v['ofi'] for k,v in list(out['lender_ofi'].items())[:5]}, "...")
