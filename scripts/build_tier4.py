#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FRC TIER-4 BUILDER — tek geciste iki katman:
  A) LENDER x EYALET: her eyalette en buyuk lender'lar + red oranlari (hucre n>=100)
  B) SEBEP PARMAK IZI: top lender'larin red-sebebi dagilimi (lender basina DTI/credit/collateral/... paylari)
KULLANIM: python build_tier4.py "C:\\Users\\ziyet\\Downloads\\year_2025_loan_types_2.csv"
CIKTI: tier4.json -> zip'le, Fable'a yukle. (Isimlendirme Fable'da - TS bende var.)
"""
import sys, json, io, zipfile

STATES = {'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC','PR'}
REASONS = {'1':'dti','2':'employment','3':'credit_history','4':'collateral','5':'insufficient_cash','6':'unverifiable_info','7':'incomplete','8':'mi_denied','9':'other','10':'other'}

def open_any(p):
    if p.lower().endswith('.zip'):
        z=zipfile.ZipFile(p); n=next(x for x in z.namelist() if x.lower().endswith(('.csv','.txt')))
        return io.TextIOWrapper(z.open(n),encoding='utf-8',errors='replace')
    return open(p,encoding='utf-8',errors='replace')

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
    i_at,i_st,i_lei=col('action_taken'),col('state_code','state'),col('lei')
    i_dr=[x for x in [col('denial_reason-1','denial_reason_1'),col('denial_reason-2','denial_reason_2'),col('denial_reason-3','denial_reason_3'),col('denial_reason-4','denial_reason_4')] if x is not None]
    print(f"  ayirac='{d}' action={i_at} state={i_st} lei={i_lei} reason={len(i_dr)}")

    ls={}   # (lei,st)->[apps,den]
    lr={}   # lei->[apps,den,{reason:count}]
    total=0
    for line in f:
        total+=1
        if total%500000==0: print(f"  ...{total:,}")
        p=line.rstrip('\n').split(d)
        if len(p)<=max(i_at,i_st,i_lei): continue
        at=p[i_at].strip().strip('"')
        if at not in ('1','2','3'): continue
        lei=p[i_lei].strip().strip('"'); st=p[i_st].strip().strip('"').upper()
        den=(at=='3')
        a=lr.setdefault(lei,[0,0,{}]); a[0]+=1
        if den:
            a[1]+=1
            for ix in i_dr:
                if ix<len(p):
                    r=p[ix].strip().strip('"')
                    if r in REASONS: a[2][REASONS[r]]=a[2].get(REASONS[r],0)+1
        if st in STATES:
            b=ls.setdefault((lei,st),[0,0]); b[0]+=1
            if den: b[1]+=1
    f.close()

    # A: eyalet basina hacim-lideri lender'lar (hucre n>=100), eyalet basi max 15
    by_state={}
    for (lei,st),(apps,den) in ls.items():
        if apps<100: continue
        by_state.setdefault(st,[]).append({"lei":lei,"apps":apps,"denials":den,"denial_rate_pct":round(100*den/apps,1)})
    for st in by_state:
        by_state[st].sort(key=lambda r:-r["apps"]); by_state[st]=by_state[st][:15]

    # B: top-100 hacimli lender'in sebep dagilimi
    fp=[]
    for lei,(apps,den,rs) in lr.items():
        if apps<500 or den<100: continue
        tot=sum(rs.values()) or 1
        fp.append({"lei":lei,"apps":apps,"denial_rate_pct":round(100*den/apps,1),
                   "reason_shares_pct":{k:round(100*v/tot,1) for k,v in sorted(rs.items(),key=lambda kv:-kv[1])}})
    fp.sort(key=lambda r:-r["apps"]); fp=fp[:100]

    out={"method":"FHA 2025 (loan_type 2); decisioned (1,2,3); denial=3. A: lender-state cells n>=100, top-15/state by volume. B: reason shares over all cited reasons (a denied file may cite multiple), lenders with >=500 apps & >=100 denials.",
         "lender_state":by_state,"reason_fingerprint":fp}
    json.dump(out,open("tier4.json","w"),indent=1)
    print(f"\nOK -> tier4.json | eyalet: {len(by_state)}, parmak-izi lender: {len(fp)}, satir: {total:,}")
    tx=by_state.get('TX',[])[:3]
    print("TX ilk 3 (LEI):", [(r['lei'][:10],r['denial_rate_pct']) for r in tx])

if __name__=="__main__": main()
