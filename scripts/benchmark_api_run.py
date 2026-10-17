#!/usr/bin/env python3
"""Benchmark questions through provider APIs with web search turned on ("API condition").

NOT the consumer-product series: an API model with a search tool is not the ChatGPT / Gemini /
Grok / Claude app a reader uses, so these results are reported as their own series and never
averaged with the clean-session administrations. One fresh call per question, no system prompt,
no follow-up, single repeat. Raw answers are saved verbatim; grading is a separate step.

Env: OPENAI_API_KEY, GOOGLE_API_KEY, XAI_API_KEY, ANTHROPIC_API_KEY (any missing -> that system skipped).
Args: --questions q9,q12 (default all) --out eval/benchmark-2026-10-api.json
"""
import argparse, datetime, json, os, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def post(url, headers, body, timeout=180):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type": "application/json", **headers}, method="POST")
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read()[:400].decode(errors='ignore')}")


def get(url, headers):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30))


def pick(available, prefs):
    for p in prefs:
        for a in available:
            if a == p or a.startswith(p):
                return a
    return None


def openai_sys(k):
    ids = [m["id"] for m in get("https://api.openai.com/v1/models", {"Authorization": "Bearer " + k})["data"]]
    model = pick(ids, ["gpt-5-mini", "gpt-4.1-mini", "gpt-4o-mini"])
    def ask(q):
        last = None
        for tool in ("web_search", "web_search_preview"):
            try:
                r = post("https://api.openai.com/v1/responses", {"Authorization": "Bearer " + k}, {"model": model, "input": q, "tools": [{"type": tool}]})
                text = r.get("output_text") or " ".join(c.get("text", "") for o in r.get("output", []) if o.get("type") == "message" for c in o.get("content", []) if c.get("type") == "output_text")
                cites = [a.get("url") for o in r.get("output", []) if o.get("type") == "message" for c in o.get("content", []) for a in c.get("annotations", []) if a.get("url")]
                return {"text": text, "citations": cites, "tool": tool, "usage": r.get("usage")}
            except RuntimeError as e:
                last = e
        raise last
    return model, ask


def google_sys(k):
    ms = get("https://generativelanguage.googleapis.com/v1beta/models?key=" + k + "&pageSize=1000", {})["models"]
    ids = [m["name"].split("/")[-1] for m in ms if "generateContent" in (m.get("supportedGenerationMethods") or [])]
    # newest flash first; listed models can still be retired for new users, so fall through on 404
    flash = sorted([i for i in ids if "flash" in i and "lite" not in i and "image" not in i and "tts" not in i and "live" not in i], reverse=True)
    cands = [c for c in ["gemini-flash-latest"] if c in ids] + flash
    state = {"model": cands[0] if cands else None}
    def ask(q):
        last = None
        for m in [state["model"]] + [c for c in cands if c != state["model"]]:
            try:
                r = post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={k}", {}, {"contents": [{"parts": [{"text": q}]}], "tools": [{"google_search": {}}]})
                state["model"] = m; break
            except RuntimeError as e:
                last = e
                if "404" not in str(e): raise
        else:
            raise last
        cand = (r.get("candidates") or [{}])[0]
        text = " ".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
        cites = [c.get("web", {}).get("uri") for c in (cand.get("groundingMetadata") or {}).get("groundingChunks", []) if c.get("web")]
        titles = [c.get("web", {}).get("title") for c in (cand.get("groundingMetadata") or {}).get("groundingChunks", []) if c.get("web")]
        return {"text": text, "citations": cites, "citation_titles": titles, "usage": r.get("usageMetadata"), "model_used": state["model"]}
    return state["model"], ask


def xai_sys(k):
    ids = [m["id"] for m in get("https://api.x.ai/v1/models", {"Authorization": "Bearer " + k})["data"]]
    model = pick(ids, ["grok-4-fast", "grok-4", "grok-3-mini", "grok-3"])
    def ask(q):
        try:
            r = post("https://api.x.ai/v1/responses", {"Authorization": "Bearer " + k}, {"model": model, "input": q, "tools": [{"type": "web_search"}]})
            text = r.get("output_text") or " ".join(c.get("text", "") for o in r.get("output", []) if o.get("type") == "message" for c in o.get("content", []) if c.get("type") in ("output_text", "text"))
            cites = [a.get("url") for o in r.get("output", []) if o.get("type") == "message" for c in o.get("content", []) for a in (c.get("annotations") or []) if a.get("url")]
            return {"text": text, "citations": cites or r.get("citations"), "api": "responses", "usage": r.get("usage")}
        except RuntimeError:
            r = post("https://api.x.ai/v1/chat/completions", {"Authorization": "Bearer " + k}, {"model": model, "messages": [{"role": "user", "content": q}], "search_parameters": {"mode": "on", "return_citations": True}})
            return {"text": r["choices"][0]["message"]["content"], "citations": r.get("citations"), "api": "chat+search_parameters", "usage": r.get("usage")}
    return model, ask


def anthropic_sys(k):
    ids = [m["id"] for m in get("https://api.anthropic.com/v1/models?limit=100", {"x-api-key": k, "anthropic-version": "2023-06-01"})["data"]]
    model = pick(ids, ["claude-haiku-5-5", "claude-haiku-4-5", "claude-sonnet-4-5"])
    def ask(q):
        r = post("https://api.anthropic.com/v1/messages", {"x-api-key": k, "anthropic-version": "2023-06-01"},
                 {"model": model, "max_tokens": 1500, "messages": [{"role": "user", "content": q}], "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 4}]})
        text = " ".join(b.get("text", "") for b in r.get("content", []) if b.get("type") == "text")
        cites = [c.get("url") for b in r.get("content", []) if b.get("type") == "text" for c in (b.get("citations") or []) if c.get("url")]
        return {"text": text, "citations": cites, "usage": r.get("usage")}
    return model, ask


SYSTEMS = [("openai", "OPENAI_API_KEY", openai_sys), ("google", "GOOGLE_API_KEY", google_sys), ("xai", "XAI_API_KEY", xai_sys), ("anthropic", "ANTHROPIC_API_KEY", anthropic_sys)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="")
    ap.add_argument("--out", default="eval/benchmark-2026-10-api.json")
    ap.add_argument("--systems", default="", help="comma-separated subset; results merge into an existing --out file")
    a = ap.parse_args()
    qs = json.load(open(os.path.join(ROOT, "benchmark.json")))["questions"]
    if a.questions:
        want = a.questions.split(",")
        qs = [q for q in qs if q["id"] in want]
    out = {"administration": datetime.date.today().isoformat(), "condition": "api_with_web_search",
           "condition_note": "Provider APIs with their own web-search tool, one fresh call per question, no system prompt, single repeat. Not comparable with the clean-session consumer-product series; reported separately.",
           "questions": [q["id"] for q in qs], "systems": {}}
    path = os.path.join(ROOT, a.out)
    if a.systems and os.path.exists(path):
        prev = json.load(open(path))
        if prev.get("questions") == out["questions"]:
            out["systems"] = prev.get("systems", {})
    for name, env, make in SYSTEMS:
        if a.systems and name not in a.systems.split(","):
            continue
        k = os.environ.get(env)
        if not k:
            out["systems"][name] = {"skipped": f"{env} not set"}; continue
        try:
            model, ask = make(k)
        except Exception as e:
            out["systems"][name] = {"skipped": f"model list failed: {e}"[:300]}; continue
        if not model:
            out["systems"][name] = {"skipped": "no preferred model available"}; continue
        res = {"model": model, "answers": {}}
        for q in qs:
            t0 = time.time()
            try:
                r = ask(q["question"]); r["seconds"] = round(time.time() - t0, 1)
            except Exception as e:
                r = {"error": str(e)[:500]}
            res["answers"][q["id"]] = r
            print(name, model, q["id"], "ok" if "text" in r else "ERROR " + r.get("error", "")[:120], flush=True)
        out["systems"][name] = res
    json.dump(out, open(os.path.join(ROOT, a.out), "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
