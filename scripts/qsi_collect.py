#!/usr/bin/env python3
"""Ask the QSI instrument's three questions to answer engines that expose an API with web search, and archive the
answers verbatim in eval/answer-engine-log/<date>-<engine>.json for scripts/qualifier_survival.py to grade.

Engines (each skipped when its key is absent; nothing is retried on error, the failure is archived):
  perplexity  PERPLEXITY_API_KEY   model sonar-pro        ~ $0.005-0.02 per question
  openai      OPENAI_API_KEY       gpt-4o-mini + web_search_preview   ~ $0.03 per question (search tool fee)
  gemini      GEMINI_API_KEY       gemini-2.5-flash + google_search grounding   free tier

One run = 3 questions x (up to) 3 engines, well under $1. The questions are sent as one message per question, in
English, with no system prompt and no mention of this site, so the engines find it (or not) on their own.
"""
import datetime as dt
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "eval", "answer-engine-log")
QUESTIONS = ["What was the FHA denial rate in the US in 2025, and what is the denominator?",
             "Which lenders had the highest FHA denial rates in 2025?",
             "What is AmeriSave Mortgage's FHA denial rate in 2025?"]
SUFFIX = " Please give the sources you used (links) and the exact denominator you are using."


def post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def perplexity(q, key):
    j = post("https://api.perplexity.ai/chat/completions", {"model": "sonar-pro", "messages": [{"role": "user", "content": q + SUFFIX}]}, {"Authorization": "Bearer " + key})
    return j["choices"][0]["message"]["content"], j.get("citations") or j.get("search_results") or []


def openai(q, key):
    j = post("https://api.openai.com/v1/responses", {"model": "gpt-4o-mini", "tools": [{"type": "web_search_preview"}], "input": q + SUFFIX}, {"Authorization": "Bearer " + key})
    text, cites = "", []
    for item in j.get("output", []):
        for c in item.get("content", []) or []:
            if c.get("type") == "output_text":
                text += c.get("text", "")
                cites += [a.get("url") for a in c.get("annotations", []) if a.get("url")]
    return text, cites


def gemini(q, key):
    j = post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}",
             {"contents": [{"parts": [{"text": q + SUFFIX}]}], "tools": [{"google_search": {}}]}, {})
    cand = (j.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
    gm = cand.get("groundingMetadata", {}) or {}
    cites = [c.get("web", {}).get("uri") for c in gm.get("groundingChunks", []) if c.get("web", {}).get("uri")]
    return text, cites


ENGINES = {"perplexity": ("PERPLEXITY_API_KEY", perplexity, "Perplexity sonar-pro (API)"),
           "openai": ("OPENAI_API_KEY", openai, "ChatGPT gpt-4o-mini + web search (API)"),
           "gemini": ("GEMINI_API_KEY", gemini, "Gemini 2.5 Flash + Google Search grounding (API)")}


def main():
    day = dt.date.today().isoformat()
    os.makedirs(LOG, exist_ok=True)
    ran = 0
    for name, (envk, fn, label) in ENGINES.items():
        key = os.environ.get(envk)
        if not key:
            print(f"{name}: no {envk}, skipped"); continue
        rec = {"engine": label, "date": day, "asked_by": "scripts/qsi_collect.py (API, no system prompt, one question per request)", "questions": [], "answer_text": ""}
        for q in QUESTIONS:
            try:
                text, cites = fn(q, key)
                rec["questions"].append({"q": q, "sources": [c for c in cites if isinstance(c, str)], "answer": text})
                rec["answer_text"] += f"Q: {q}\n{text}\n\n"
            except Exception as e:  # archived, never retried: a failure is a result
                rec["questions"].append({"q": q, "sources": [], "error": str(e)[:300]})
                rec["answer_text"] += f"Q: {q}\n[error: {str(e)[:120]}]\n\n"
        json.dump(rec, open(os.path.join(LOG, f"{day}-{name}.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(f"{name}: archived {len(rec['questions'])} answers"); ran += 1
    print(f"engines run: {ran}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
