#!/usr/bin/env python3
"""FRC IndexNow pusher — Bing/Yandex/Seznam/Naver'a ANINDA URL bildirir.
Ziya'nin makinesinde: python indexnow.py
Yeni sayfa yayinlandiginda calistir. Kota yok, ucretsiz, saniyeler icinde indekse duser."""
import json, urllib.request

KEY = "c6b683da5a78f29f3cfc283546e6ee73"
HOST = "financeratecalc.com"
URLS = [
 "https://financeratecalc.com/fha-denial-rates-alabama.html",
 "https://financeratecalc.com/fha-denial-rates-alaska.html",
 "https://financeratecalc.com/fha-denial-rates-arizona.html",
 "https://financeratecalc.com/fha-denial-rates-arkansas.html",
 "https://financeratecalc.com/fha-denial-rates-california.html",
 "https://financeratecalc.com/fha-denial-rates-colorado.html",
 "https://financeratecalc.com/fha-denial-rates-connecticut.html",
 "https://financeratecalc.com/fha-denial-rates-delaware.html",
 "https://financeratecalc.com/fha-denial-rates-florida.html",
 "https://financeratecalc.com/fha-denial-rates-georgia.html",
 "https://financeratecalc.com/fha-denial-rates-idaho.html",
 "https://financeratecalc.com/fha-denial-rates-illinois.html",
 "https://financeratecalc.com/fha-denial-rates-indiana.html",
 "https://financeratecalc.com/fha-denial-rates-iowa.html",
 "https://financeratecalc.com/fha-denial-rates-kansas.html",
 "https://financeratecalc.com/fha-denial-rates-kentucky.html",
 "https://financeratecalc.com/fha-denial-rates-louisiana.html",
 "https://financeratecalc.com/fha-denial-rates-maine.html",
 "https://financeratecalc.com/fha-denial-rates-maryland.html",
 "https://financeratecalc.com/fha-denial-rates-massachusetts.html",
 "https://financeratecalc.com/fha-denial-rates-michigan.html",
 "https://financeratecalc.com/fha-denial-rates-minnesota.html",
 "https://financeratecalc.com/fha-denial-rates-mississippi.html",
 "https://financeratecalc.com/fha-denial-rates-missouri.html",
 "https://financeratecalc.com/fha-denial-rates-montana.html",
 "https://financeratecalc.com/fha-denial-rates-nebraska.html",
 "https://financeratecalc.com/fha-denial-rates-nevada.html",
 "https://financeratecalc.com/fha-denial-rates-new-hampshire.html",
 "https://financeratecalc.com/fha-denial-rates-new-jersey.html",
 "https://financeratecalc.com/fha-denial-rates-new-mexico.html",
 "https://financeratecalc.com/fha-denial-rates-new-york.html",
 "https://financeratecalc.com/fha-denial-rates-north-carolina.html",
 "https://financeratecalc.com/fha-denial-rates-north-dakota.html",
 "https://financeratecalc.com/fha-denial-rates-ohio.html",
 "https://financeratecalc.com/fha-denial-rates-oklahoma.html",
 "https://financeratecalc.com/fha-denial-rates-oregon.html",
 "https://financeratecalc.com/fha-denial-rates-pennsylvania.html",
 "https://financeratecalc.com/fha-denial-rates-rhode-island.html",
 "https://financeratecalc.com/fha-denial-rates-south-carolina.html",
 "https://financeratecalc.com/fha-denial-rates-south-dakota.html",
 "https://financeratecalc.com/fha-denial-rates-tennessee.html",
 "https://financeratecalc.com/fha-denial-rates-texas.html",
 "https://financeratecalc.com/fha-denial-rates-utah.html",
 "https://financeratecalc.com/fha-denial-rates-virginia.html",
 "https://financeratecalc.com/fha-denial-rates-washington.html",
 "https://financeratecalc.com/fha-denial-rates-west-virginia.html",
 "https://financeratecalc.com/fha-denial-rates-wisconsin.html",
 "https://financeratecalc.com/fha-denial-rates-wyoming.html",
 "https://financeratecalc.com/fha-denial-rates-puerto-rico.html",
 "https://financeratecalc.com/fha-rates-vs-denial.html",
 "https://financeratecalc.com/fha-lenders-by-state.html",
 "https://financeratecalc.com/fha-denial-reasons-by-lender.html",
 "https://financeratecalc.com/fha-denial-rates-by-state.html",
 "https://financeratecalc.com/fha-denial-rates-by-loan-amount.html",
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
