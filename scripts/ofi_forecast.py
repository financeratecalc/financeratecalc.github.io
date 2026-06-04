import requests
import json
import os
import numpy as np
from datetime import datetime, timedelta

FRED_KEY = os.environ.get("FRED_API_KEY", "")
BASE = "https://api.stlouisfed.org/fred/series/observations"

def get_fred(series_id, limit=24):
    r = requests.get(BASE, params={
        "series_id": series_id,
        "api_key": FRED_KEY,
        "file_type": "json",
        "limit": limit,
        "sort_order": "desc"
    }, timeout=15)
    if r.status_code != 200:
        return []
    obs = r.json().get("observations", [])
    return [(o["date"], float(o["value"])) for o in obs if o["value"] != "."]

def momentum(series, periods=4):
    """Son N periyod momentum — pozitif = stres artıyor"""
    if len(series) < periods + 1:
        return 0
    vals = [v for _, v in series[:periods+1]]
    return (vals[0] - vals[periods]) / abs(vals[periods]) * 100

def normalize(val, min_val, max_val):
    return max(0, min(100, (val - min_val) / (max_val - min_val) * 100))

print("FRED'den veri çekiliyor...")

# Temel seriler
mortgage_rate = get_fred("MORTGAGE30US", 24)
unrate = get_fred("UNRATE", 24)
houst = get_fred("HOUST", 24)        # Housing starts (öncü)
permit = get_fred("PERMIT", 24)      # Building permits (öncü)
sentiment = get_fred("UMCSENT", 24)  # Consumer sentiment (öncü)
fedfunds = get_fred("FEDFUNDS", 12)  # Fed funds
jobless = get_fred("ICSA", 24)       # Weekly jobless claims
delinq = get_fred("DRSFRMACBS", 16)  # Mortgage delinquency

print(f"Mortgage rate: {mortgage_rate[0] if mortgage_rate else 'N/A'}")
print(f"Unemployment: {unrate[0] if unrate else 'N/A'}")
print(f"Housing starts: {houst[0] if houst else 'N/A'}")

# === MEVCUT OFI HESAPLA ===
current_ofi = 47  # Baseline — model update eder

if mortgage_rate and unrate and delinq:
    rate = mortgage_rate[0][1]
    unemp = unrate[0][1]
    delinq_rate = delinq[0][1] if delinq else 1.5
    
    # OFI = f(rate, unemployment, delinquency)
    # Mevcut model: OFI = 4.81 × rate + 20.17
    current_ofi = round(4.81 * rate + 20.17, 1)
    print(f"Mevcut OFI: {current_ofi}")

# === FORWARD-LOOKING GÖSTERGELER ===
# Her gösterge için momentum hesapla

# 1. Mortgage rate momentum (pozitif = sıkılaşma)
rate_mom = momentum(mortgage_rate, 6) if len(mortgage_rate) >= 7 else 0

# 2. Housing starts momentum (negatif = talep düşüyor = ileride tightening)
houst_mom = -momentum(houst, 3) if len(houst) >= 4 else 0  # ters çevir

# 3. Building permits (6 ay öncü gösterge)
permit_mom = -momentum(permit, 3) if len(permit) >= 4 else 0

# 4. Consumer sentiment (düşüş = ileride stres)
sent_mom = -momentum(sentiment, 3) if len(sentiment) >= 4 else 0

# 5. Jobless claims (yükseliş = stres)
jobless_mom = momentum(jobless, 4) if len(jobless) >= 5 else 0

# 6. Fed funds yönü
fed_direction = 0
if len(fedfunds) >= 4:
    fed_direction = (fedfunds[0][1] - fedfunds[3][1]) * 5  # büyütülmüş etki

# === 60 GÜN TAHMİN ===
# Ağırlıklı momentum modeli
weights = {
    "rate": 0.35,      # En güçlü öncü
    "permits": 0.20,   # 6 ay öncü
    "houst": 0.15,     # 3 ay öncü
    "sentiment": 0.15, # 1-3 ay öncü
    "jobless": 0.10,   # Anlık stres
    "fed": 0.05        # Politika yönü
}

total_pressure = (
    rate_mom * weights["rate"] +
    permit_mom * weights["permits"] +
    houst_mom * weights["houst"] +
    sent_mom * weights["sentiment"] +
    jobless_mom * weights["jobless"] +
    fed_direction * weights["fed"]
)

# 60 günlük OFI tahmini
ofi_60 = round(current_ofi + (total_pressure * 0.3), 1)
ofi_60 = max(20, min(90, ofi_60))  # 20-90 arası sınırla

# 90 günlük OFI tahmini (daha az kesin)
ofi_90 = round(current_ofi + (total_pressure * 0.5), 1)
ofi_90 = max(20, min(90, ofi_90))

# === APPROVAL WINDOW SCORE ===
def calc_aws(ofi_current, ofi_60, ofi_90, borrower_type="W2"):
    """
    AWS = Approval Window Score (0-100)
    Yüksek = şimdi başvur
    Düşük = bekle
    """
    # OFI yönü etkisi
    ofi_trend = ofi_current - ofi_60  # pozitif = iyileşiyor
    
    # Borrower type OFI sensitivity
    sensitivity = {
        "W2": 0.3,
        "Self-Employed": 0.8,
        "SSDI": 0.5,
        "1099": 0.7,
        "Retirement": 0.2
    }
    sens = sensitivity.get(borrower_type, 0.5)
    
    # Base AWS: OFI ne kadar düşükse o kadar iyi
    base = 100 - normalize(ofi_current, 20, 90)
    
    # Trend bonusu/cezası
    trend_bonus = ofi_trend * sens * 2
    
    aws = round(max(0, min(100, base + trend_bonus)), 0)
    return int(aws)

# AWS hesapla
aws_now = calc_aws(current_ofi, ofi_60, ofi_90, "W2")
aws_se = calc_aws(current_ofi, ofi_60, ofi_90, "Self-Employed")

# === TAVSİYE ÜRET ===
def get_recommendation(ofi_now, ofi_60, ofi_90):
    delta_60 = ofi_60 - ofi_now
    delta_90 = ofi_90 - ofi_now
    
    if delta_60 > 3:
        return {
            "action": "APPLY NOW",
            "urgency": "HIGH",
            "reason": f"OFI forecast shows tightening in 60 days (+{delta_60:.1f}pp). Current window is favorable.",
            "window": "Now — next 30 days"
        }
    elif delta_60 < -3:
        return {
            "action": "WAIT 60 DAYS",
            "urgency": "LOW", 
            "reason": f"Market conditions improving. OFI projected to ease by {abs(delta_60):.1f}pp in 60 days.",
            "window": "60-90 days from now"
        }
    else:
        return {
            "action": "APPLY NOW",
            "urgency": "MODERATE",
            "reason": "Market conditions stable. No significant change forecast.",
            "window": "Current window is neutral"
        }

recommendation = get_recommendation(current_ofi, ofi_60, ofi_90)

# === ÇIKTI ===
forecast = {
    "generated": datetime.utcnow().isoformat(),
    "ofi": {
        "current": current_ofi,
        "forecast_60d": ofi_60,
        "forecast_90d": ofi_90,
        "trend": "tightening" if ofi_60 > current_ofi else "easing",
        "delta_60d": round(ofi_60 - current_ofi, 1),
        "delta_90d": round(ofi_90 - current_ofi, 1)
    },
    "aws": {
        "W2": aws_now,
        "Self-Employed": aws_se,
        "interpretation": "Higher = better time to apply (0-100)"
    },
    "recommendation": recommendation,
    "inputs": {
        "mortgage_rate": mortgage_rate[0][1] if mortgage_rate else None,
        "unemployment": unrate[0][1] if unrate else None,
        "rate_momentum_6wk": round(rate_mom, 2),
        "permit_momentum": round(permit_mom, 2),
        "sentiment_momentum": round(sent_mom, 2),
        "total_pressure": round(total_pressure, 2)
    },
    "methodology": "OFI = 4.81 × mortgage_rate + 20.17 (base). Forward model uses FRED leading indicators: mortgage rate momentum (35%), building permits (20%), housing starts (15%), consumer sentiment (15%), jobless claims (10%), fed funds direction (5%).",
    "source": "FRED API — Federal Reserve Economic Data"
}

print(f"\n=== OFI FORECAST ===")
print(f"Current OFI: {current_ofi}")
print(f"60-day forecast: {ofi_60} ({forecast['ofi']['delta_60d']:+.1f}pp)")
print(f"90-day forecast: {ofi_90} ({forecast['ofi']['delta_90d']:+.1f}pp)")
print(f"Trend: {forecast['ofi']['trend'].upper()}")
print(f"AWS (W2): {aws_now}/100")
print(f"AWS (Self-Employed): {aws_se}/100")
print(f"Recommendation: {recommendation['action']}")

# Kaydet
os.makedirs("_data", exist_ok=True)
with open("_data/ofi_forecast.json", "w") as f:
    json.dump(forecast, f, indent=2)

print("\n✅ _data/ofi_forecast.json yazıldı")
