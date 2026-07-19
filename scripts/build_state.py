#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FRC STATE BUILDER — eyalet bazinda FHA red orani (+ tutar kesiti)
==================================================================
KULLANIM: python build_state.py "C:\\Users\\ziyet\\Downloads\\year_2025_loan_types_2.csv"
CIKTI: state_fha.json  -> zip'le, Fable'a yukle.

Hesaplar:
  - 50 eyalet + DC: FHA red orani (n>=200)
  - her eyalet icin: kucuk-kredi (<150K) vs buyuk-kredi (>=250K) red orani
    -> F09 (kucuk-kredi cezasi) cografi olarak degisiyor mu?
Stdlib-only, 768MB akitir.
"""
import sys, json, io, zipfile, os

STATES = {'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC','PR'}

def open_any(p):
    if p.lower().endswith('.zip'):
        z = zipfile.ZipFile(p); n = next(x for x in z.namelist() if x.lower().endswith(('.csv','.txt')))
        return io.TextIOWrapper(z.open(n), encoding='utf-8', errors='replace')
    return open(p, encoding='utf-8', errors='replace')

def main():
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    f = open_any(sys.argv[1])
    head = f.readline(); d = '|' if head.count('|')>head.count(',') else ','
    cols = [c.strip().strip('"').lower() for c in head.split(d)]
    def col(*cc):
        for c in cc:
            for i,x in enumerate(cols):
                if x==c: return i
        for c in cc:
            for i,x in enumerate(cols):
                if c in x: return i
        return None
    i_at, i_st, i_amt = col('action_taken'), col('state_code','state'), col('loan_amount')
    if None in (i_at,i_st): print("HATA: action/state yok:",cols[:8]); sys.exit(2)
    print(f"  ayirac='{d}' action={i_at} state={i_st} amount={i_amt}")

    agg = {}  # st -> [apps, den, small_apps, small_den, big_apps, big_den]
    total=0
    for line in f:
        total+=1
        if total%500000==0: print(f"  ...{total:,}")
        p=line.rstrip('\n').split(d)
        if len(p)<=max(i_at,i_st): continue
        at=p[i_at].strip().strip('"')
        if at not in ('1','2','3'): continue
        st=p[i_st].strip().strip('"').upper()
        if st not in STATES: continue
        a=agg.setdefault(st,[0,0,0,0,0,0]); a[0]+=1
        den = (at=='3')
        if den: a[1]+=1
        if i_amt is not None and len(p)>i_amt:
            try: amt=float(p[i_amt].strip().strip('"'))
            except: amt=None
            if amt is not None:
                if amt<150000: a[2]+=1; a[3]+= 1 if den else 0
                elif amt>=250000: a[4]+=1; a[5]+= 1 if den else 0
    f.close()

    rows=[]
    for st,a in agg.items():
        if a[0]<200: continue
        rows.append({"state":st,"apps":a[0],"denials":a[1],
            "denial_rate_pct":round(100*a[1]/a[0],1),
            "small_loan_denial_pct":round(100*a[3]/a[2],1) if a[2]>=100 else None,
            "big_loan_denial_pct":round(100*a[5]/a[4],1) if a[4]>=100 else None})
    rows.sort(key=lambda r:-r["denial_rate_pct"])
    out={"method":"FHA 2025 (loan_type 2); decisioned apps (1,2,3); denial=3; min 200/state. small=<150K, big=>=250K (min 100 each).",
         "state_count":len(rows),"states":rows}
    json.dump(out,open("state_fha.json","w"),indent=1)
    print(f"\nOK -> state_fha.json ({len(rows)} eyalet, {total:,} satir)")
    print("EN SERT 5:")
    for r in rows[:5]: print(f"   {r['state']}: {r['denial_rate_pct']}%  (kucuk {r['small_loan_denial_pct']} vs buyuk {r['big_loan_denial_pct']})")
    print("EN YUMUSAK 5:")
    for r in rows[-5:]: print(f"   {r['state']}: {r['denial_rate_pct']}%")

if __name__=="__main__": main()
