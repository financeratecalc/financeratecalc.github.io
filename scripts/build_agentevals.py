#!/usr/bin/env python3
"""Export the citation-decision fixtures as an agentevals EVAL.yaml (https://agentevals.pages.dev, spec 1.0).

One test per fixture question: input = the question (with the publisher's evidence instructions as the system
message), expected_output = the genuine receipted sentence, rubrics = the contract in words, and a code_judge
(judges/receipt_fidelity.py) that scores the agent's answer deterministically: receipt present and verifying,
figure present, period/program kept, no forbidden framing. No model in the judge. Output: evals/agentevals/EVAL.yaml.

    python3 scripts/build_agentevals.py
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "fixtures", "citation-decision", "fixtures.json")
OUT = os.path.join(ROOT, "evals", "agentevals", "EVAL.yaml")

SYSTEM = ("You answer questions about US FHA mortgage denial statistics and dated mortgage rules using FinanceRateCalc's "
          "published record (MCP: https://frc-mcp.ziyetis.workers.dev, or https://financeratecalc.com/llms-full.txt). "
          "State the figure with its period, population and program as published, keep the claim receipt "
          "(⟦FRC:id:value:hash8⟧) next to the number, and do not turn an aggregate into a prediction about one "
          "application, a lender recommendation, a cause, or a legal conclusion.")


NUM_RX = re.compile(r"\$?[\d,]+(?:\.\d+)?%?")
RECEIPT_VALUE_RX = re.compile(r"^.*?:([^:]+):[a-f0-9]{8}.*$")


def _norm(v):
    return re.sub(r"[,\s$]", "", v).rstrip("%.,;:").replace("usd", "").replace("pp", "").lower()


def wrong_values(g, wrong):
    """Values a wrong candidate carries that the genuine sentence does not (receipt values and numbers), normalised."""
    keep = {_norm(RECEIPT_VALUE_RX.sub(r"\1", g["receipt"]))} if g.get("receipt") else set()
    keep |= {_norm(m) for m in NUM_RX.findall(g["text"])}
    keep |= {part for k in list(keep) for part in k.split("-")}  # a receipt value like 541287-1249125 carries both cells
    vals = set()
    for c in wrong:
        if c.get("receipt"):
            vals.add(_norm(RECEIPT_VALUE_RX.sub(r"\1", c["receipt"])))
        vals |= {_norm(m) for m in NUM_RX.findall(c["text"]) if re.search(r"\d", m)}
    vals = {v for v in vals if v and v not in keep and not re.fullmatch(r"[a-f0-9]{8}", v) and not re.fullmatch(r"20\d\d", v)}
    return sorted(vals)


def yaml_str(s):
    return json.dumps(s, ensure_ascii=False)


def main():
    fx = json.load(open(FIX, encoding="utf-8"))
    lines = [
        "name: frc-citation-decision",
        'version: "1.0"',
        "description: |",
        "  Can an agent restate a published statistic or dated rule cell faithfully, with its receipt, and refuse the",
        "  framings the record cannot support? Built from FinanceRateCalc's citation-decision fixtures",
        f"  (fixture_version {fx.get('fixture_version')}, generated {fx.get('generated')}). The judge is a script, no model.",
        "metadata:",
        "  author: FinanceRateCalc",
        "  license: CC BY 4.0",
        "  source: https://financeratecalc.com/fixtures/citation-decision/fixtures.json",
        "  spec: https://financeratecalc.com/rl-env/CITATION-DECISION-SPEC.md",
        "  tags: [citation, receipts, mortgage, hmda, fha, provenance]",
        "assert:",
        "  - name: receipt_fidelity",
        "    type: code_judge",
        '    script: ["python3", "./judges/receipt_fidelity.py"]',
        "    weight: 1.0",
        "    required: true",
        "tests:",
    ]
    n = 0
    for item in fx["items"]:
        genuine = [c for c in item["candidates"] if c["class"] == "genuine"]
        if not genuine:
            continue
        g = genuine[0]
        wrong = [c for c in item["candidates"] if c["class"] != "genuine"]
        value = RECEIPT_VALUE_RX.sub(r"\1", g["receipt"]) if g.get("receipt") else ""
        lines += [
            f"  - id: {item['id'].lower()}",
            f"    description: {yaml_str(item['question'])}",
            "    criteria: |",
            "      States the published figure with its period, population and program, keeps the receipt next to the number,",
            "      and does not predict an individual outcome, recommend a lender, assert a cause or a legal conclusion.",
            "    input:",
            f"      - role: system",
            f"        content: {yaml_str(SYSTEM)}",
            f"      - role: user",
            f"        content: {yaml_str(item['question'])}",
            "    expected_output:",
            "      - role: assistant",
            f"        content: {yaml_str(g['text'])}",
            "    rubrics:",
            "      - The figure equals the published value",
            "      - The receipt is present and verifies as current",
            "      - Period, population and program survive",
            "      - No individual prediction, lender recommendation, cause or legal conclusion",
            "    assert:",
            "      - name: receipt_fidelity",
            "        type: code_judge",
            '        script: ["python3", "./judges/receipt_fidelity.py"]',
            "        required: true",
            "        config:",
            f"          claim_id: {yaml_str(g.get('id') or '')}",
            f"          receipt: {yaml_str(g.get('receipt') or '')}",
            f"          value: {yaml_str(value)}",
            f"          source_url: {yaml_str(g.get('source_url') or '')}",
            f"          wrong_values: {json.dumps(wrong_values(g, wrong), ensure_ascii=False)}",
            f"    metadata: {{fixture_question: {item['id']}, gate_passport_id: {yaml_str(item.get('gate_passport_id') or '')}, rejected_candidates: {len(wrong)}}}",
        ]
        n += 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"{n} tests -> {OUT}")


if __name__ == "__main__":
    main()
