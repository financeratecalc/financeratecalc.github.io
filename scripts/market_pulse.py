"""
FRC Market Pulse Pipeline
Çalışır: Her Çarşamba 11:00 UTC (MBA yayınından sonra)
Veri: FRED API (MBA Weekly Index + OFI bileşenleri + Freddie Mac PMMS)
"""

import requests
import json
import os
from datetime import datetime

FRED_KEY = os.environ.get("FRED_API_KEY", "e872976af25e927468d55dac36247a4f")
BASE = "https://api.stlouisfed.org/fred/series/observations"

def get_fred(series_id, limit=8):
    r = requests.get(BASE, params={
        "series_id": series_id,
        "api_key": FRED_KEY,
        "file_type": "json",
        "limit": limit,
        "sort_order": "desc"
    }, timeout=15)
    if r.status_code == 200:
        obs = r.json().get("observations", [])
        return [(o["date"], float(o["value"])) for o in obs if o["value"] != "."]
    return []

print("Market Pulse Pipeline başlatılıyor...")

# 1. MBA Weekly Applications Index
mba = get_fred("MMNRNSA", 8)  # MBA Mortgage Applications
mba_purchase = get_fred("MABMM301USM189S", 4)  # MBA Purchase Index

# 2. Freddie Mac PMMS (30yr rate)
pmms_30 = get_fred("MORTGAGE30US", 8)
pmms_15 = get_fred("MORTGAGE15US", 4)

# 3. OFI bileşenleri
fed_funds = get_fred("FEDFUNDS", 4)
unrate = get_fred("UNRATE", 4)
permit = get_fred("PERMIT", 4)
jobless = get_fred("ICSA", 4)
sentiment = get_fred("UMCSENT", 4)

# 4. Piyasa pulse hesapla
pulse = {}

if pmms_30:
    current_rate = pmms_30[0][1]
    prev_rate = pmms_30[1][1] if len(pmms_30) > 1 else current_rate
    rate_change = current_rate - prev_rate
    pulse["mortgage_rate"] = {
        "current": current_rate,
        "prev_week": prev_rate,
        "change": round(rate_change, 3),
        "direction": "up" if rate_change > 0 else "down",
        "date": pmms_30[0][0]
    }
    print(f"✅ 30yr Rate: {current_rate}% ({rate_change:+.3f})")

if mba:
    current_mba = mba[0][1]
    prev_mba = mba[1][1] if len(mba) > 1 else current_mba
    mba_change = (current_mba - prev_mba) / prev_mba * 100
    pulse["mba_index"] = {
        "current": current_mba,
        "prev_week": prev_mba,
        "change_pct": round(mba_change, 1),
        "direction": "up" if mba_change > 0 else "down",
        "date": mba[0][0]
    }
    print(f"✅ MBA Index: {current_mba} ({mba_change:+.1f}%)")

if permit:
    pulse["permits"] = {
        "current": permit[0][1],
        "date": permit[0][0]
    }
    print(f"✅ Building Permits: {permit[0][1]}")

if jobless:
    pulse["jobless_claims"] = {
        "current": jobless[0][1],
        "date": jobless[0][0]
    }
    print(f"✅ Jobless Claims: {jobless[0][1]}")

if sentiment:
    pulse["consumer_sentiment"] = {
        "current": sentiment[0][1],
        "date": sentiment[0][0]
    }
    print(f"✅ Consumer Sentiment: {sentiment[0][1]}")

# 5. Market Signal hesapla
def calc_market_signal(pulse):
    """
    OPEN / TIGHTENING / EASING / VOLATILE
    """
    signals = []
    
    # Rate direction
    if "mortgage_rate" in pulse:
        if pulse["mortgage_rate"]["change"] > 0.1:
            signals.append(("TIGHTENING", 2))
        elif pulse["mortgage_rate"]["change"] < -0.1:
            signals.append(("EASING", 2))
        else:
            signals.append(("STABLE", 1))
    
    # MBA volume direction
    if "mba_index" in pulse:
        if pulse["mba_index"]["change_pct"] > 5:
            signals.append(("EASING", 1))  # More apps = lenders hungry
        elif pulse["mba_index"]["change_pct"] < -5:
            signals.append(("TIGHTENING", 1))
    
    # Count signals
    tightening = sum(w for s, w in signals if s == "TIGHTENING")
    easing = sum(w for s, w in signals if s == "EASING")
    
    if tightening > easing + 1:
        return "TIGHTENING", "Rate momentum and application volume suggest tightening conditions."
    elif easing > tightening + 1:
        return "EASING", "Rate decline and volume increase suggest easing conditions."
    else:
        return "STABLE", "Mixed signals — market conditions appear stable this week."

signal, signal_note = calc_market_signal(pulse)
pulse["market_signal"] = {
    "signal": signal,
    "note": signal_note,
    "generated": datetime.utcnow().isoformat()
}

print(f"✅ Market Signal: {signal}")

# 6. Policy change detection
# Önceki hafta ile karşılaştır
prev_path = "_data/market_pulse_prev.json"
changes = []

if os.path.exists(prev_path):
    with open(prev_path) as f:
        prev = json.load(f)
    
    if "mortgage_rate" in pulse and "mortgage_rate" in prev:
        rate_delta = pulse["mortgage_rate"]["current"] - prev["mortgage_rate"]["current"]
        if abs(rate_delta) > 0.25:
            changes.append({
                "type": "RATE_SHIFT",
                "message": f"30yr rate moved {rate_delta:+.2f}% since last week",
                "severity": "HIGH" if abs(rate_delta) > 0.5 else "MEDIUM"
            })
    
    if "mba_index" in pulse and "mba_index" in prev:
        vol_delta = pulse["mba_index"]["change_pct"]
        if abs(vol_delta) > 10:
            changes.append({
                "type": "VOLUME_SHIFT", 
                "message": f"Mortgage applications {vol_delta:+.1f}% week-over-week",
                "severity": "HIGH" if abs(vol_delta) > 20 else "MEDIUM"
            })

pulse["policy_changes"] = changes
if changes:
    print(f"⚠️ {len(changes)} policy change detected!")
    for c in changes:
        print(f"  [{c['severity']}] {c['message']}")

# 7. Kaydet
os.makedirs("_data", exist_ok=True)

# Bu haftayı "prev" olarak kaydet
if os.path.exists("_data/market_pulse.json"):
    import shutil
    shutil.copy("_data/market_pulse.json", prev_path)

with open("_data/market_pulse.json", "w") as f:
    json.dump(pulse, f, indent=2)

print("\n✅ _data/market_pulse.json kaydedildi")
print(f"Market Signal: {signal}")
print(f"Note: {signal_note}")
