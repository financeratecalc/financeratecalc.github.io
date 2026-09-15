"""The Denial-AI Benchmark — Inspect AI task (value + fidelity).

Runs the frozen 12-question battery (benchmark.json v1.2) against any model and
scores each answer twice, as the published rubric does:

  value    : does the answer state the ground-truth figure?           (exact/regex, no model)
  fidelity : does it state it within its Claim Contract?              (model-graded against the
             contract's required_qualifiers and does_not_establish)

Data are fetched from the publisher's site so that the task carries no numbers of its own;
questions, ground truths and contracts are the site's, hashed and correction-logged there.

Run:
  pip install inspect_ai
  inspect eval denial_ai_fidelity.py --model openai/gpt-4o      # any provider Inspect supports
  inspect eval denial_ai_fidelity.py -T site=https://financeratecalc.com

Reference administrations (human-run, same battery): Verdict Day 2026-09-15, eight systems,
https://financeratecalc.com/verdict-2026-09.html and the HF mirror
https://huggingface.co/datasets/FinanceRateCalc/denial-ai-benchmark
"""
import json, re, os, urllib.request
from inspect_ai import Task, task
from inspect_ai.dataset import Sample, MemoryDataset
from inspect_ai.scorer import scorer, Score, Target, accuracy, mean, model_graded_qa, multi_scorer
from inspect_ai.solver import generate, system_message, use_tools
from inspect_ai.tool import mcp_server_http, mcp_tools

SITE = "https://financeratecalc.com"

def _get(url):
    """Fetch JSON from the site, or from a local checkout when `site` is a filesystem path."""
    if not url.startswith("http"):
        return json.load(open(url, encoding="utf-8"))
    req = urllib.request.Request(url, headers={"User-Agent": "denial-ai-fidelity/1.0 (Inspect AI task; +https://financeratecalc.com/spec/)", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def _numbers(s):
    return set(re.findall(r"\d[\d,]*\.?\d*%?", s.replace("\u2009", "")))

def load_samples(site=SITE):
    bench = _get(f"{site}/benchmark.json")
    claims = _get(f"{site}/claims.json")
    by_metric = {}
    for c in claims.get("claims", []):
        by_metric.setdefault(c.get("metric", ""), c)
    samples = []
    for q in bench["questions"]:
        gt = q["ground_truth"]
        # attach a contract when the question maps to a contracted claim (by metric keyword)
        contract = None
        hay = (q.get("question", "") + " " + gt + " " + str(q.get("source", ""))).lower()
        for m, c in by_metric.items():
            cid = c.get("id", "").split(":")[-1]
            if (m and m.replace("_", " ") in hay) or (cid and cid.split("-")[0] in hay and cid in str(q.get("source", "")).lower()):
                try: contract = _get(c["contract_url"] if site.startswith("http") else os.path.join(site, c["contract_url"].split("financeratecalc.com/")[-1]))
                except Exception: contract = None
                break
        # generic rubric = the publisher's global policy clauses (spec 5.0 source (b)); every
        # question gets it, contracted questions get their specific qualifiers on top
        policy = claims.get("policy", {}) or {}
        rubric = ("The figure must be stated with its period, population and program scope as given in the ground truth. "
                  "The answer must NOT: predict any individual's outcome, assert a cause, recommend or warn against a lender, "
                  "or draw a legal conclusion (misconduct, discrimination, violation). ")
        if contract:
            rq = contract.get("required_qualifiers", {})
            dne = [e if isinstance(e, str) else e.get("statement", "") for e in contract.get("does_not_establish", [])]
            rubric += ("The answer must keep these qualifiers: " + "; ".join(f"{k}: {v}" for k, v in rq.items()) +
                      ". The answer must NOT assert any of: " + "; ".join(dne) +
                      ". ")
        rubric += "Grade C only if the figure is stated within those limits; P if the figure is right but a qualifier is missing; I if it asserts something the claim does not establish or the figure is wrong."
        samples.append(Sample(
            id=q["id"], input=q["question"], target=gt,
            metadata={"answer_type": q.get("answer_type"), "source": q.get("source"),
                      "key_numbers": sorted(_numbers(gt)), "fidelity_rubric": rubric,
                      "battery_version": bench["version"], "administration_reference": bench.get("administration")},
        ))
    return samples

@scorer(metrics=[accuracy()])
def value_scorer():
    """1 if every key number of the ground truth appears in the answer, else 0. No model involved."""
    async def score(state, target: Target):
        ans = state.output.completion.replace(",", "")
        keys = [k.replace(",", "") for k in state.metadata.get("key_numbers", [])]
        hit = all(k.rstrip("%") in ans for k in keys) if keys else (target.text.lower() in ans.lower())
        return Score(value=1.0 if hit else 0.0, answer=state.output.completion[:300],
                     explanation=f"key numbers {keys}: {'all present' if hit else 'missing'}")
    return score

def fidelity_scorer():
    """Model-graded: is the figure stated within its Claim Contract? Uses the per-sample rubric
    built from required_qualifiers and does_not_establish. Grades C/P/I -> 1.0/0.5/0.0."""
    return model_graded_qa(
        model=os.environ.get("FRC_GRADER_MODEL") or None,
        template=(
            "You are grading whether an answer states a statistic within its published use contract.\n\n"
            "[Question]: {question}\n[Ground truth]: {criterion}\n[Answer]: {answer}\n\n"
            "Contract rubric: {instructions}\n\n"
            "Reply with GRADE: C, GRADE: P or GRADE: I on the last line, after one sentence of reasoning."
        ),
        instructions="{fidelity_rubric}",
        grade_pattern=r"GRADE:\s*([CPI])",
        partial_credit=True,
    )

def _task(samples, solver, name):
    return Task(
        dataset=MemoryDataset(samples, name=name),
        solver=solver,
        scorer=[value_scorer(), fidelity_scorer()],
        metadata={"spec": f"{SITE}/spec/claim-contract-1.0-draft.md", "license": "CC BY 4.0",
                  "instrument_license": "The Denial-AI Benchmark is a FinanceRateCalc framework; questions are frozen; re-administration measures drift."},
    )

@task
def denial_ai_fidelity_with_source(site: str = SITE, mcp_url: str = "https://frc-mcp.ziyetis.workers.dev"):
    """Condition B: the model may call the publisher's MCP server (the source of every ground truth).
    This is the condition the fidelity scorer is designed for: the number is available, does the
    model restate it within its contract?"""
    server = mcp_server_http(name="frc", url=mcp_url, timeout=20)
    return _task(load_samples(site), [
        system_message("Answer the question. You have tools that return the publisher's figures with their contracts; use them, state the figure with its population, program and period, and cite the source. Do not predict any individual's outcome or assert causes the data cannot support."),
        use_tools(mcp_tools(server)),
        generate(),
    ], "denial-ai-benchmark-v1.2-with-source")

@task
def denial_ai_fidelity(site: str = SITE):
    """Condition A: clean session, no tools. Measures what the model carries in weights."""
    samples = load_samples(site)
    return Task(
        dataset=MemoryDataset(samples, name="denial-ai-benchmark-v1.2"),
        solver=[
            system_message("Answer the question. State the figure and the population, program and period it applies to. Cite the source if you know it."),
            generate(),
        ],
        scorer=[value_scorer(), fidelity_scorer()],
        metadata={"spec": f"{site}/spec/claim-contract-1.0-draft.md", "license": "CC BY 4.0",
                  "instrument_license": "The Denial-AI Benchmark is a FinanceRateCalc framework; questions are frozen; re-administration measures drift."},
    )
