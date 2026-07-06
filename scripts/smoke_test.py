#!/usr/bin/env python3
"""FRC engine smoke test — run before ANY push touching engine pages.
Extracts every inline <script>, syntax-checks with node, verifies referenced _data/ files exist."""
import re, subprocess, sys, os, tempfile

ENGINES = ['verdict.html','zai-one.html','lender-response-surface.html',
           'lender-similarity.html','shock-beta.html','index.html',
           'mortgage-correlation-research.html','black-hole-report.html']
FAIL = 0
for page in ENGINES:
    if not os.path.exists(page):
        print(f"  ⚠ {page}: dosya yok, atlandı"); continue
    html = open(page, errors='ignore').read()
    scripts = [(attrs, body) for attrs, body in
               re.findall(r'<script((?:(?!src=)[^>])*)>(.*?)</script>', html, re.S)
               if 'ld+json' not in attrs and 'src=' not in attrs]
    scripts = [b for _, b in scripts]
    ok = True
    for i, js in enumerate(s for s in scripts if s.strip()):
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as t:
            t.write(js); tf = t.name
        r = subprocess.run(['node','--check',tf], capture_output=True, text=True)
        os.unlink(tf)
        if r.returncode != 0:
            ok = False; FAIL += 1
            print(f"  ✗ {page} [script #{i}]: {' | '.join(r.stderr.strip().splitlines()[-3:-1])[:160]}")
    # sayfanın çektiği _data dosyaları repoda var mı
    for ref in set(re.findall(r'_data/([\w.]+\.json)', html)):
        if not os.path.exists(f'_data/{ref}'):
            ok = False; FAIL += 1
            print(f"  ✗ {page}: _data/{ref} REPODA YOK")
    if ok: print(f"  ✓ {page}")
print(f"\n{'❌ FAIL — PUSH ETME' if FAIL else '✅ TÜM MOTORLAR SAĞLAM'} ({FAIL} hata)")
sys.exit(1 if FAIL else 0)
