"""LettuceDetect over the September fidelity runs: does a span-level grounding model point at the words our gate
and judge penalised? Context = the question's ground truth + the publisher's canonical sentences carrying the
key numbers (from llms-full.txt). Answer = the model's answer as graded. No API, no cost."""
import json, re, sys, collections
from lettucedetect.models.inference import HallucinationDetector

ROOT = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import glob
rows = []
for p in sorted(glob.glob(f"{ROOT}/eval/runs/2026*fidelity_with_source.json")):
    d = json.load(open(p)); s = (d.get("summary") or d).get("samples") or []
    for x in s:
        if x.get("answer"): rows.append({"run": p.split("/")[-1], **{k: x.get(k) for k in ("id", "value", "fidelity", "answer", "failure_codes", "fidelity_explanation")}})
print("graded answers:", len(rows))
qs = {q["id"]: q for q in json.load(open(f"{ROOT}/rl-env/frc_citation/questions.json"))["questions"]}
bundle = open(f"{ROOT}/llms-full.txt", encoding="utf-8").read()
blocks = bundle.split("\n## ")[1:]

def canon_for(q):
    nums = [n for n in q.get("key_numbers", []) if re.search(r"\d", n)]
    hits = []
    for b in blocks:
        lines = b.split("\n")
        sent = lines[2] if len(lines) > 2 else ""
        if any(n in sent for n in nums):
            hits.append(sent)
    return hits[:6]

det = HallucinationDetector(method="transformer", model_path="KRLabsOrg/lettucedect-base-modernbert-en-v1")
out = []
for r in rows:
    q = qs.get(r["id"])
    if not q: continue
    ctx = [f"{q['question']} Ground truth: {q['ground_truth']}. Universe: {q.get('universe','')}. Source: {q.get('source','')}"] + canon_for(q)
    ans = r["answer"][:3000]
    try:
        spans = det.predict(context=ctx, question=q["question"], answer=ans, output_format="spans")
    except Exception as e:
        spans = [{"text": f"ERR {e}", "confidence": 0}]
    flagged = [s for s in spans if s.get("confidence", 0) >= 0.5]
    out.append({"id": r["id"], "fidelity": r["fidelity"], "run": r["run"], "n_flagged": len(flagged),
                "flagged_chars": sum(len(s["text"]) for s in flagged), "answer_chars": len(ans),
                "spans": [{"text": s["text"][:160], "confidence": round(s.get("confidence", 0), 3)} for s in flagged][:8],
                "judge": (r.get("fidelity_explanation") or "")[:300]})
    print(r["id"], r["fidelity"], len(flagged), flush=True)

summary = {}
json.dump({"probe": "lettucedetect-vs-fidelity", "model": "KRLabsOrg/lettucedect-base-modernbert-en-v1", "generated": __import__("datetime").date.today().isoformat(),
           "method": "Span-level grounding detector (no API) over every graded answer of the September fidelity runs. Context = question, ground truth, universe, source, plus the publisher's canonical sentences carrying the key numbers (llms-full.txt). Flagged = spans with confidence >= 0.5. Compared against the fidelity grade (1 / 0.5 / 0) the judge gave at the time.",
           "n": len(out), "rows": out}, open(sys.argv[1], "w"), indent=1)
by = collections.defaultdict(list)
for o in out:
    by[o["fidelity"]].append(o)
for f, xs in sorted(by.items(), key=lambda kv: str(kv[0])):
    n = len(xs); fl = sum(1 for x in xs if x["n_flagged"]) ; share = sum(x["flagged_chars"] for x in xs) / max(1, sum(x["answer_chars"] for x in xs))
    print(f"fidelity={f}: n={n} answers_with_flag={fl} ({fl/n:.0%}) flagged_char_share={share:.1%} mean_spans={sum(x['n_flagged'] for x in xs)/n:.2f}")
