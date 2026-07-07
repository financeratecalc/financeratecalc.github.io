#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FRC RADAR v1 — makine tarar, INSAN cevaplar.
Ziya'nin makinesinde calisir:  python radar.py
Reddit'in halka acik JSON aramasini tarar, FRC verisiyle cevaplanabilir
taze sorulari bulur, her birine hangi verinin dustugunu soyler.
KURAL: Cevaplari SEN yazarsin, kendi kimliginle, "I analyze federal HMDA
data at financeratecalc.com" seffafligiyla. Link'i yalniz veri gercekten
cevapsa birak. Gunde en fazla 3-4 cevap — komsu ol, pazarlamaci degil."""
import json, urllib.request, datetime, time

QUERIES = [
    ('denied fha loan',            'vintage'),
    ('mortgage denied dti',        'surfaces'),
    ('fha denial rate lender',     'table'),
    ('reapply after mortgage denial', 'verdict'),
    ('which fha lender high dti',  'zai'),
]
TALKING = {
 'vintage':  'Yil-iklimi: 2023 en sert yildi (66/100), 2021 en gevsek (21). -> the-vintage.html',
 'surfaces': 'Koordinat verisi: ayni DTIxCLTV hucresinde lenderlar arasi fark 8x olabiliyor. -> fha-denial-rates-by-lender.html',
 'table':    '11 lender tablosu: CrossCountry %6.5 -> NewRez %52.3 (2025). -> fha-denial-rates-by-lender.html',
 'verdict':  'Red lender-desenine mi cevre kosuluna mi bagliydi? 310K kayitla kiyas. -> verdict.html',
 'zai':      'DTI 44-45 cliff lenderdan lendera degisiyor (Rocket +15pp, MrCooper +1.4pp). -> zai-one.html',
}
UA = {'User-Agent': 'FRC-radar/1.0 (manual research tool; contact press@financeratecalc.com)'}
seen = set()
try: seen = set(json.load(open('radar_seen.json')))
except Exception: pass

print('=== FRC RADAR —', datetime.date.today(), '===\n')
found = 0
for q, key in QUERIES:
    url = 'https://www.reddit.com/search.json?q=' + urllib.parse.quote(q) + '&sort=new&t=week&limit=8'
    try:
        req = urllib.request.Request(url, headers=UA)
        data = json.load(urllib.request.urlopen(req, timeout=15))
    except Exception as e:
        print('  ! arama hatasi (%s): %s' % (q, e)); continue
    for ch in data.get('data', {}).get('children', []):
        p = ch['data']
        if p['id'] in seen or p.get('num_comments', 99) > 25: continue
        seen.add(p['id']); found += 1
        print('[%s] r/%s (%d yorum)' % (q, p['subreddit'], p['num_comments']))
        print('   ', p['title'][:110])
        print('    https://reddit.com' + p['permalink'])
        print('    VERI:', TALKING[key], '\n')
    time.sleep(2)
json.dump(sorted(seen), open('radar_seen.json', 'w'))
print('%d yeni av. Kural: gunde en fazla 3-4 cevap, hepsi kendi agzindan, seffaf kimlikle.' % found)
