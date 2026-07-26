#!/usr/bin/env python3
"""
FRC — REFERENCE IMPLEMENTATION  (DIAGNOSTIC ARTIFACT — read this first)

WHAT THIS IS
  The code that produced the figures published at financeratecalc.com.
  It is published so that when two results disagree, the disagreement can be traced
  line by line rather than left ambiguous between "an error here" and "a different
  reading there."

WHAT THIS IS NOT
  This is NOT the instrument for independent replication. Running a script written by
  the source establishes computational reproduction — that the same pipeline yields the
  same output — not independent replication, which requires an implementation written by
  someone else from the stated method.

  If you want to check these figures, write your own implementation from the written
  specification at https://financeratecalc.com/reconciliation.html and compare against
  the expected values listed there. A replication that starts from this file will be
  described as computational reproduction, not independent replication.

  If your implementation and this one disagree, that disagreement is worth reporting
  either way: press@financeratecalc.com. Results are published whether they match or not.

INPUT   CFPB HMDA 2025 national loan-level file (download from consumerfinance.gov,
        not from financeratecalc.com)
USAGE   python reference_implementation.py <path_to_hmda_csv>
LICENSE CC BY 4.0
"""
import csv, json, sys, os, statistics
from collections import defaultdict

if len(sys.argv) < 2:
    print("Kullanim: python rebuild_all.py <hmda_csv_yolu>"); sys.exit(1)
PATH = sys.argv[1]
OUT = os.path.join(os.path.dirname(os.path.abspath(PATH)), "frc_rebuild.json")

MIN_LENDER   = 1500   # lender tablosu icin minimum karar gormus basvuru
MIN_METRO    = 500    # metro yayini icin minimum
MIN_CELL_M   = 100    # metro x lender hucresi minimum
MIN_CELL_STD = 25     # standardizasyon hucresi minimum (altinda ulusal orana duser)
MIN_ADJ      = 500    # adjusted olculen lender minimum

with open(PATH,"r",encoding="utf-8",errors="ignore") as f:
    head=f.readline()
for sep in [",","|","\t",";"]:
    cols=[c.strip().strip('"').lower() for c in head.split(sep)]
    if len(cols)>8: break
def find(*names):
    for n in names:
        if n in cols: return cols.index(n)
    for i,c in enumerate(cols):
        for n in names:
            if n in c: return i
    return None
IX={"action":find("action_taken"),"ltype":find("loan_type"),"lei":find("lei","legal_entity_identifier"),
    "rev":find("reverse_mortgage"),"amount":find("loan_amount"),"income":find("income"),
    "state":find("state_code","state"),"dti":find("debt_to_income_ratio"),
    "cltv":find("combined_loan_to_value_ratio","loan_to_value_ratio"),
    "msa":find("derived_msa-md","derived_msa_md","msa_md","msa"),
    "d1":find("denial_reason-1","denial_reason_1"),"d2":find("denial_reason-2","denial_reason_2"),"d3":find("denial_reason-3","denial_reason_3"),"d4":find("denial_reason-4","denial_reason_4")}
print("  kolonlar:", {k:v for k,v in IX.items()})
# MSA kolonu dogrulamasi
if IX["msa"] is not None:
    _chk=[]
    with open(PATH,"r",encoding="utf-8",errors="ignore") as _f:
        _rd=csv.reader(_f,delimiter=sep); next(_rd,None)
        for _i,_r in enumerate(_rd):
            if _i>3000: break
            try:
                _v=_r[IX["msa"]].strip()
                if _v and _v!="99999": _chk.append(len(_v))
            except: pass
    if _chk:
        _mode=max(set(_chk),key=_chk.count)
        print(f"  MSA kolonu kontrol: en sik uzunluk {_mode} hane ({cols[IX['msa']]})")
        if _mode!=5:
            print("  !! UYARI: MSA kodlari 5 haneli degil — yanlis kolon secilmis olabilir, metro katmani atlanacak")
            IX["msa"]=None

REASON={"1":"dti","2":"employment","3":"credit_history","4":"collateral","5":"insufficient_cash",
        "6":"unverifiable_info","7":"incomplete","8":"mortgage_insurance_denied","9":"other","10":"other"}

def b_amount(v):
    try: a=float(v)
    except: return None
    if a<100000: return "u100"
    if a<150000: return "100-150"
    if a<200000: return "150-200"
    if a<250000: return "200-250"
    if a<350000: return "250-350"
    if a<500000: return "350-500"
    return "500p"
def b_income(v):
    try: a=float(v)
    except: return None
    if a<40: return "u40"
    if a<60: return "40-60"
    if a<80: return "60-80"
    if a<120: return "80-120"
    if a<200: return "120-200"
    return "200p"
def b_dti(v):
    if v is None: return None
    s=str(v).strip()
    if not s: return None
    try:
        f=float(s)
        if f<36: return "u36"
        if f<43: return "36-43"
        if f<50: return "43-50"
        return "50p"
    except:
        s=s.replace("%","")
        if "<20" in s or "20%-<30" in s or "30%-<36" in s: return "u36"
        if "36" in s and "43" not in s: return "36-43"
        if "43" in s: return "43-50"
        if "50" in s or ">60" in s: return "50p"
        return None
def b_cltv(v):
    try: a=float(v)
    except: return None
    if a<=80: return "u80"
    if a<=90: return "80-90"
    if a<=95: return "90-95"
    if a<=96.5: return "95-96.5"
    return "96.5p"

lend_t=defaultdict(int); lend_d=defaultdict(int)
reason_c=defaultdict(lambda: defaultdict(int)); reason_tot=defaultdict(int)
st_t=defaultdict(int); st_d=defaultdict(int)
st_small_t=defaultdict(int); st_small_d=defaultdict(int)
st_big_t=defaultdict(int); st_big_d=defaultdict(int)
metro_t=defaultdict(int); metro_d=defaultdict(int)
metro_small_t=defaultdict(int); metro_small_d=defaultdict(int)
metro_big_t=defaultdict(int); metro_big_d=defaultdict(int)
mcell_t=defaultdict(int); mcell_d=defaultdict(int)
cell_t=defaultdict(int); cell_d=defaultdict(int)
adj_t=defaultdict(int); adj_d=defaultdict(int)
rows_cell=[]
national_t=0; national_d=0; hecm_skipped=0
n=0

with open(PATH,"r",encoding="utf-8",errors="ignore") as f:
    rd=csv.reader(f,delimiter=sep); next(rd,None)
    for r in rd:
        n+=1
        if n%400000==0: print(f"  {n:,} satir...")
        try:
            if IX["ltype"] is not None and r[IX["ltype"]].strip()!="2": continue
            a=r[IX["action"]].strip()
            if a not in ("1","2","3"): continue
            # *** DUZELTME: HECM disla ***
            if IX["rev"] is not None and r[IX["rev"]].strip()=="1":
                hecm_skipped+=1; continue
            lei=r[IX["lei"]].strip()
            if not lei: continue
            den = 1 if a=="3" else 0
            national_t+=1; national_d+=den
            lend_t[lei]+=1; lend_d[lei]+=den
            if den:
                reason_tot[lei]+=1
                seen=set()
                for k in ("d1","d2","d3","d4"):
                    if IX[k] is None: continue
                    v=r[IX[k]].strip()
                    if v and v in REASON and REASON[v] not in seen:
                        reason_c[lei][REASON[v]]+=1; seen.add(REASON[v])
            st=r[IX["state"]].strip() if IX["state"] is not None else ""
            if st in ("NA","","na","N/A"): st=""
            am_raw=r[IX["amount"]] if IX["amount"] is not None else ""
            try: amt=float(am_raw)
            except: amt=None
            if st:
                st_t[st]+=1; st_d[st]+=den
                if amt is not None:
                    if amt<150000: st_small_t[st]+=1; st_small_d[st]+=den
                    elif amt>=250000: st_big_t[st]+=1; st_big_d[st]+=den
            msa=r[IX["msa"]].strip() if IX["msa"] is not None else ""
            if msa and msa!="99999":
                metro_t[msa]+=1; metro_d[msa]+=den
                mcell_t[(msa,lei)]+=1; mcell_d[(msa,lei)]+=den
                if amt is not None:
                    if amt<150000: metro_small_t[msa]+=1; metro_small_d[msa]+=den
                    elif amt>=250000: metro_big_t[msa]+=1; metro_big_d[msa]+=den
            am=b_amount(am_raw); inc=b_income(r[IX["income"]]) if IX["income"] is not None else None
            dt=b_dti(r[IX["dti"]]) if IX["dti"] is not None else None
            lv=b_cltv(r[IX["cltv"]]) if IX["cltv"] is not None else None
            if st and am and inc and dt and lv:
                key=(st,am,inc,dt,lv)
                cell_t[key]+=1; cell_d[key]+=den
                rows_cell.append((lei,key))
                adj_t[lei]+=1; adj_d[lei]+=den   # adjusted icin AYNI alt kume
        except Exception:
            continue

print(f"\n  HECM cikarilan: {hecm_skipped:,}")
print(f"  YENI EVREN: {national_t:,}  red: {national_d:,}  ULUSAL ORAN: {100*national_d/national_t:.2f}%")

# --- lender ---
lenders=[]
for lei,t in lend_t.items():
    if t<MIN_LENDER: continue
    lenders.append({"lei":lei,"apps":t,"denials":lend_d[lei],"rate":round(100*lend_d[lei]/t,1)})
lenders.sort(key=lambda x:-x["apps"])
top100=lenders[:100]
print(f"  lender (>= {MIN_LENDER}): {len(lenders)} | top100 makas: "
      f"{min(x['rate'] for x in top100):.1f}% - {max(x['rate'] for x in top100):.1f}%")

# --- reason fingerprints (top100) ---
fps=[]
for x in top100:
    lei=x["lei"]; tot=reason_tot.get(lei,0)
    if tot<50: continue
    shares={k:round(100*v/tot,1) for k,v in reason_c[lei].items()}
    fps.append({"lei":lei,"apps":x["apps"],"denial_rate_pct":x["rate"],"reason_shares_pct":shares})
inc_med=statistics.median([f["reason_shares_pct"].get("incomplete",0) for f in fps]) if fps else 0
print(f"  reason fingerprints: {len(fps)} | incomplete medyan: {inc_med:.1f}%")

# --- state ---
states=[]
for s,t in st_t.items():
    if t<200: continue
    sm = round(100*st_small_d[s]/st_small_t[s],1) if st_small_t[s]>=100 else None
    bg = round(100*st_big_d[s]/st_big_t[s],1) if st_big_t[s]>=100 else None
    states.append({"state":s,"apps":t,"denials":st_d[s],"denial_rate_pct":round(100*st_d[s]/t,1),
                   "small_loan_denial_pct":sm,"big_loan_denial_pct":bg})
states.sort(key=lambda x:-x["apps"])
print(f"  state: {len(states)}")

# --- metro ---
mc=defaultdict(list)
for (msa,lei),t in mcell_t.items():
    if t>=MIN_CELL_M: mc[msa].append({"lei":lei,"apps":t,"denial_rate_pct":round(100*mcell_d[(msa,lei)]/t,1)})
metros=[]
for m,t in metro_t.items():
    if t<MIN_METRO: continue
    sm = round(100*metro_small_d[m]/metro_small_t[m],1) if metro_small_t[m]>=100 else None
    bg = round(100*metro_big_d[m]/metro_big_t[m],1) if metro_big_t[m]>=100 else None
    L=sorted(mc.get(m,[]),key=lambda x:-x["apps"])[:5]
    metros.append({"msa":m,"apps":t,"denials":metro_d[m],"denial_rate_pct":round(100*metro_d[m]/t,1),
                   "small_denial_pct":sm,"big_denial_pct":bg,"top_lenders":L})
metros.sort(key=lambda x:-x["apps"])
print(f"  metro: {len(metros)}")

# --- adjusted ---
GLOBAL=national_d/max(1,national_t)
cell_rate={}
for k,t in cell_t.items():
    cell_rate[k]=(cell_d[k]/t) if t>=MIN_CELL_STD else GLOBAL
exp=defaultdict(float)
for lei,key in rows_cell:
    exp[lei]+=cell_rate.get(key,GLOBAL)
adjusted=[]
for lei,t in adj_t.items():
    if t<MIN_ADJ: continue
    e=exp.get(lei,0)
    if e<=0: continue
    o=adj_d[lei]
    # kapsama: bu lender'in kac basvurusu tam profilli
    cov=round(100*t/lend_t[lei],1) if lend_t[lei] else 0
    if cov<50: continue   # profil kapsami dusukse adjusted yayinlanmaz
    adjusted.append({"lei":lei,"apps_in_cells":t,"apps_total":lend_t[lei],"profile_coverage_pct":cov,
                     "observed_denials":o,"observed_rate_pct":round(100*o/t,1),
                     "expected_denials":round(e,1),"expected_rate_pct":round(100*e/t,1),
                     "adjusted_ratio":round(o/e,2)})
adjusted.sort(key=lambda x:-x["apps_in_cells"])
if adjusted:
    _a=sorted(adjusted,key=lambda x:x["adjusted_ratio"])
    print(f"  adjusted: {len(adjusted)} lender | hucre: {len(cell_t):,} | oran araligi: {_a[0]['adjusted_ratio']} - {_a[-1]['adjusted_ratio']}")
    print(f"  beklenen oran araligi: {min(x['expected_rate_pct'] for x in adjusted)}% - {max(x['expected_rate_pct'] for x in adjusted)}%")
    print(f"  medyan profil kapsami: {statistics.median([x['profile_coverage_pct'] for x in adjusted])}%")

json.dump({
 "method":("CFPB HMDA 2025; FHA loan_type=2; decisioned = action_taken 1,2,3; denial = action 3. "
           "REVERSE MORTGAGE (HECM) RECORDS EXCLUDED following independent methodology review. "
           "Purchased loans (action 6), withdrawals (4), incomplete closures (5) and preapproval track (7,8) excluded. "
           f"Standardization cells: state x amount x income x DTI x CLTV; cells with n<{MIN_CELL_STD} fall back to national rate."),
 "national":{"apps":national_t,"denials":national_d,"rate_pct":round(100*national_d/national_t,2),
             "hecm_excluded":hecm_skipped},
 "lenders":lenders,"fingerprints":fps,"states":states,"metros":metros,"adjusted":adjusted
}, open(OUT,"w"))
print(f"\nBITTI -> {OUT}  ({os.path.getsize(OUT)/1024/1024:.1f} MB)  ZIP'le ve yukle")
