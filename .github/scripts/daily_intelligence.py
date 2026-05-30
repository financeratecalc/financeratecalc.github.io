"""
FRC Daily Intelligence Pipeline
Çalışır: GitHub Actions (her gün 09:00 UTC)
Yapar: CFPB → AI classify → OFI güncelle → JSON yaz
"""

import requests
import json
import os
import re
from datetime import datetime, timedelta

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# ── CFPB COMPLAINTS
def fetch_cfpb(days_back=7):
    """GitHub Actions IP'si CFPB tarafından bloklu değil"""
    date_from = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    try:
        resp = requests.get(
            "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/",
            params={
                'product': 'Mortgage',
                'size': 50,
                'sort': 'created_date_desc',
                'no_aggs': True,
                'date_received_min': date_from
            },
            timeout=30,
            headers={'User-Agent': 'FRC-Research-Bot/1.0 (financeratecalc.com)'}
        )
        
        if resp.status_code == 200:
            hits = resp.json().get('hits', {}).get('hits', [])
            complaints = []
            for h in hits:
                s = h.get('_source', {})
                narrative = s.get('consumer_complaint_narrative', '') or ''
                if not narrative:
                    continue
                complaints.append({
                    'id':        s.get('complaint_id', ''),
                    'date':      s.get('date_received', ''),
                    'company':   s.get('company', ''),
                    'issue':     s.get('issue', ''),
                    'narrative': narrative[:500],
                    'state':     s.get('state', ''),
                })
            print(f"✓ CFPB live: {len(complaints)} complaints")
            return complaints
        else:
            print(f"CFPB status: {resp.status_code}")
            return []
    except Exception as e:
        print(f"CFPB error: {e}")
        return []

# ── AI CLASSIFIER
def classify_complaints(complaints):
    if not complaints or not ANTHROPIC_API_KEY:
        return []
    
    classified = []
    
    for c in complaints[:30]:  # Max 30 per day
        try:
            resp = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': ANTHROPIC_API_KEY,
                    'anthropic-version': '2023-06-01'
                },
                json={
                    'model': 'claude-haiku-4-5-20251001',
                    'max_tokens': 100,
                    'system': 'Return ONLY JSON: {"denial_type":"OVERLAY|AGENCY_RULE|UNCLEAR","confidence":0.9,"denial_factor":"DTI|CREDIT|SSDI|INCOME|EMPLOYMENT|OTHER"}',
                    'messages': [{'role': 'user', 'content': f"Company: {c['company']}\nState: {c['state']}\nNarrative: {c['narrative']}"}]
                },
                timeout=15
            )
            
            data = resp.json()
            text = data.get('content', [{}])[0].get('text', '{}')
            match = re.search(r'\{[^}]+\}', text)
            if match:
                result = json.loads(match.group())
                c['classification'] = result
                classified.append(c)
        except Exception as e:
            print(f"  Classify error: {e}")
    
    print(f"✓ Classified: {len(classified)}")
    return classified

# ── OFI CALCULATOR
def calculate_ofi(classified):
    if not classified:
        return {'ofi': 47, 'delta': 0, 'signal_count': 0, 'source': 'baseline'}
    
    overlay_n = sum(1 for c in classified if c.get('classification', {}).get('denial_type') == 'OVERLAY')
    agency_n  = sum(1 for c in classified if c.get('classification', {}).get('denial_type') == 'AGENCY_RULE')
    total = overlay_n + agency_n
    
    if total == 0:
        return {'ofi': 47, 'delta': 0, 'signal_count': 0, 'source': 'baseline'}
    
    overlay_ratio = overlay_n / total
    baseline = 47
    delta = round((overlay_ratio - 0.6) * 20, 1)
    ofi = round(baseline + delta, 1)
    
    # Factor counts
    factor_counts = {}
    state_counts = {}
    for c in classified:
        if c.get('classification', {}).get('denial_type') == 'OVERLAY':
            factor = c.get('classification', {}).get('denial_factor', 'OTHER')
            factor_counts[factor] = factor_counts.get(factor, 0) + 1
            if c.get('state'):
                state_counts[c['state']] = state_counts.get(c['state'], 0) + 1
    
    # Alerts
    alerts = []
    for f, n in sorted(factor_counts.items(), key=lambda x: -x[1]):
        if n >= 2:
            alerts.append({
                'type': 'FACTOR_SPIKE',
                'signal': f'FRC-SIGNAL: {f} overlays = {n} CFPB signals (7d)',
                'count': n
            })
    for s, n in sorted(state_counts.items(), key=lambda x: -x[1]):
        if n >= 2:
            alerts.append({
                'type': 'REGIONAL',
                'signal': f'FRC-REGIONAL: {s} overlay friction spike ({n} signals)',
                'count': n
            })
    
    # Lender friction
    lender_data = {}
    for c in classified:
        co = c.get('company', 'Unknown')[:35]
        if co not in lender_data:
            lender_data[co] = {'ov': 0, 'ag': 0}
        ct = c.get('classification', {}).get('denial_type', '')
        if ct == 'OVERLAY':    lender_data[co]['ov'] += 1
        if ct == 'AGENCY_RULE': lender_data[co]['ag'] += 1
    
    friction_map = {}
    for co, d in lender_data.items():
        t = d['ov'] + d['ag']
        if t > 0:
            friction_map[co] = {
                'friction_score': round(d['ov']/t*100, 1),
                'overlay_signals': d['ov'],
                'total': t
            }
    friction_map = dict(sorted(friction_map.items(), key=lambda x: -x[1]['friction_score']))
    
    return {
        'ofi':            ofi,
        'baseline':       baseline,
        'delta':          delta,
        'overlay_ratio':  round(overlay_ratio, 2),
        'overlay_count':  overlay_n,
        'agency_count':   agency_n,
        'signal_count':   len(classified),
        'source':         'CFPB_LIVE',
        'alerts':         alerts[:5],
        'friction_map':   friction_map
    }

# ── MAIN
def main():
    print(f"\n{'='*50}")
    print(f"FRC Daily Intelligence — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print('='*50)
    
    # 1. Fetch CFPB
    print("\n[1/3] Fetching CFPB...")
    complaints = fetch_cfpb(days_back=7)
    
    # 2. Classify
    print("\n[2/3] Classifying...")
    classified = classify_complaints(complaints) if complaints else []
    
    # 3. Calculate OFI
    print("\n[3/3] Calculating OFI...")
    ofi_data = calculate_ofi(classified)
    
    # 4. Write live-intelligence.json
    output = {
        'generated':   datetime.now().isoformat(),
        'data_source': 'CFPB Consumer Complaint Database (public federal data)',
        'license':     'CC BY 4.0',
        'methodology': 'financeratecalc.com/ofi-methodology.html',
        'ofi':         ofi_data,
        'classification': {
            'OVERLAY':      ofi_data.get('overlay_count', 0),
            'AGENCY_RULE':  ofi_data.get('agency_count', 0),
        },
        'friction_map':  ofi_data.get('friction_map', {}),
        'active_alerts': ofi_data.get('alerts', [])
    }
    
    with open('live-intelligence.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    # 5. Write ofi-live.json (simple, for widgets)
    ofi_simple = {
        'ofi':       ofi_data['ofi'],
        'delta':     ofi_data['delta'],
        'state':     ('TIGHTENING' if ofi_data['ofi'] > 55 else
                      'MODERATE'   if ofi_data['ofi'] > 40 else 'EXPANSION'),
        'updated':   datetime.now().isoformat(),
        'signals':   ofi_data['signal_count'],
        'source':    ofi_data['source']
    }
    
    with open('ofi-live.json', 'w') as f:
        json.dump(ofi_simple, f, indent=2)
    
    print(f"\n{'='*50}")
    print(f"✅ Done")
    print(f"   OFI: {ofi_data['ofi']} (delta: {ofi_data['delta']:+.1f})")
    print(f"   Signals: {ofi_data['signal_count']}")
    print(f"   Alerts: {len(ofi_data.get('alerts', []))}")
    print('='*50)

if __name__ == '__main__':
    main()
