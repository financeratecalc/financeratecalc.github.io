#!/usr/bin/env python3
"""Rule discovery layer: watch the agencies, propose candidates, never decide.

Weekly. For each source page in SOURCES the page is fetched and compared with the stored
snapshot (eval/rule-sources/<id>.txt). Only text that changed, and only paragraphs that carry one
of the rule keywords, is sent to a model with one job: quote the sentence that states a dated
numeric constant and return it as structured JSON. The model reads; it does not write to any
rule table. Everything it proposes lands in rules/candidates.json with the exact quote, the
source URL, the fetch date and a sha256 of the page, and waits there for a human to read the
quote against the primary document and approve or reject it. Approval is a hand edit of a rule
file in rules/ plus rulecheck/constants.json; this script never touches either.

No model consensus, no reward, no autonomy. The model can be wrong; the quote is there so that
the reviewer sees it in seconds, and the reviewer's seconds are recorded (review_seconds) as
the one metric of whether this layer saves work.

Env: ANTHROPIC_API_KEY (missing -> candidates are not extracted; changed pages are still logged).
"""
import datetime, hashlib, html, json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = os.path.join(ROOT, "eval", "rule-sources")
OUT = os.path.join(ROOT, "rules", "candidates.json")

# Agency pages where the constants we track are announced. Edit here; nothing else is configured.
SOURCES = [
    {"id": "fhfa-news", "rule": "frc:rule:fhfa-conforming-loan-limits-2026", "url": "https://www.fhfa.gov/news", "expects": "conforming loan limit values (late November)"},
    {"id": "fhfa-cll", "rule": "frc:rule:fhfa-conforming-loan-limits-2026", "url": "https://www.fhfa.gov/data/conforming-loan-limit-cll-values", "expects": "baseline and ceiling"},
    {"id": "hud-press", "rule": "frc:rule:fha-forward-loan-limits-2026", "url": "https://www.hud.gov/news", "expects": "FHA loan limits press release (early December)"},
    {"id": "hud-mortgagee-letters", "rule": "frc:rule:fha-forward-loan-limits-2026", "url": "https://www.hud.gov/program_offices/administration/hudclips/letters/mortgagee", "expects": "Mortgagee Letter: loan limits, annual MIP"},
    {"id": "cfpb-newsroom", "rule": "frc:rule:cfpb-hoepa-qm-thresholds-2026", "url": "https://www.consumerfinance.gov/about-us/newsroom/", "expects": "annual threshold adjustments (HOEPA, QM points-and-fees, late December)"},
    {"id": "va-funding-fee", "rule": "frc:rule:va-funding-fee-2023-04-07", "url": "https://www.va.gov/housing-assistance/home-loans/funding-fee-and-closing-costs/", "expects": "funding fee table"},
]
KEYWORDS = re.compile(r"loan limit|conforming|ceiling|baseline|mortgage insurance premium|annual mip|funding fee|hoepa|points and fees|qualified mortgage|threshold|mortgagee letter", re.I)
MODEL = "claude-haiku-4-5-20251001"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "frc-rule-discovery/0.1 (+https://financeratecalc.com/rules/)"})
    raw = urllib.request.urlopen(req, timeout=40).read()
    return raw.decode("utf-8", errors="ignore")


def to_text(page):
    page = re.sub(r"<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", page, flags=re.S | re.I)
    page = re.sub(r"<br\s*/?>|</p>|</li>|</h\d>|</tr>|</div>", "\n", page, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", page))
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in text.split("\n")]
    return "\n".join(l for l in lines if l)


def changed_paragraphs(old, new):
    old_set = set(old.split("\n")) if old else set()
    return [l for l in new.split("\n") if l not in old_set and KEYWORDS.search(l) and re.search(r"\d", l)]


def extract(src, paragraphs, key):
    prompt = ("You are reading text that changed on a US agency web page. Find every sentence that states a dated numeric "
              "regulatory constant: a loan limit, a ceiling or floor, a mortgage insurance premium, a funding fee rate, a "
              "HOEPA or qualified-mortgage threshold. For each, return JSON with: quote (the exact sentence, verbatim), "
              "value (number only), unit (usd or pct), what (one line: which constant, for which year or effective date), "
              "effective (ISO date if stated, else null). Return a JSON array only. If there is none, return [].\n\n"
              f"Page: {src['url']}\nExpected content: {src['expects']}\n\nText:\n" + "\n".join(paragraphs)[:12000])
    body = {"model": MODEL, "max_tokens": 1500, "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    text = " ".join(b.get("text", "") for b in r.get("content", []) if b.get("type") == "text")
    m = re.search(r"\[.*\]", text, re.S)
    items = json.loads(m.group(0)) if m else []
    usage = r.get("usage", {})
    return [i for i in items if isinstance(i, dict) and i.get("quote")], usage


def main():
    os.makedirs(SNAP, exist_ok=True)
    today = datetime.date.today().isoformat()
    key = os.environ.get("ANTHROPIC_API_KEY")
    doc = json.load(open(OUT)) if os.path.exists(OUT) else {"note": "", "candidates": [], "runs": []}
    doc["note"] = ("Candidates proposed by the discovery layer (scripts/discover_rule_candidates.py). A model read the changed "
                   "text and quoted it; nothing here is a rule until a human reads the quote against the primary document and "
                   "moves it into rules/ with a source. status: pending | approved | rejected; review_seconds is the reviewer's own count.")
    run = {"date": today, "sources": [], "tokens": 0, "new_candidates": 0}
    existing = {(c["source_id"], c["quote"]) for c in doc["candidates"]}
    for src in SOURCES:
        rec = {"id": src["id"], "url": src["url"]}
        try:
            page = fetch(src["url"])
        except Exception as e:
            rec["error"] = str(e)[:200]; run["sources"].append(rec); print(src["id"], "ERROR", rec["error"]); continue
        text = to_text(page)
        snap_path = os.path.join(SNAP, src["id"] + ".txt")
        old = open(snap_path, encoding="utf-8").read() if os.path.exists(snap_path) else None
        paras = changed_paragraphs(old, text)
        rec.update({"sha256": hashlib.sha256(text.encode()).hexdigest()[:16], "changed_paragraphs": len(paras), "first_fetch": old is None})
        open(snap_path, "w", encoding="utf-8").write(text)
        if paras and key:
            try:
                items, usage = extract(src, paras, key)
                run["tokens"] += usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                for it in items:
                    k = (src["id"], it["quote"])
                    if k in existing:
                        continue
                    existing.add(k)
                    doc["candidates"].append({"id": f"cand:{today}:{hashlib.sha256((src['id'] + it['quote']).encode()).hexdigest()[:8]}",
                                              "found": today, "source_id": src["id"], "source_url": src["url"], "page_sha256": rec["sha256"],
                                              "rule": src["rule"], "quote": it["quote"], "value": it.get("value"), "unit": it.get("unit"),
                                              "what": it.get("what"), "effective": it.get("effective"), "status": "pending",
                                              "review_seconds": None, "reviewed": None, "decision_note": None})
                    run["new_candidates"] += 1
                rec["extracted"] = len(items)
            except Exception as e:
                rec["extract_error"] = str(e)[:200]
        elif paras and not key:
            rec["skipped"] = "ANTHROPIC_API_KEY not set; changed text logged only"
        run["sources"].append(rec)
        print(src["id"], rec)
    doc["runs"] = (doc["runs"] + [run])[-52:]
    doc["generated"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    json.dump(doc, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(f"candidates: {len(doc['candidates'])} total, {run['new_candidates']} new; tokens this run: {run['tokens']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
