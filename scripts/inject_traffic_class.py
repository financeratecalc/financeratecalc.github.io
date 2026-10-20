#!/usr/bin/env python3
"""Attach a `traffic_class` parameter to every GA4 event on every page (page_view included).

Why: referrer-less fetcher waves (SG egress, tz Asia/Shanghai, old-Chrome UA, no client hints)
inflate GA "users" and trigger anomaly alerts. We never block them; we label them so GA can
show readers and fetchers in separate columns. The label is set on gtag('config'), so it rides
on the page_view itself, not only on later events. No personal data: three coarse signals.

Classes:
  automation  navigator.webdriver is true
  fetcher     no referrer, no query string, tz Asia/Shanghai|Singapore|Hong_Kong, and
              (Chrome major < 120 or a Chrome UA without userAgentData)
  reader      everything else

Idempotent; rerun after new pages are generated. Register `traffic_class` once in GA4
(Admin > Custom definitions > event-scoped) to filter and compare by it.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GA = "G-ND9P4F3PHT"
CLS = ("(function(){try{if(navigator.webdriver)return'automation';var r=document.referrer,q=location.search,"
       "t=Intl.DateTimeFormat().resolvedOptions().timeZone||'',u=navigator.userAgent||'',m=/Chrome\\/(\\d+)/.exec(u);"
       "if(!r&&!q&&/^Asia\\/(Shanghai|Singapore|Hong_Kong)$/.test(t)&&m&&(+m[1]<120||!navigator.userAgentData))return'fetcher';"
       "return'reader'}catch(e){return'reader'}})()")
NEW = f"gtag('config','{GA}',{{traffic_class:{CLS}}});"
OLD_RX = re.compile(r"gtag\('config',\s*'" + GA + r"'\);")
SKIP = {"404.html"}  # sends its own config (send_page_view:false)


def main():
    changed = seen = 0
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if not d.startswith(".") and d not in ("node_modules", "eval", "rl-env", "fixtures", "examples")]
        for f in fn:
            if not f.endswith(".html"):
                continue
            rel = os.path.relpath(os.path.join(dp, f), ROOT)
            if rel in SKIP:
                continue
            p = os.path.join(dp, f)
            s = open(p, encoding="utf-8").read()
            if GA not in s:
                continue
            seen += 1
            n, k = OLD_RX.subn(lambda _m: NEW, s)
            if k:
                open(p, "w", encoding="utf-8").write(n)
                changed += 1
    print(f"pages with GA: {seen}; rewritten: {changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
