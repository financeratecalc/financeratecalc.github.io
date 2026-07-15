#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FRC INDEXNOW — yeni/guncellenen URL'leri Bing'e (ve IndexNow agina) aninda bildirir.
Ziya'nin makinesinde:  python indexnow.py
Varsayilan: priority sitemap'teki TUM amiral gemileri.
Tek URL icin:  python indexnow.py https://financeratecalc.com/climate.html"""
import json, sys, urllib.request, re

KEY = "bd45cca31ee741d782a82eb0be514e13"
HOST = "financeratecalc.com"

def priority_urls():
    raw = urllib.request.urlopen("https://financeratecalc.com/sitemap-priority.xml", timeout=20).read().decode()
    return re.findall(r"<loc>(.*?)</loc>", raw)

urls = sys.argv[1:] or priority_urls()
payload = {"host": HOST, "key": KEY,
           "keyLocation": f"https://{HOST}/{KEY}.txt",
           "urlList": urls[:10000]}
req = urllib.request.Request("https://api.indexnow.org/IndexNow",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json; charset=utf-8"})
try:
    r = urllib.request.urlopen(req, timeout=30)
    print(f"HTTP {r.status} — {len(urls)} URL bildirildi.")
    print("200/202 = kabul edildi. Bing panelinde 'URLs submitted' sayaci artacak.")
except Exception as e:
    print("Hata:", e)
    print("(422 = key dogrulanamadi: key dosyasi canliya cikti mi kontrol et)")
