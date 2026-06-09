import json, requests, os, time
from datetime import datetime, timedelta

# Google Trends via pytrends (no API key needed)
# Install: pip install pytrends

KEYWORDS = [
    "mortgage denied",
    "FHA loan denied", 
    "mortgage lender Texas",
    "CrossCountry mortgage",
    "FHA approval",
    "mortgage rejection"
]

def get_trends():
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10,25))
        
        results = {}
        
        # 2'şer kelime grupla (pytrends max 5)
        for i in range(0, len(KEYWORDS), 2):
            batch = KEYWORDS[i:i+2]
            try:
                pytrends.build_payload(batch, cat=67, timeframe='now 7-d', geo='US')
                interest = pytrends.interest_over_time()
                
                if not interest.empty:
                    for kw in batch:
                        if kw in interest.columns:
                            vals = interest[kw].tolist()
                            if vals:
                                current = vals[-1]
                                avg = sum(vals) / len(vals) if vals else 50
                                change = round(((current - avg) / max(avg, 1)) * 100)
                                results[kw] = {
                                    'current': int(current),
                                    'avg_7d': round(avg, 1),
                                    'change_pct': change,
                                    'signal': 'SPIKE' if change > 30 else ('DIP' if change < -20 else 'NORMAL')
                                }
                time.sleep(3)  # Rate limit
            except Exception as e:
                print(f"Batch error: {e}")
                continue
        
        return results
    except ImportError:
        # Pytrends yok — mock veri
        print("pytrends not installed, using baseline data")
        return {kw: {'current': 50, 'avg_7d': 50, 'change_pct': 0, 'signal': 'NORMAL'} for kw in KEYWORDS}

def analyze_signals(trends):
    spikes = [(kw, d) for kw, d in trends.items() if d['signal'] == 'SPIKE']
    dips = [(kw, d) for kw, d in trends.items() if d['signal'] == 'DIP']
    
    # Market signal
    if len(spikes) >= 2:
        market_signal = 'HIGH_DEMAND'
        signal_text = f"Search interest elevated — {len(spikes)} denial-related terms spiking"
    elif len(dips) >= 2:
        market_signal = 'LOW_DEMAND'
        signal_text = "Search interest below average — quieter market week"
    else:
        market_signal = 'NORMAL'
        signal_text = "Search interest tracking normal levels"
    
    return {
        'market_signal': market_signal,
        'signal_text': signal_text,
        'spikes': [(kw, d['change_pct']) for kw, d in spikes],
        'top_keyword': max(trends.items(), key=lambda x: x[1]['current'])[0] if trends else None
    }

def main():
    print(f"Running trends tracker — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    trends = get_trends()
    analysis = analyze_signals(trends)
    
    output = {
        'generated': datetime.now().strftime('%Y-%m-%d'),
        'week': datetime.now().strftime('%Y-W%V'),
        'trends': trends,
        'analysis': analysis
    }
    
    # Kaydet
    with open('_data/trends_signal.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Market signal: {analysis['market_signal']}")
    print(f"Message: {analysis['signal_text']}")
    
    if analysis['spikes']:
        print(f"Spikes: {analysis['spikes']}")
    
    # Market signal sayfasını güncelle
    update_market_signal(analysis)

def update_market_signal(analysis):
    path = 'market-signal.html'
    if not os.path.exists(path):
        return
    
    with open(path, 'r', errors='ignore') as f:
        c = f.read()
    
    # Trends signal badge ekle/güncelle
    badge_old = '<!-- TRENDS_SIGNAL -->'
    badge_html = f'''<!-- TRENDS_SIGNAL -->
<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:10px 14px;margin-bottom:12px;font-size:12px;">
  <span style="font-size:10px;color:rgba(255,255,255,0.3);text-transform:uppercase;letter-spacing:0.08em;">Search Trends · This Week</span><br>
  <span style="color:{'#27ae60' if analysis['market_signal']=='HIGH_DEMAND' else '#C8A84B'};font-weight:700;">{analysis['signal_text']}</span>
</div>'''
    
    if badge_old in c:
        import re
        c = re.sub(r'<!-- TRENDS_SIGNAL -->.*?</div>', badge_html, c, flags=re.DOTALL)
    else:
        c = c.replace('<body>', '<body>\n' + badge_html, 1)
    
    with open(path, 'w') as f:
        f.write(c)
    print("✅ market-signal.html güncellendi")

if __name__ == '__main__':
    main()
