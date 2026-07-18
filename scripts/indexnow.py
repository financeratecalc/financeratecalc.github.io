#!/usr/bin/env python3
"""FRC IndexNow pusher — Bing/Yandex/Seznam/Naver'a ANINDA URL bildirir.
Ziya'nin makinesinde: python indexnow.py
Yeni sayfa yayinlandiginda calistir. Kota yok, ucretsiz, saniyeler icinde indekse duser."""
import json, urllib.request

KEY = "c6b683da5a78f29f3cfc283546e6ee73"
HOST = "financeratecalc.com"
URLS = [
 "https://financeratecalc.com/fha-denial-rates-top-100.html",
 "https://financeratecalc.com/ai-vs-the-data.html",
 "https://financeratecalc.com/answers.html",
 "https://financeratecalc.com/ai-benchmark.html",
 "https://financeratecalc.com/fha-lender-comparison.html",
 "https://financeratecalc.com/fha-denial-rates-by-lender.html",
 "https://financeratecalc.com/climate.html",
 "https://financeratecalc.com/the-vintage.html",
 "https://financeratecalc.com/the-meter.html",
 "https://financeratecalc.com/verdict.html",
 "https://financeratecalc.com/zai-one.html",
 "https://financeratecalc.com/widgets.html",
 "https://financeratecalc.com/about.html",
 "https://financeratecalc.com/crosscountry-fha-denial-rate.html",
 "https://financeratecalc.com/freedom-fha-denial-rate.html",
 "https://financeratecalc.com/guild-fha-denial-rate.html",
 "https://financeratecalc.com/loandepot-fha-denial-rate.html",
 "https://financeratecalc.com/mr-cooper-fha-denial-rate.html",
 "https://financeratecalc.com/newrez-fha-denial-rate.html",
 "https://financeratecalc.com/pennymac-fha-denial-rate.html",
 "https://financeratecalc.com/planet-home-fha-denial-rate.html",
 "https://financeratecalc.com/rocket-fha-denial-rate.html",
 "https://financeratecalc.com/uwm-fha-denial-rate.html",
 "https://financeratecalc.com/wells-fargo-fha-denial-rate.html"
]

payload = {"host": HOST, "key": KEY,
           "keyLocation": f"https://{HOST}/{KEY}.txt", "urlList": URLS}
req = urllib.request.Request("https://api.indexnow.org/indexnow",
    data=json.dumps(payload).encode(), headers={"Content-Type": "application/json; charset=utf-8"})
try:
    r = urllib.request.urlopen(req, timeout=20)
    print(f"IndexNow: HTTP {r.status} — {len(URLS)} URL bildirildi (200/202 = basarili)")
except Exception as e:
    print("Hata:", e)
