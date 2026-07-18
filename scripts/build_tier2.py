#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FRC TIER-2 BUILDER — en buyuk ~100 FHA lender'inin yillik red oranlari
=======================================================================
KULLANIM (Ziya'nin makinesinde):
  python build_tier2.py LAR_DOSYASI [TS_DOSYASI]

  LAR_DOSYASI : HMDA loan-level dosyasi (.csv veya .zip olabilir, acmana gerek yok)
                - FFIEC Data Browser'dan FHA filtreli indirme  VEYA
                - Snapshot 2024/2025_public_lar_csv.zip (buyuk ama script akitarak okur)
  TS_DOSYASI  : (istege bagli) Transmittal Sheet - lender ISIMLERI icin
                ornk: 2024_public_ts_csv.zip  (~5MB, kucuk)

CIKTI: lender_tier2.json  -> bunu Fable'a yukle, sayfayi o basar.

Notlar:
- Sadece stdlib (pandas gerekmez). 4GB dosyayi bile RAM sismeden akitir.
- FHA = loan_type 2 (2018+ HMDA semasi). Denominator: action_taken 1,2,3
  (originated + approved-not-accepted + denied) — FRC'nin yayimli konvansiyonu.
- Eslik: n>=500 basvuru alti listeye girmez (yillik agrega istikrari).
"""
import sys, csv, json, io, zipfile, os

def open_any(path):
    """csv ya da zip icindeki ilk .csv/.txt akisini dondur"""
    if path.lower().endswith('.zip'):
        z = zipfile.ZipFile(path)
        name = next(n for n in z.namelist() if n.lower().endswith(('.csv','.txt','.psv')))
        print(f"  zip icinden okunuyor: {name}")
        return io.TextIOWrapper(z.open(name), encoding='utf-8', errors='replace')
    return open(path, encoding='utf-8', errors='replace')

def sniff(f):
    head = f.readline()
    delim = '|' if head.count('|') > head.count(',') else ','
    cols = [c.strip().strip('"').lower() for c in head.split(delim)]
    return delim, cols

def col(cols, *cands):
    for cand in cands:
        for i,c in enumerate(cols):
            if c == cand: return i
    for cand in cands:
        for i,c in enumerate(cols):
            if cand in c: return i
    return None

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    lar_path = sys.argv[1]
    ts_path  = sys.argv[2] if len(sys.argv) > 2 else None

    # ---- 1) isimler (TS varsa)
    names = {}
    if ts_path and os.path.exists(ts_path):
        f = open_any(ts_path); d, cols = sniff(f)
        i_lei, i_name = col(cols,'lei'), col(cols,'respondent_name','institution_name','name')
        for line in f:
            p = line.rstrip('\n').split(d)
            if i_lei is not None and i_name is not None and len(p) > max(i_lei,i_name):
                names[p[i_lei].strip().strip('"')] = p[i_name].strip().strip('"')
        f.close(); print(f"  {len(names)} lender ismi yuklendi (TS)")

    # ---- 2) LAR akisi
    f = open_any(lar_path); d, cols = sniff(f)
    i_lei  = col(cols,'lei')
    i_lt   = col(cols,'loan_type')
    i_at   = col(cols,'action_taken')
    if None in (i_lei, i_lt, i_at):
        print("HATA: lei / loan_type / action_taken sutunlari bulunamadi. Basliklar:", cols[:10]); sys.exit(2)
    print(f"  ayirac='{d}' lei={i_lei} loan_type={i_lt} action={i_at}")

    agg = {}   # lei -> [apps(1/2/3), denials(3)]
    total = fha = 0
    for line in f:
        total += 1
        if total % 1000000 == 0: print(f"  ...{total:,} satir")
        p = line.rstrip('\n').split(d)
        if len(p) <= max(i_lei,i_lt,i_at): continue
        if p[i_lt].strip().strip('"') != '2':  # 2 = FHA (2018+ semasi)
            continue
        at = p[i_at].strip().strip('"')
        if at not in ('1','2','3'):           # kredi karari verilmis dosyalar
            continue
        fha += 1
        lei = p[i_lei].strip().strip('"')
        a = agg.setdefault(lei, [0,0])
        a[0] += 1
        if at == '3': a[1] += 1
    f.close()
    print(f"  toplam satir: {total:,} | FHA karar-dosyasi: {fha:,} | lender: {len(agg):,}")

    # ---- 3) top-100 (n>=500)
    rows = []
    for lei,(apps,den) in agg.items():
        if apps < 500: continue
        rows.append({
            "lei": lei,
            "name": names.get(lei, ""),
            "fha_applications": apps,
            "fha_denials": den,
            "fha_denial_rate_pct": round(100.0*den/apps, 1)
        })
    rows.sort(key=lambda r: -r["fha_applications"])
    rows = rows[:100]

    out = {
        "generated_note": "FRC Tier-2: yillik FHA-only red oranlari, en buyuk 100 FHA lender (basvuru hacmine gore).",
        "method": "FHA = loan_type 2; denominator = action_taken 1,2,3 (originated + approved-not-accepted + denied); denial = action 3; min 500 decisioned FHA applications.",
        "source_file": os.path.basename(lar_path),
        "lender_count": len(rows),
        "lenders": rows
    }
    with open("lender_tier2.json","w") as fo:
        json.dump(out, fo, indent=1)
    print(f"\nOK -> lender_tier2.json ({len(rows)} lender)")
    print("Simdi bu dosyayi Fable'a yukle; sayfa + atomlar + indexnow ondan.")
    for r in rows[:10]:
        print(f"   {r['name'] or r['lei'][:12]}: {r['fha_denial_rate_pct']}%  (n={r['fha_applications']:,})")

if __name__ == "__main__":
    main()
