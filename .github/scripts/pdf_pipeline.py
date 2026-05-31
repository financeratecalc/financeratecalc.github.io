"""
FRC PDF Pipeline Bot — Step 1
Public overlay guideline PDFs → Claude analysis → overlay-intelligence.json update

Çalışır: GitHub Actions (haftalık veya manuel)
Yasal: Sadece public, non-login PDFs. Robots.txt tüm hedefler için OK.
"""

import os, json, requests, tempfile
from datetime import datetime

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# ─── HEDEF LENDER PDF KAYNAKLARI ─────────────────────────────────────────────
# Her kaynak için: URL, fallback (Google snippet), güven skoru
PDF_SOURCES = [
    {
        "lender_key": "PennyMac_Correspondent",
        "name": "PennyMac Correspondent",
        "pdf_urls": [
            "https://corr.pennymac.com/assets/documents/non-delegated-resources/non-delegated-government-overlay-matrix.pdf",
            "https://corr.pennymac.com/assets/documents/guides/government-pennymac-overlay-compilation.pdf",
        ],
        "google_fallback": True,
        "google_query": "PennyMac government overlay matrix FHA 2026 site:corr.pennymac.com"
    },
    {
        "lender_key": "UWM",
        "name": "United Wholesale Mortgage",
        "pdf_urls": [
            "https://www.uwm.com/content/dam/uwm/pdf/guides/fha-overlay-guide.pdf",
            "https://www.uwm.com/content/dam/uwm/pdf/underwriting/fha-guidelines.pdf",
        ],
        "google_fallback": True,
        "google_query": "UWM FHA overlay guidelines 2026 site:uwm.com filetype:pdf"
    },
    {
        "lender_key": "Freedom_Mortgage",
        "name": "Freedom Mortgage Wholesale",
        "pdf_urls": [
            "https://wholesale.freedommortgage.com/content/dam/freedom/pdf/guidelines/fha-overlay-matrix.pdf",
        ],
        "google_fallback": True,
        "google_query": "Freedom Mortgage wholesale FHA overlay matrix 2026 filetype:pdf"
    }
]

CLAUDE_EXTRACT_PROMPT = """You are an expert US Mortgage Underwriter analyzing a lender overlay document.

Extract ONLY these specific overlay rules from the text below. These are rules STRICTER than standard FHA/VA/Fannie Mae guidelines.

Return ONLY valid JSON, no markdown, no explanation:

{
  "fha": {
    "min_fico": <integer or null>,
    "max_dti": <integer percentage or null>,
    "reserves_months": <integer or null>,
    "condo_eligible": <boolean or null>,
    "manufactured_home_eligible": <boolean or null>,
    "key_restrictions": [<list of notable overlay rules as strings>]
  },
  "conventional": {
    "min_fico": <integer or null>,
    "max_dti": <integer percentage or null>,
    "reserves_months": <integer or null>
  },
  "va": {
    "min_fico": <integer or null>,
    "max_dti": <integer percentage or null>
  },
  "confidence": <float 0.0-1.0>,
  "notes": "<any important caveats>"
}

Text to analyze:
"""

def try_download_pdf(url):
    """Public PDF indirmeyi dene"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; FRCResearchBot/1.0; +https://financeratecalc.com)',
        'Accept': 'application/pdf,*/*',
    }
    try:
        r = requests.get(url, headers=headers, timeout=15, stream=True)
        if r.status_code == 200 and 'pdf' in r.headers.get('content-type', '').lower():
            return r.content
        return None
    except:
        return None

def extract_text_from_pdf(pdf_bytes):
    """PDF'den metin çıkar"""
    try:
        import pdfplumber, io
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = ""
            for page in pdf.pages[:20]:  # İlk 20 sayfa yeterli
                text += page.extract_text() or ""
        return text[:50000]  # Token limiti
    except Exception as e:
        return None

def analyze_with_claude(text, lender_name):
    """Claude API ile overlay kurallarını çıkar"""
    if not ANTHROPIC_API_KEY:
        return None
    
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1000,
                "messages": [{
                    "role": "user",
                    "content": CLAUDE_EXTRACT_PROMPT + f"\n\nLender: {lender_name}\n\n{text}"
                }]
            },
            timeout=30
        )
        
        if r.status_code == 200:
            response_text = r.json()['content'][0]['text']
            # JSON temizle
            response_text = response_text.strip()
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
            return json.loads(response_text)
    except Exception as e:
        print(f"Claude API error: {e}")
    return None

def run_pipeline():
    """Ana pipeline"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.join(script_dir, '..', '..')
    db_path = os.path.join(repo_root, 'overlay-intelligence.json')
    
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    results = {"processed": 0, "updated": 0, "failed": 0, "timestamp": datetime.now().isoformat()}
    
    for source in PDF_SOURCES:
        lender_key = source['lender_key']
        print(f"\n📄 Processing: {source['name']}")
        
        pdf_text = None
        
        # PDF indirmeyi dene
        for url in source.get('pdf_urls', []):
            print(f"   Trying: {url[:60]}...")
            pdf_bytes = try_download_pdf(url)
            if pdf_bytes:
                print(f"   ✅ Downloaded ({len(pdf_bytes)//1024}KB)")
                pdf_text = extract_text_from_pdf(pdf_bytes)
                if pdf_text:
                    print(f"   ✅ Extracted {len(pdf_text)} chars")
                    break
        
        if not pdf_text:
            print(f"   ⚠️ PDF not accessible — using existing data")
            results['failed'] += 1
            continue
        
        # Claude ile analiz et
        print(f"   🤖 Analyzing with Claude...")
        extracted = analyze_with_claude(pdf_text, source['name'])
        
        if extracted:
            # Veritabanını güncelle
            if lender_key in db['lenders']:
                # Sadece Claude'un bulduğu değerleri güncelle
                for loan_type in ['fha', 'conventional', 'va']:
                    if loan_type in extracted and loan_type in db['lenders'][lender_key]:
                        for key, val in extracted[loan_type].items():
                            if val is not None:
                                db['lenders'][lender_key][loan_type][key] = val
                                db['lenders'][lender_key]['confidence_score'] = extracted.get('confidence', 0.8)
                                db['lenders'][lender_key]['source_date'] = datetime.now().strftime('%Y-%m-%d')
                                db['lenders'][lender_key]['source'] = 'pdf_pipeline'
                
                print(f"   ✅ Updated {lender_key}")
                results['updated'] += 1
            else:
                print(f"   ⚠️ Lender {lender_key} not in database")
        else:
            print(f"   ❌ Claude extraction failed")
            results['failed'] += 1
        
        results['processed'] += 1
    
    # ML vaka sayısını güncelle
    db['last_updated'] = datetime.now().strftime('%Y-%m-%d')
    
    # Kaydet
    with open(db_path, 'w') as f:
        json.dump(db, f, indent=2)
    
    print(f"\n📊 Pipeline complete: {results}")
    return results

if __name__ == "__main__":
    run_pipeline()
