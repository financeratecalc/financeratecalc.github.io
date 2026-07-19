#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FRC TIER-5 BUILDER — tek geciste iki kesit:
  A) KAPININ FIYATI: lender basina (originated FHA purchase, n>=500):
     medyan rate_spread + medyan faiz + red orani -> "yumusak kapi pahali mi?"
  B) PREFABRIK CEZASI: site-built vs manufactured red oranlari + manufactured'in buyuk lender'lari
KULLANIM: python build_tier5.py "C:\\Users\\ziyet\\Downloads\\year_2025_loan_types_2.csv"
CIKTI: tier5.json -> zip'le yukle.
"""
import sys, json, io, zipfile

def open_any(p):
    if p.lower().endswith('.zip'):
        z=zipfile.ZipFile(p); n=next(x for x in z.namelist() if x.lower().endswith(('.csv','.txt')))
        return io.TextIOWrapper(z.open(n),encoding='utf-8',errors='replace')
    return open(p,encoding='utf-8',errors='replace')

def med(v):
    if not v: return None
    v=sorted(v); n=len(v)
    return round(v[n//2] if n%2 else (v[n//2-1]+v[n//2])/2, 3)

def main():
    if len(sys.argv)<2: print(__doc__); sys.exit(1)
    f=open_any(sys.argv[1])
    head=f.readline(); d='|' if head.count('|')>head.count(',') else ','
    cols=[c.strip().strip('"').lower() for c in head.split(d)]
    def col(*cc):
        for c in cc:
            for i,x in enumerate(cols):
                if x==c: return i
        for c in cc:
            for i,x in enumerate(cols):
                if c in x: return i
        return None
    i_at,i_lei = col('action_taken'), col('lei')
    i_ir,i_rs = col('interest_rate'), col('rate_spread')
    i_cm,i_lp = col('construction_method'), col('loan_purpose')
    print(f"  action={i_at} lei={i_lei} rate={i_ir} spread={i_rs} constr={i_cm} purpose={i_lp}")

    P={}       # lei -> {'apps','den','rates':[],'spreads':[]}  (purchase)
    CM={'1':[0,0],'2':[0,0]}   # site-built / manufactured [apps,den]
    ML={}      # manufactured: lei->[apps,den]
    total=0
    for line in f:
        total+=1
        if total%500000==0: print(f"  ...{total:,}")
        p=line.rstrip('\n').split(d)
        if len(p)<=max(i_at,i_lei): continue
        at=p[i_at].strip().strip('"')
        if at not in ('1','2','3'): continue
        den=(at=='3'); lei=p[i_lei].strip().strip('"')
        # B: construction
        if i_cm is not None and len(p)>i_cm:
            cm=p[i_cm].strip().strip('"')
            if cm in CM:
                CM[cm][0]+=1
                if den: CM[cm][1]+=1
                if cm=='2':
                    a=ML.setdefault(lei,[0,0]); a[0]+=1
                    if den: a[1]+=1
        # A: pricing (purchase only)
        if i_lp is not None and len(p)>i_lp and p[i_lp].strip().strip('"')!='1': continue
        a=P.setdefault(lei,{'apps':0,'den':0,'rates':[],'spreads':[]})
        a['apps']+=1
        if den: a['den']+=1
        elif at=='1':
            if i_ir is not None and len(p)>i_ir:
                try: a['rates'].append(float(p[i_ir].strip().strip('"')))
                except: pass
            if i_rs is not None and len(p)>i_rs:
                try: a['spreads'].append(float(p[i_rs].strip().strip('"')))
                except: pass
    f.close()

    pricing=[]
    for lei,a in P.items():
        if a['apps']<500 or len(a['rates'])<200: continue
        pricing.append({"lei":lei,"purchase_apps":a['apps'],
            "denial_rate_pct":round(100*a['den']/a['apps'],1),
            "median_rate_pct":med(a['rates']),
            "median_spread_pct":med(a['spreads']),
            "originated":len(a['rates'])})
    pricing.sort(key=lambda r:-r['purchase_apps']); pricing=pricing[:60]

    mfg=[{"lei":k,"apps":v[0],"denial_rate_pct":round(100*v[1]/v[0],1)} for k,v in ML.items() if v[0]>=200]
    mfg.sort(key=lambda r:-r['apps']); mfg=mfg[:25]

    out={"method":"FHA 2025; decisioned (1,2,3); denial=3. Pricing: purchase-only, medians over ORIGINATED loans (rate_spread vs APOR), lenders n>=500 apps & 200 originated. Construction: method 1=site-built 2=manufactured; mfg lenders n>=200.",
         "construction_totals":{"site_built":{"apps":CM['1'][0],"denials":CM['1'][1],"denial_rate_pct":round(100*CM['1'][1]/max(CM['1'][0],1),1)},
                                 "manufactured":{"apps":CM['2'][0],"denials":CM['2'][1],"denial_rate_pct":round(100*CM['2'][1]/max(CM['2'][0],1),1)}},
         "manufactured_lenders":mfg,"lender_pricing":pricing}
    json.dump(out,open("tier5.json","w"),indent=1)
    sb,mf=out['construction_totals']['site_built'],out['construction_totals']['manufactured']
    print(f"\nOK -> tier5.json | pricing: {len(pricing)} lender, mfg lender: {len(mfg)}")
    print(f"SITE-BUILT: {sb['denial_rate_pct']}% (n={sb['apps']:,})  vs  MANUFACTURED: {mf['denial_rate_pct']}% (n={mf['apps']:,})")
    print("FIYAT ILK 5 (hacim):")
    for r in pricing[:5]: print(f"   {r['lei'][:10]}: red {r['denial_rate_pct']}% | medyan spread {r['median_spread_pct']} | faiz {r['median_rate_pct']}%")

if __name__=="__main__": main()
