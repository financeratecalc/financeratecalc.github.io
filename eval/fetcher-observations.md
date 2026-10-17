# Fetcher observations (hand-recorded from GA4 Realtime; dated; never edited after the fact)

| date | what was seen | signature | source |
|---|---|---|---|
| 2026-10-12/13 | Referrer-less first visits from Singapore to long-tail pages (affordability, salary, age, credit score) | webdriver=no, tz=Asia/Shanghai, Chrome 109 and 133 on Windows 10, no client hints | GA4 direct_or_hidden_referrer parameters, read by Ziya |
| 2026-10-14/16 | Same pattern landing on templated URLs that do not exist ("Page not found"), resolved to the nearest page from 16 Oct | as above (not re-read) | GA4 Realtime screenshots |
| 2026-10-17 | Referrer-less first visits to valid metro pages that carry an evidence footnote and its receipt (Arlington-Alexandria-Reston VA-WV, Cape Coral FL); no "Page not found" views | SG egress; tz/UA for 17 Oct not yet read | GA4 Realtime screenshot 12:40 |
| 2026-10-16 | First outside receipt verifications: GPTBot verified an evidence-footnote receipt (f), Applebot a lender-page receipt (l), both current | worker verify_log, requester class from User-Agent | eval/usage-snapshot.json verify_log_external |
