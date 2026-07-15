#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FRC INDEXNOW — yeni/guncellenen URL'leri Bing'e (ve IndexNow agina) aninda bildirir.
Ziya'nin makinesinde:  python indexnow.py
Varsayilan: priority sitemap'teki TUM amiral gemileri.
Tek URL icin:  python indexnow.py https://financeratecalc.com/climate.html"""
import json, sys, urllib.request, re

KEY = "bd45cca31ee741d782a82eb0be514e13"
HOST = "financeratecalc.com"

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def priority_urls():
    req = urllib.request.Request("https://financeratecalc.com/sitemap-priority.xml", headers=UA)
    raw = urllib.request.urlopen(req, timeout=20).read().decode()
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
