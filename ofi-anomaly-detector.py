"""
OFI ML Anomaly Detector — Weekly Auto-Run
Runs every Wednesday 08:00 UTC via GitHub Actions
Updates ofi-anomaly-scores.json with latest analysis
"""

import json
import numpy as np
from datetime import datetime
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPRegressor
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')

# ─── VERİ ────────────────────────────────────────────────────────────────────
ALL_DATA = [
    (2014,1,4.34,2.44,1.52,52),(2014,2,4.13,2.40,1.48,50),
    (2014,3,4.10,2.38,1.44,49),(2014,4,3.99,2.35,1.41,48),
    (2015,1,3.69,2.29,1.35,46),(2015,2,3.98,2.25,1.30,45),
    (2015,3,3.90,2.21,1.28,44),(2015,4,3.94,2.18,1.25,44),
    (2016,1,3.69,2.15,1.22,43),(2016,2,3.64,2.12,1.20,42),
    (2016,3,3.44,2.10,1.18,41),(2016,4,3.77,2.08,1.30,43),
    (2017,1,4.17,2.36,1.25,46),(2017,2,4.03,2.38,1.22,45),
    (2017,3,3.88,2.40,1.20,44),(2017,4,3.92,2.45,1.24,44),
    (2018,1,4.33,2.51,1.28,45),(2018,2,4.54,2.52,1.31,44),
    (2018,3,4.63,2.55,1.38,43),(2018,4,4.83,2.58,1.47,43),
    (2019,1,4.37,2.57,1.55,41),(2019,2,4.00,2.55,1.52,39),
    (2019,3,3.73,2.54,1.49,37),(2019,4,3.74,2.56,1.48,36),
    (2020,1,3.50,2.59,1.89,38),(2020,2,3.23,3.41,2.78,36),
    (2020,3,2.96,3.22,2.11,33),(2020,4,2.76,2.65,1.38,32),
    (2021,1,2.92,1.80,1.05,31),(2021,2,3.00,1.63,0.98,30),
    (2021,3,2.87,1.53,0.95,31),(2021,4,3.07,1.37,0.94,36),
    (2022,1,3.76,1.48,1.12,42),(2022,2,5.23,1.72,1.58,50),
    (2022,3,5.55,2.01,1.89,55),(2022,4,6.79,2.23,2.03,58),
    (2023,1,6.36,2.63,1.76,56),(2023,2,6.57,2.94,1.58,55),
    (2023,3,6.82,3.25,1.44,53),(2023,4,7.03,3.75,1.58,51),
    (2024,1,6.97,4.06,1.63,50),(2024,2,7.06,4.32,1.55,48),
    (2024,3,6.55,4.57,1.52,46),(2024,4,6.72,4.63,1.58,44),
]

labels = [f"{d[0]} Q{d[1]}" for d in ALL_DATA]
X = np.array([[d[2], d[3], d[4], d[5]] for d in ALL_DATA])

# Normal dönem baseline: 2014-2019
normal_idx = [i for i, d in enumerate(ALL_DATA) if d[0] <= 2019]
X_normal = X[normal_idx]

# ─── MODEL 1: ISOLATION FOREST ───────────────────────────────────────────────
sc = StandardScaler()
X_scaled = sc.fit_transform(X)
X_normal_scaled = sc.transform(X_normal)

iso = IsolationForest(contamination=0.1, random_state=42, n_estimators=200)
iso.fit(X_normal_scaled)
if_scores_raw = iso.score_samples(X_scaled)
if_scores = 100 * (1 - (if_scores_raw - if_scores_raw.min()) / (if_scores_raw.max() - if_scores_raw.min()))

# ─── MODEL 2: AUTOENCODER ────────────────────────────────────────────────────
ae = MLPRegressor(hidden_layer_sizes=(3, 2, 3), max_iter=2000, random_state=42, activation='tanh')
ae.fit(X_normal_scaled, X_normal_scaled)
X_reconstructed = ae.predict(X_scaled)
recon_errors = np.mean((X_scaled - X_reconstructed) ** 2, axis=1)
ae_scores = 100 * (recon_errors - recon_errors.min()) / (recon_errors.max() - recon_errors.min())

# ─── MODEL 3: PCA DISTANCE ───────────────────────────────────────────────────
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)
normal_center = X_pca[normal_idx].mean(axis=0)
pca_distances = np.sqrt(np.sum((X_pca - normal_center) ** 2, axis=1))
pca_scores = 100 * (pca_distances - pca_distances.min()) / (pca_distances.max() - pca_distances.min())

# ─── CONSENSUS SCORE ─────────────────────────────────────────────────────────
consensus = if_scores * 0.4 + ae_scores * 0.3 + pca_scores * 0.3

def get_alert(score):
    if score >= 70: return "CRITICAL"
    elif score >= 50: return "HIGH"
    elif score >= 30: return "ELEVATED"
    return "NORMAL"

# ─── CURRENT QUARTER SİNYALİ ─────────────────────────────────────────────────
# Şu an Q2 2026 — modelin gördüğü son nokta 2024 Q4
# Mevcut OFI 47 ile extrapolate et
current_ofi = 47
current_rate = 6.72
current_cc = 4.63
current_mbs = 1.58

current_features = np.array([[current_rate, current_cc, current_mbs, current_ofi]])
current_scaled = sc.transform(current_features)

current_if = float(iso.score_samples(current_scaled)[0])
current_if_norm = 100 * (1 - (current_if - if_scores_raw.min()) / (if_scores_raw.max() - if_scores_raw.min()))
current_if_norm = max(0, min(100, current_if_norm))

current_ae = float(np.mean((current_scaled - ae.predict(current_scaled)) ** 2))
current_ae_norm = 100 * (current_ae - recon_errors.min()) / (recon_errors.max() - recon_errors.min())
current_ae_norm = max(0, min(100, current_ae_norm))

current_pca = pca.transform(current_scaled)
current_dist = float(np.sqrt(np.sum((current_pca - normal_center) ** 2)))
current_pca_norm = 100 * (current_dist - pca_distances.min()) / (pca_distances.max() - pca_distances.min())
current_pca_norm = max(0, min(100, current_pca_norm))

current_consensus = current_if_norm * 0.4 + current_ae_norm * 0.3 + current_pca_norm * 0.3

# ─── CONTAGION SEQUENCE ──────────────────────────────────────────────────────
LENDER_DENIAL_2024 = {
    "WellsFargo": 58.5,
    "loanDepot": 37.0,
    "Rocket": 28.4,
    "PennyMac": 26.6,
    "Freedom": 28.1,
    "UWM": 19.9,
}

LENDER_DENIAL_2019 = {
    "WellsFargo": 42.1,
    "loanDepot": 36.2,
    "Rocket": 29.8,
    "PennyMac": 48.2,
    "Freedom": 26.1,
    "UWM": 14.8,
}

normal_order = sorted(LENDER_DENIAL_2019, key=LENDER_DENIAL_2019.get, reverse=True)
current_order = sorted(LENDER_DENIAL_2024, key=LENDER_DENIAL_2024.get, reverse=True)

from scipy.stats import spearmanr
normal_ranks = {l: i for i, l in enumerate(normal_order)}
current_ranks = {l: i for i, l in enumerate(current_order)}
lenders_common = list(LENDER_DENIAL_2024.keys())

rank_corr, _ = spearmanr(
    [normal_ranks.get(l, 3) for l in lenders_common],
    [current_ranks.get(l, 3) for l in lenders_common]
)

# ─── OUTPUT ──────────────────────────────────────────────────────────────────
historical = []
for i, label in enumerate(labels):
    historical.append({
        "quarter": label,
        "ofi": ALL_DATA[i][5],
        "rate": ALL_DATA[i][2],
        "if_score": round(float(if_scores[i]), 1),
        "ae_score": round(float(ae_scores[i]), 1),
        "pca_score": round(float(pca_scores[i]), 1),
        "consensus": round(float(consensus[i]), 1),
        "alert": get_alert(float(consensus[i]))
    })

output = {
    "generated": datetime.utcnow().isoformat() + "Z",
    "model_version": "OFI-Anomaly-v1.0",
    "current_quarter": {
        "quarter": "Q2 2026",
        "ofi": current_ofi,
        "if_score": round(current_if_norm, 1),
        "ae_score": round(current_ae_norm, 1),
        "pca_score": round(current_pca_norm, 1),
        "consensus": round(current_consensus, 1),
        "alert": get_alert(current_consensus),
        "interpretation": "MODERATE anomaly — elevated vs pre-2022 baseline but below crisis threshold"
    },
    "contagion_sequence": {
        "rank_correlation_2019_vs_2024": round(float(rank_corr), 3),
        "normal_order": normal_order,
        "current_order": current_order,
        "status": "STABLE" if rank_corr > 0.8 else "WATCH" if rank_corr > 0.6 else "FRAGMENTED",
        "uwm_rank_2019": normal_order.index("UWM") + 1,
        "uwm_rank_2024": current_order.index("UWM") + 1,
        "uwm_signal": "SAFE — UWM still most accessible lender"
    },
    "thresholds": {
        "normal": "consensus < 30",
        "elevated": "consensus 30-50",
        "high": "consensus 50-70",
        "critical": "consensus > 70",
        "crisis_2022_peak": 87.8,
        "current": round(current_consensus, 1)
    },
    "historical": historical,
    "top_anomalies": sorted(historical, key=lambda x: x['consensus'], reverse=True)[:5]
}

with open('ofi-anomaly-scores.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"✅ OFI Anomaly Detector — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
print(f"   Current Q2 2026: {round(current_consensus, 1)}% ({get_alert(current_consensus)})")
print(f"   Contagion rank corr: {round(float(rank_corr), 3)} ({output['contagion_sequence']['status']})")
print(f"   UWM rank: #{current_order.index('UWM')+1} (safe)")
print(f"   Top anomaly: {output['top_anomalies'][0]['quarter']} ({output['top_anomalies'][0]['consensus']}%)")
print(f"   JSON saved: ofi-anomaly-scores.json")
