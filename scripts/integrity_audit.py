#!/usr/bin/env python3
"""FRC INTEGRITY AUDIT — her push oncesi calisir.
Amac: 'sitede boyle seyler bulmak' isini Ziya'dan alip makineye vermek.
Kullanim: python3 scripts/integrity_audit.py     (repo kokunden)
Cikis kodu 1 = ihlal var, push edilmemeli.
"""
import re, os, glob, sys, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

HTML = glob.glob('*.html') + glob.glob('metro/*.html') + glob.glob('stat/*.html') + glob.glob('salary/*.html')
TXT  = ['llms.txt', 'README.md']

# --- 1) ESKI EVREN / ESKI RAKAM KALINTILARI ---
STALE = {
    r'\b11 (major )?lenders?\b'        : 'eski evren (11 lender) — artik 100',
    r'310,592'                          : 'eski evren toplami',
    r'2\.9 ?million FHA records'        : 'eski evren toplami',
    r'\b8x spread\b|roughly a 8x'       : 'eski makas (8x) — artik 44x',
    r'6\.5% \(CrossCountry\)'           : 'eski uc deger',
    r'52\.3% \(NewRez\)'                : 'eski uc deger',
    r'[Ee]very 4 [Mm]inutes'            : 'eski Denial Clock (4 dk) — artik 2 dk',
    r'103,022'                          : 'eski Denial Clock tabani',
    r'\b23-year (banker|banking)'       : 'B-formulune aykiri kimlik',
    r'1,217,297'                        : 'HECM-oncesi evren (dogru: 1,187,606)',
    r'national (rate|denial rate) of 21\.7%|21\.7% nationally|21\.7% of 1,1|21\.7% \(national'  : 'HECM-oncesi ulusal oran (dogru: 22.1%)',
    r'median (share is )?1\.2%'          : 'HECM-oncesi incomplete medyani (dogru: 1.8%)',
    r'73\.5% of Carrington|Carrington 73\.5' : 'HECM-oncesi Carrington (dogru: 75.2%)',
    r'8\.9% to 31\.8%'                   : 'HECM-oncesi metro araligi (dogru: 9.0-32.9)',
    r'3\.19(&times;|x) in Idaho|Idaho[^.]{0,40}3\.19'  : 'HECM-oncesi Idaho cezasi (dogru: 4.45x)',
    r'3\.61(&times;|x) in El Paso|El Paso[^.]{0,40}3\.61'  : 'HECM-oncesi El Paso cezasi (dogru: 3.94x)',
    r'6\.5% to 52\.3%|6\.5%-52\.3%'      : 'Eski 11-lender evreni (dogru: 1.8% to 78.7%)',
    r'quarterly (signal|index|measure|score)|per quarter' : 'HMDA yillik — ceyreklik olcu kaynakta yok',
    r'(?<!almost )\bnobody publishes\b|(?<!Almost )\bNobody publishes\b|\bno one else publishes\b(?! free)' : 'Dogrulanmamis ozgunluk iddiasi (nitelendir: "almost nobody publishes free and current")',
    r'\bretired (banker|23)'            : 'YASAK: retired ibaresi',
}

# --- 1b) ISVEREN / KISISEL KIMLIK SIZINTISI (Ziya'nin aktif isi korunur) ---
EMPLOYER = {
    r'(?i)\bi[sş] bankas[iı]\b|\bisbank\b|\bi[sş]bank\b'      : 'ISVEREN ADI sizintisi',
    r'(?i)t[uü]rkiye i[sş]'                                          : 'ISVEREN ADI sizintisi',
    r'(?i)\bmy day job\b|\bwhere i currently work\b'             : 'aktif istihdam ifsasi',
    r'(?i)\bcurrently (a )?(bank |branch )?manager\b'               : 'aktif unvan ifsasi',
    r'(?i)\bi (currently )?work (at|for) (a |the )?bank\b'        : 'aktif istihdam ifsasi',
    r'(?i)\bbased in (turkey|adana|mersin|istanbul|ankara)\b'       : 'kisisel konum ifsasi',
    r'(?i)\blinkedin\.com/in/'                                      : 'kisisel LinkedIn profili linki',
}

# --- 2) KIMLIK / VAAT IHLALLERI ---
FORBIDDEN = {
    r'googlesyndication|adsbygoogle' : 'REKLAM scripti (site "no ads" diyor)',
    r'approval (probability|odds) (of|for) your'  : 'P_approve vaadi',
    r'we will match you with|lenders will contact you' : 'arka-ucsuz pazar vaadi',
    r'guarantee[d]? approval'         : 'onay garantisi',
}

def scan(patterns, label, files):
    hits = []
    for f in files:
        if f.endswith('corrections.html') or f.endswith('reconciliation.html') or f.endswith('claims.json') or f.endswith('ofi-evidence.html') or f.endswith('ofi-for-lenders.html'):
            continue   # duzeltme kaydi ve sapma teshisi eski rakamlari BILEREK icerir
        try:
            s = open(f, encoding='utf-8', errors='ignore').read()
        except Exception:
            continue
        for pat, why in patterns.items():
            for m in re.finditer(pat, s):
                hits.append((f, why, s[max(0, m.start()-40):m.start()+50].replace('\n', ' ')))
                break
    if hits:
        print(f"\n[{label}] {len(hits)} bulgu:")
        for f, why, ctx in hits[:25]:
            print(f"  {f}: {why}\n      ...{ctx.strip()}...")
    return len(hits)

# --- 3) KIRIK IC LINK ---
def broken_links():
    bad = {}
    for f in HTML:
        s = open(f, encoding='utf-8', errors='ignore').read()
        for href in set(re.findall(r'href="(/[^":#?]+\.(?:html|txt|json|xml|png|pdf))"', s)):
            t = href.lstrip('/')
            if not os.path.exists(t):
                bad.setdefault(href, []).append(f)
    if bad:
        print(f"\n[KIRIK LINK] {len(bad)} hedef:")
        for k, v in sorted(bad.items(), key=lambda x: -len(x[1]))[:15]:
            print(f"  {k}  <- {len(v)} sayfa (orn: {v[0]})")
    return len(bad)

# --- 4) SATILAN AMA OLMAYAN OZELLIK ---
def phantom_products():
    if not os.path.exists('pricing.html'):
        return 0
    s = open('pricing.html', encoding='utf-8', errors='ignore').read()
    # "IN DEVELOPMENT" etiketli bolumden sonrasi muaf (waitlist urunu)
    dev = s.find('IN DEVELOPMENT')
    sellable = s[:dev] if dev > 0 else s
    feats = re.findall(r'<li[^>]*>([^<]{6,70})</li>', sellable)
    known_ok = ['everything in', 'unlimited', 'denial clock', 'state ofi', 'condo', 'lender stress',
                'denial letter', 'zai', 'matrix', 'bulk tools', 'lsi', 'priority', 'analyses',
                'state map', 'the verdict', 'the vintage', 'the meter', '12b gap', 'pre-flight']
    sus = [f.strip() for f in feats if not any(k in f.lower() for k in known_ok)]
    if sus:
        print(f"\n[SUPHELI SATIS VAADI] pricing.html icinde {len(sus)} kalem — teslim edilebilir mi?")
        for f in sus[:12]:
            print(f"  - {f}")
    return len(sus)

# --- 5) CANONICAL / GA4 EKSIGI (amiral sayfalar) ---
FLAGSHIPS = ['index.html', 'fha-loan-denied-now-what.html', 'fha-denial-rates-top-100.html',
             'fha-denial-rates-by-metro.html', 'methodology.html', 'data-sources.html',
             'the-incomplete-wall.html', 'the-builders-door.html', 'same-lender-different-city.html',
             'salary-vs-denial-risk-by-state.html', 'ai-benchmark.html', 'pricing.html']
def flagship_health():
    n = 0
    for f in FLAGSHIPS:
        if not os.path.exists(f):
            print(f"\n[AMIRAL EKSIK] {f} yok"); n += 1; continue
        s = open(f, encoding='utf-8', errors='ignore').read()
        if 'canonical' not in s:
            print(f"[CANONICAL YOK] {f}"); n += 1
        if 'G-ND9P4F3PHT' not in s:
            print(f"[GA4 YOK] {f}"); n += 1
        if re.search(r'<meta name="robots"[^>]*noindex', s):
            print(f"[NOINDEX!] {f} — amiral sayfa indekslenemez durumda"); n += 1
    return n

print("=" * 60)
print("FRC INTEGRITY AUDIT")
print("=" * 60)
total = 0
total += scan(STALE, 'ESKI RAKAM/KIMLIK', HTML + TXT)
total += scan(EMPLOYER, 'ISVEREN/KISISEL SIZINTI', HTML + TXT)
total += scan(FORBIDDEN, 'YASAK ICERIK', HTML)
total += broken_links()
total += phantom_products()
total += flagship_health()

print("\n" + "=" * 60)
if total == 0:
    print("TEMIZ — ihlal yok.")
else:
    print(f"TOPLAM {total} BULGU — push oncesi duzelt.")
print("=" * 60)
sys.exit(1 if total else 0)
