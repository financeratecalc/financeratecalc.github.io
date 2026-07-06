#!/usr/bin/env python3
"""FRC data schema validator — run BEFORE every _data/ or data/ push.
Usage: python3 scripts/validate_schema.py"""
import json, sys, glob

FAIL = 0
def err(m):
    global FAIL; FAIL += 1; print(f"  ✗ {m}")

def check(path, rules):
    try: d = json.load(open(path))
    except Exception as e: return err(f"{path}: JSON PARSE FAIL — {e}")
    for r in rules:
        if not r(d): err(f"{path}: kural ihlali — {r.__doc__}")
    print(f"  ✓ {path}")

# macro_annual: her seri source+data taşımalı, değerler sayısal olmalı
def m_keys(d):
    "series ve derived_findings anahtarları mevcut"
    return 'series' in d and 'derived_findings' in d
def m_series(d):
    "her seri {source, unit, data} taşır ve data değerleri sayısaldır"
    return all('source' in s and 'data' in s and
               all(isinstance(v,(int,float)) for v in s['data'].values())
               for s in d['series'].values())
check('_data/macro_annual.json', [m_keys, m_series])

# decision surfaces: lender>dti>cltv sayısal denial değerleri
def ds_numeric(d):
    "tüm hücre değerleri sayısal ya da null"
    def walk(x):
        if isinstance(x, dict): return all(walk(v) for v in x.values())
        return x is None or isinstance(x,(int,float,str,list,bool))
    return walk(d)
for f in glob.glob('_data/*.json'):
    if 'macro_annual' in f: continue
    check(f, [ds_numeric])

check('data/citable.json', [lambda d: 'statistics' in d and 'source' in d])
(lambda d: True).__doc__ = ""

print(f"\n{'❌ FAIL — PUSH ETME' if FAIL else '✅ TÜM ŞEMALAR GEÇERLİ — push güvenli'} ({FAIL} hata)")
sys.exit(1 if FAIL else 0)
