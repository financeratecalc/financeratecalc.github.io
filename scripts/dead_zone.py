#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FRC DEAD ZONE ANALIZI — kucuk kredi cezasi var mi?
===================================================
KULLANIM: python dead_zone.py "C:\\Users\\ziyet\\Downloads\\year_2025_loan_types_2.csv"
CIKTI: dead_zone.json  -> zip'le, Fable'a yukle.

Hesapladigi: kredi tutari bandi x red orani + her bandin ilk 3 red sebebi.
Stdlib-only, 768MB'i akitarak okur (build_tier2 ile ayni motor).
"""
import sys, json, io, zipfile, os

BANDS = [(0,100000,"<$100K"),(100000,150000,"$100-150K"),(150000,200000,"$150-200K"),
         (200000,250000,"$200-250K"),(250000,300000,"$250-300K"),(300000,400000,"$300-400K"),
         (400000,10**9,"$400K+")]
REASONS = {'1':'Debt-to-income ratio','2':'Employment history','3':'Credit history',
           '4':'Collateral','5':'Insufficient cash','6':'Unverifiable information',
           '7':'Credit application incomplete','8':'Mortgage insurance denied','9':'Other','10':'Other'}

def open_any(p):
    if p.lower().endswith('.zip'):
        z = zipfile.ZipFile(p); n = next(x for x in z.namelist() if x.lower().endswith(('.csv','.txt')))
        return io.TextIOWrapper(z.open(n), encoding='utf-8', errors='replace')
    return open(p, encoding='utf-8', errors='replace')

def main():
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    f = open_any(sys.argv[1])
    head = f.readline(); d = '|' if head.count('|') > head.count(',') else ','
    cols = [c.strip().strip('"').lower() for c in head.split(d)]
    def col(*cands):
        for cand in cands:
            for i,c in enumerate(cols):
                if c == cand: return i
        for cand in cands:
            for i,c in enumerate(cols):
                if cand in c: return i
        return None
    i_at, i_amt = col('action_taken'), col('loan_amount')
    i_dr = [col('denial_reason-1','denial_reason_1'), col('denial_reason-2','denial_reason_2'),
            col('denial_reason-3','denial_reason_3'), col('denial_reason-4','denial_reason_4')]
    i_dr = [x for x in i_dr if x is not None]
    print(f"  ayirac='{d}' action={i_at} amount={i_amt} reason-sutunlari={len(i_dr)}")

    agg = {b[2]: {"apps":0,"denials":0,"reasons":{}} for b in BANDS}
    total = 0
    for line in f:
        total += 1
        if total % 500000 == 0: print(f"  ...{total:,}")
        p = line.rstrip('\n').split(d)
        if len(p) <= max(i_at, i_amt): continue
        at = p[i_at].strip().strip('"')
        if at not in ('1','2','3'): continue
        try: amt = float(p[i_amt].strip().strip('"'))
        except: continue
        band = next((b[2] for b in BANDS if b[0] <= amt < b[1]), None)
        if not band: continue
        a = agg[band]; a["apps"] += 1
        if at == '3':
            a["denials"] += 1
            for ix in i_dr:
                if ix < len(p):
                    r = p[ix].strip().strip('"')
                    if r and r in REASONS:
                        a["reasons"][REASONS[r]] = a["reasons"].get(REASONS[r], 0) + 1
    f.close()
    out = {"method":"FHA 2025 (loan_type 2); decisioned apps (action 1,2,3); denial=3; loan_amount HMDA midpoint; reasons from denial_reason-1..4 (a denied file may cite multiple).",
           "bands":[]}
    for _,_,name in BANDS:
        a = agg[name]
        top3 = sorted(a["reasons"].items(), key=lambda kv:-kv[1])[:3]
        out["bands"].append({"band":name,"apps":a["apps"],"denials":a["denials"],
            "denial_rate_pct": round(100.0*a["denials"]/a["apps"],1) if a["apps"] else None,
            "top_reasons":[{"reason":r,"count":c,"share_of_denials_pct":round(100.0*c/a["denials"],1)} for r,c in top3] if a["denials"] else []})
    json.dump(out, open("dead_zone.json","w"), indent=1)
    print(f"\nOK -> dead_zone.json  (toplam {total:,} satir)")
    for b in out["bands"]:
        print(f"   {b['band']:<10} n={b['apps']:>9,}  red={b['denial_rate_pct']}%" + (f"  | #1 sebep: {b['top_reasons'][0]['reason']}" if b['top_reasons'] else ""))

if __name__ == "__main__": main()
