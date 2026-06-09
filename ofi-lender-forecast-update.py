import json, os, requests
from datetime import datetime

FRED_KEY = os.environ.get('FRED_API_KEY', '')

# LSI bazlı lender forecast — OFI değişince ne olur
LSI_SCORES = {
    'CrossCountry': 6, 'Guild': 21, 'PennyMac': 17, 'Rocket': 16,
    'UWM': 30, 'Mr. Cooper': 32, 'Wells Fargo': 29, 'Planet Home': 38,
    'loanDepot': 44, 'Freedom': 50, 'NewRez': 57
}

# FRED'den mortgage rate çek
current_rate = 6.8
if FRED_KEY:
    try:
        r = requests.get(f'https://api.stlouisfed.org/fred/series/observations?series_id=MORTGAGE30US&api_key={FRED_KEY}&sort_order=desc&limit=1&file_type=json', timeout=10)
        if r.ok:
            obs = r.json().get('observations', [])
            if obs and obs[0]['value'] != '.':
                current_rate = float(obs[0]['value'])
    except:
        pass

# OFI hesapla (rate bazlı)
ofi = min(85, max(20, round(current_rate * 8.2)))

# Her lender için forecast
forecasts = {}
for lender, lsi in LSI_SCORES.items():
    # OFI arttıkça LSI yüksek lenderlar daha fazla etkiliyor
    sensitivity = lsi / 100
    projected_denial_change = round((ofi - 47) * sensitivity * 0.3, 1)
    
    signal = 'STABLE' if lsi <= 25 else ('REACTIVE' if lsi <= 55 else 'HIGH RISK')
    
    forecasts[lender] = {
        'lsi': lsi,
        'signal': signal,
        'ofi': ofi,
        'projected_change': projected_denial_change,
        'updated': datetime.now().strftime('%Y-%m-%d')
    }

output = {
    'ofi': ofi,
    'mortgage_rate': current_rate,
    'generated': datetime.now().strftime('%Y-%m-%d'),
    'forecasts': forecasts
}

with open('ofi-lender-predictions.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"✅ Forecast updated — OFI {ofi}, Rate {current_rate}%")
for l, d in sorted(forecasts.items(), key=lambda x: x[1]['lsi']):
    print(f"  {l}: LSI {d['lsi']} {d['signal']} | Change: {d['projected_change']:+.1f}pp")
