#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FRC PULSE v1 — kaynak nabzi. Kimseye posta atmaz; KAYNAKLARI izler.
Ziya'nin makinesinde: python pulse.py
FHFA HPI, CFPB HMDA ve Fed SLOOS sayfalarinin degisip degismedigini
(icerik parmak iziyle) kontrol eder. Degisen varsa soyler -> sen indirirsin,
Fable isler, site tazelenir, Climate bulteni o ay tazeleme notuyla cikar.
Zamanli-tetikleyicinin DURUST hali: makine kaynagi izler, insan yayinlar."""
import urllib.request, hashlib, json, datetime

SOURCES = {
 'FHFA HPI (eyalet ceyreklik)': 'https://www.fhfa.gov/data/hpi/datasets',
 'CFPB HMDA (yillik vintage)':  'https://ffiec.cfpb.gov/data-publication/',
 'Fed SLOOS (ceyreklik anket)': 'https://www.federalreserve.gov/data/sloos.htm',
}
UA = {'User-Agent': 'Mozilla/5.0 (FRC-pulse; press@financeratecalc.com)'}
try: state = json.load(open('pulse_state.json'))
except Exception: state = {}

print('=== FRC PULSE —', datetime.date.today(), '===\n')
changed = 0
for name, url in SOURCES.items():
    try:
        req = urllib.request.Request(url, headers=UA)
        body = urllib.request.urlopen(req, timeout=20).read()
        fp = hashlib.sha256(body).hexdigest()[:16]
    except Exception as e:
        print('  ! erisim hatasi (%s): %s' % (name, e)); continue
    old = state.get(name)
    if old is None:
        print('  [ilk kayit] %s' % name)
    elif old != fp:
        changed += 1
        print('  >>> DEGISTI: %s' % name)
        print('      %s' % url)
        print('      -> Yeni veri olabilir. Indir, Fable\'a haber ver; validate_schema kapisindan gecsin.')
    else:
        print('  [sakin] %s' % name)
    state[name] = fp
json.dump(state, open('pulse_state.json', 'w'), indent=1)
print('\n%d kaynakta hareket. Ritm: haftada 1-2 kosu yeter.' % changed)
