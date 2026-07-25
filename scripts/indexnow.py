#!/usr/bin/env python3
"""FRC IndexNow pusher — Bing/Yandex/Seznam/Naver'a ANINDA URL bildirir.
Ziya'nin makinesinde: python indexnow.py
Sitemap'i canli okur; yeni sayfalar otomatik dahil olur. Kota yok, ucretsiz.
"""
import json, urllib.request, re, sys

KEY  = "c6b683da5a78f29f3cfc283546e6ee73"
HOST = "financeratecalc.com"
SITEMAP = "https://financeratecalc.com/sitemap.xml"
BATCH = 500          # IndexNow tek istekte 10.000'e izin verir; 500 guvenli
UA = {"User-Agent": "Mozilla/5.0 (FRC IndexNow)"}

def fetch_urls():
    req = urllib.request.Request(SITEMAP, headers=UA)
    xml = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)
    seen, out = set(), []
    for u in urls:
        if HOST in u and u not in seen:
            seen.add(u); out.append(u)
    return out

def push(urls):
    payload = {"host": HOST, "key": KEY,
               "keyLocation": f"https://{HOST}/{KEY}.txt", "urlList": urls}
    req = urllib.request.Request("https://api.indexnow.org/indexnow",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json; charset=utf-8", **UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status

def main():
    try:
        urls = fetch_urls()
    except Exception as e:
        print("Sitemap okunamadi:", e); sys.exit(1)
    print(f"Sitemap'te {len(urls)} URL bulundu. Gonderiliyor...")
    ok = 0
    for i in range(0, len(urls), BATCH):
        chunk = urls[i:i+BATCH]
        try:
            st = push(chunk)
            print(f"  parti {i//BATCH+1}: HTTP {st} — {len(chunk)} URL")
            if st in (200, 202): ok += len(chunk)
        except Exception as e:
            print(f"  parti {i//BATCH+1} HATA: {e}")
    print(f"IndexNow tamam: {ok}/{len(urls)} URL bildirildi (200/202 = basarili)")

if __name__ == "__main__":
    main()
