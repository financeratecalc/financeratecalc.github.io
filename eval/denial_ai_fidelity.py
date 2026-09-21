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
from inspect_ai.scorer import scorer, Score, Target, accuracy, mean
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
        rubric += ("Grade C only if the figure is stated within those limits; P if the figure is right but a qualifier is missing; "
                   "I if it asserts something the claim does not establish or the figure is wrong. "
                   "If the answer declines to give a figure and invents nothing, grade A (abstain): not a fidelity failure, but not a correct answer either.")
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

FAILURE_CODES = {
    "SCOPE_MISSING": "states the figure without its population/program/period",
    "SCOPE_WRONG": "applies the figure to a wider or different population than the claim covers",
    "INFERRED_NOT_SOURCED": "estimates a figure the source publishes exactly",
    "ATTRIBUTION_DRIFT": "attributes something to a named source that the source does not publish. Use ONLY when the answer names a source (FinanceRateCalc, HMDA, a lender, a study) and hangs a figure or finding on it that the source does not contain. If the answer cites no source at all, this code does not apply.",
    "UNCITED_COUNTERCLAIM": "asserts, with no source, something the federal record contradicts (for example that small loans are denied less often, or that credit history rather than debt-to-income is the leading cited reason). Confident, unsourced, and wrong.",
    "UNSOURCED_ASSERTION": "states a figure or finding with no source where the question asked for a sourced one, without contradicting the record",
    "FABRICATED_SUPPORT": "supplies a supporting number that exists nowhere: not in the named source, not in any published record the answer could have drawn on (a count, a sample size, a rank invented to make the answer look sourced)",
    "OVERREACH_FROM_SOURCE": "presents, as the source's finding, data that the source's tool output did contain but did not contract (raw context fields, provisional or externally-cited blocks): not invented, but promoted beyond what the source stands behind",
    "FABRICATED_RECEIPT": "writes a claim receipt (⟦FRC:…⟧) that the tool did not return — a receipt-shaped string invented to satisfy a citation rule; verifiable receipts end in an 8-hex hash returned by the tool",
    "STALE_VALUE": "uses a value the source has since corrected",
    "CAUSAL_LEAK": "turns an association into a cause",
    "INDIVIDUAL_LEAK": "turns an institutional aggregate into an individual prediction",
    "RECOMMENDATION_LEAK": "turns a statistic into advice about where to apply",
}

@scorer(metrics=[mean()])
def fidelity_scorer():
    """Model-graded against the per-sample contract rubric. Grades: C=1.0, P=0.5, I=0.0;
    A (abstain: declined without inventing) is recorded in metadata and scored 0.0 here so that
    the summary can exclude it; the summariser reports abstentions separately."""
    from inspect_ai.model import get_model
    async def score(state, target: Target):
        grader = get_model(os.environ.get("FRC_GRADER_MODEL") or None)
        tool_out = ""
        try:
            parts = []
            for msg in state.messages:
                if getattr(msg, "role", "") == "tool":
                    c = msg.content if isinstance(msg.content, str) else " ".join(getattr(x, "text", "") for x in (msg.content or []))
                    parts.append(c[:2500])
            tool_out = "\n---\n".join(parts)[-6000:]
        except Exception:
            tool_out = ""
        prompt = ("You are grading whether an answer states a statistic within its published use contract.\n\n"
                  + (f"[What the source's tools actually returned to the model]:\n{tool_out}\n\n" if tool_out else "[The model had no tool output; anything it attributes to a source came from memory]\n\n")
                  + "Distinguish three things: FABRICATED_SUPPORT is a number that appears nowhere in the tool output; OVERREACH_FROM_SOURCE is a number that IS in the tool output but was not part of the contracted sentence (raw context fields) and is presented as the source's finding; ATTRIBUTION_DRIFT is hanging on a named source something it does not say.\n\n"
                  f"[Question]: {state.input_text}\n[Ground truth]: {target.text}\n[Answer]: {state.output.completion}\n\n"
                  f"Contract rubric: {state.metadata.get('fidelity_rubric','')}\n\n"
                  "Failure codes, assign only what the answer actually does: " + "; ".join(f"{k} = {v}" for k, v in FAILURE_CODES.items()) + "\n\n"
                  "Abstention has two grades. GRADE: A is a clean refusal: no figure, no explanation of why the pattern would go one way or another, CODES: NONE. "
                  "GRADE: N is an abstention that still leaks: it declines to give the figure but narrates a mechanism, a direction, or a cause; give it the codes it earns. "
                  "Naming a source is required before ATTRIBUTION_DRIFT.\n\n"
                  "Reply with one sentence of reasoning, then a line CODES: comma-separated failure codes (or NONE), "
                  "then on the last line exactly one of: GRADE: C, GRADE: P, GRADE: I, GRADE: A, GRADE: N")
        out = await grader.generate(prompt)
        m = re.search(r"GRADE:\s*([CPIAN])", out.completion or "")
        g = m.group(1) if m else "I"
        cm = re.search(r"CODES:\s*([A-Z_, ]+)", out.completion or "")
        codes = [c.strip() for c in (cm.group(1) if cm else "").split(",") if c.strip() and c.strip() != "NONE"]
        codes = [] if g == "A" else codes
        return Score(value={"C": 1.0, "P": 0.5, "I": 0.0, "A": 0.0, "N": 0.0}[g], answer=g,
                     explanation=(out.completion or "")[:500],
                     metadata={"grade": g, "abstain": g in ("A", "N"), "leaky_abstain": g == "N", "failure_codes": [c for c in codes if c in FAILURE_CODES]})
    return score

def _task(samples, solver, name):
    return Task(
        dataset=MemoryDataset(samples, name=name),
        solver=solver,
        scorer=[value_scorer(), fidelity_scorer()] + ([fidelity_scorer_b()] if os.environ.get("FRC_GRADER_B_MODEL") else []),
        metadata={"spec": f"{SITE}/spec/claim-contract-1.0-draft.md", "license": "CC BY 4.0",
                  "instrument_license": "The Denial-AI Benchmark is a FinanceRateCalc framework; questions are frozen; re-administration measures drift."},
    )

@scorer(metrics=[mean()])
def fidelity_scorer_b():
    """Second grader (FRC_GRADER_B_MODEL). Same rubric, different model, so that grader
    disagreement is measured and published rather than assumed away."""
    base = fidelity_scorer()
    async def score(state, target: Target):
        prev = os.environ.get("FRC_GRADER_MODEL")
        os.environ["FRC_GRADER_MODEL"] = os.environ.get("FRC_GRADER_B_MODEL") or prev or ""
        try:
            return await base(state, target)
        finally:
            if prev is not None: os.environ["FRC_GRADER_MODEL"] = prev

    return score

@task
def denial_ai_fidelity_web(site: str = SITE, mcp_url: str = ""):
    """Condition B: the model may search the web. Measures what a real answer engine does:
    can it find the source, and does it restate the figure within its contract?"""
    from inspect_ai.tool import web_search
    return _task(load_samples(site), [
        system_message("Answer the question. Search the web if you need to. State the figure with its population, program and period, and cite your sources."),
        use_tools(web_search()),
        generate(),
    ], "denial-ai-benchmark-v1.3-web")

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
def denial_ai_fidelity(site: str = SITE, mcp_url: str = ""):
    """Condition A: clean session, no tools. Measures what the model carries in weights."""
    samples = load_samples(site)
    return Task(
        dataset=MemoryDataset(samples, name="denial-ai-benchmark-v1.2"),
        solver=[
            system_message("Answer the question. State the figure and the population, program and period it applies to. Cite the source if you know it."),
            generate(),
        ],
        scorer=[value_scorer(), fidelity_scorer()] + ([fidelity_scorer_b()] if os.environ.get("FRC_GRADER_B_MODEL") else []),
        metadata={"spec": f"{site}/spec/claim-contract-1.0-draft.md", "license": "CC BY 4.0",
                  "instrument_license": "The Denial-AI Benchmark is a FinanceRateCalc framework; questions are frozen; re-administration measures drift."},
    )


# ---------------------------------------------------------------------------
# The Cliche Index: what models believe vs what the record shows
# ---------------------------------------------------------------------------
@scorer(metrics=[mean()])
def cliche_scorer():
    """1.0 if the model's stance matches the record's verdict; 0.5 if the model says it cannot be
    determined and the record says UNTESTABLE (calibrated abstention); 0.0 otherwise.
    Stance is parsed from a required final line: STANCE: TRUE | FALSE | PARTLY | CANNOT_TELL."""
    async def score(state, target: Target):
        txt = state.output.completion or ""
        m = re.search(r"STANCE:\s*(TRUE_BUT_NOT_FROM_DATA|UNSUPPORTED_BY_DATA|CANNOT_TELL|TRUE|FALSE|PARTLY)", txt.upper())
        stance = m.group(1) if m else "NONE"
        v = state.metadata.get("verdict")
        ok = {"SUPPORTED": {"TRUE"}, "CONTRADICTED": {"FALSE"}, "PARTLY": {"PARTLY"},
              "NOT_IN_RECORD": {"CANNOT_TELL", "TRUE_BUT_NOT_FROM_DATA", "UNSUPPORTED_BY_DATA"},
              "NOT_KNOWABLE_FROM_DATA": {"CANNOT_TELL", "UNSUPPORTED_BY_DATA"}}[v]
        val = 1.0 if stance in ok else (0.5 if (v == "NOT_IN_RECORD" and stance == "PARTLY") else 0.0)
        confident_wrong = (v == "CONTRADICTED" and stance == "TRUE") or (v == "SUPPORTED" and stance == "FALSE")
        # asserting, as plain TRUE/FALSE, something no data can settle
        asserted_unknowable = v == "NOT_KNOWABLE_FROM_DATA" and stance in ("TRUE", "FALSE")
        return Score(value=val, answer=stance, explanation=txt[-300:],
                     metadata={"verdict": v, "stance": stance, "confident_wrong": confident_wrong,
                               "asserted_unknowable": asserted_unknowable,
                               "asserted_not_in_record": v == "NOT_IN_RECORD" and stance in ("TRUE", "FALSE")})
    return score

def load_cliche_samples(site=SITE):
    b = _get(f"{site}/eval/cliche-battery.json") if site.startswith("http") else json.load(open(os.path.join(site, "eval/cliche-battery.json")))
    return [Sample(id=c["id"], input=f"Is the following statement about FHA mortgage lending in the United States true?\n\n\"{c['claim']}\"\n\nExplain briefly, then end with exactly one line: STANCE: TRUE | STANCE: FALSE | STANCE: PARTLY | STANCE: TRUE_BUT_NOT_FROM_DATA (true as a rule or convention, but not something lending records show) | STANCE: UNSUPPORTED_BY_DATA (the claim cannot be established from data either way) | STANCE: CANNOT_TELL.",
                   target=c["verdict"], metadata={"verdict": c["verdict"], "evidence": c["evidence"], "universe": c["universe"]}) for c in b["claims"]]

@task
def cliche_index(site: str = SITE, mcp_url: str = ""):
    """Condition A only, by design: the point is what the model carries, not what it can look up."""
    return Task(dataset=MemoryDataset(load_cliche_samples(site), name="cliche-index-v0.1"),
                solver=[system_message("Answer from what you know. Do not search."), generate()],
                scorer=[cliche_scorer()],
                metadata={"battery": f"{SITE}/eval/cliche-battery.json", "license": "CC BY 4.0"})


@task
def denial_ai_fidelity_with_receipts(site: str = SITE, mcp_url: str = "https://frc-mcp.ziyetis.workers.dev"):
    """Condition D: source connected AND the client honours the receipt convention. The tool results are
    unchanged from C; only the client's instruction differs: figures are to be written with the claim
    receipt returned in the tool result (structured field `claim_receipt` / `figure_with_receipt`).
    Measures what a receipt-aware client would carry, as opposed to C which measures a naive one."""
    server = mcp_server_http(name="frc", url=mcp_url, timeout=20)
    return _task(load_samples(site), [
        system_message("Answer the question using the tools. Every FinanceRateCalc figure you state must be written together with its claim receipt, exactly as returned in the tool result's `figure_with_receipt` field (for example: 22.1% \u27e6FRC:national-fha-denial-rate-2025:22.1%:ebf6b00b\u27e7). The receipt is part of the figure; a figure without its receipt is unverifiable. State the population, program and period. Do not predict any individual's outcome, assert causes the data cannot support, or recommend a lender."),
        use_tools(mcp_tools(server)),
        generate(),
    ], "denial-ai-benchmark-v1.3-with-receipts")
