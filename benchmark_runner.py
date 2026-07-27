#!/usr/bin/env python3
"""
benchmark_runner.py — administration harness for a domain benchmark

WHAT THIS AUTOMATES
  The protocol. It presents frozen questions one at a time, refuses to let you follow
  up or correct mid-run, archives verbatim answers, shows the rubric at the moment of
  scoring, records hygiene flags, and emits results in the published schema.

WHAT THIS DOES NOT AUTOMATE
  The scoring. That is deliberate, not a limitation to be fixed later.

  Automatic grading would compare a returned figure against the ground truth and mark
  a mismatch wrong. In the first administration of this benchmark one system answered
  22.0% against a ground truth of 22.1% and scored full marks, because the question was
  whether it knew the national rate, not whether it rounded identically. A numeric
  comparator would have marked that wrong.

  More fundamentally, the rubric turns on judgments a comparator cannot make: did the
  system fabricate, or decline? Does the citation attached to the claim actually support
  it? Is this a calibrated refusal or an evasion? Those distinctions are the measurement.
  Automating them would produce a cleaner-looking number that measures less.

  So this harness enforces the protocol and asks you for the grade, with the rubric on
  screen. Where a control condition can be checked mechanically — a local data lookup —
  it does that automatically and marks it as a control rather than a result.

USAGE
  python benchmark_runner.py --config benchmark.json --system "SystemName"
  python benchmark_runner.py --config benchmark.json --control ./control_lookup.py
  python benchmark_runner.py --config benchmark.json --report results.json

LICENSE  MIT for this script. The benchmark instrument itself is CC BY 4.0.
ORIGIN   https://financeratecalc.com/benchmark-scorecard.html
"""

import argparse, json, os, sys, datetime, textwrap

RUBRIC = [
    ("A", 3, "correct figure with correct attribution"),
    ("B", 2, "right direction or magnitude; no figure or no source"),
    ("C", 1, "calibrated refusal; no fabrication"),
    ("D", 0, "confident wrong figure, or invented source"),
]
RUBRIC_NOTE = ("C outranks D deliberately. A calibrated refusal is more useful than a "
               "fluent wrong number, and a benchmark scoring them equally rewards the "
               "wrong behaviour.")

HYGIENE_PROMPT = textwrap.dedent("""
    Hygiene check for this answer:
      - Did the response reference anything not present in the question?
      - Was the session fresh, with history disabled?
      - Did you follow up, clarify or correct during the run?
    Enter a flag if any of these apply, or press Enter for none.
""").strip()


def _rule(ch="─", n=72):
    print(ch * n)


def show_rubric():
    print("\nRUBRIC (published before scoring):")
    for g, p, crit in RUBRIC:
        print(f"  {g}  {p} pts   {crit}")
    print(f"\n  {textwrap.fill(RUBRIC_NOTE, 68, subsequent_indent='  ')}\n")


def administer(cfg, system, outpath):
    qs = cfg["questions"]
    print()
    _rule("═")
    print(f"  {cfg.get('benchmark','benchmark')} v{cfg.get('version','?')} — administering to: {system}")
    _rule("═")
    print(textwrap.dedent(f"""
      Protocol, from the checklist:
        - Fresh session. History and memory disabled.
        - One question per message. Paste it exactly as printed.
        - No follow-ups, no clarifications, no corrections during the run.
        - Paste the verbatim answer back here. Do not summarise it.

      {len(qs)} questions. Ground truths are shown only at scoring, after the
      answer is recorded, so the answer is not read against the key.
    """).strip())
    show_rubric()

    results, total = [], 0
    for i, q in enumerate(qs, 1):
        _rule()
        print(f"\nQUESTION {i} of {len(qs)}   [{q['id']}]\n")
        print("  " + textwrap.fill(q["question"], 68, subsequent_indent="  "))
        print("\n  ↑ paste exactly this. Then paste the answer below.")
        print("  End the answer with a line containing only: ///\n")
        lines = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line.strip() == "///":
                break
            lines.append(line)
        answer = "\n".join(lines).strip()
        if not answer:
            print("  (empty — recorded as no answer)")

        print(f"\n  GROUND TRUTH: {q['ground_truth']}")
        show_rubric()
        while True:
            g = input("  Grade [A/B/C/D]: ").strip().upper()
            if g in {r[0] for r in RUBRIC}:
                break
            print("  Enter A, B, C or D.")
        pts = next(p for gg, p, _ in RUBRIC if gg == g)
        note = input("  One-line reason for the grade: ").strip()
        print("\n  " + HYGIENE_PROMPT.replace("\n", "\n  "))
        flag = input("\n  Hygiene flag (Enter for none): ").strip()

        total += pts
        results.append({"id": q["id"], "question": q["question"],
                        "ground_truth": q["ground_truth"], "answer_verbatim": answer,
                        "grade": g, "points": pts, "grader_note": note,
                        "hygiene_flag": flag or None})
        print(f"\n  Recorded: {g} ({pts})   running total {total}/{len(qs)*3}\n")

    out = {"benchmark": cfg.get("benchmark"), "version": cfg.get("version"),
           "system": system, "administered": datetime.date.today().isoformat(),
           "total_points": total, "max_points": len(qs) * 3,
           "score": round(total / (len(qs) * 3), 3),
           "hygiene_flags": [r for r in results if r["hygiene_flag"]],
           "answers": results,
           "note": "Grades assigned by a human against a rubric published before scoring. "
                   "Verbatim answers are included so the scoring can be checked."}
    with open(outpath, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)

    _rule("═")
    print(f"  {system}: {total}/{len(qs)*3}  ({out['score']:.1%})")
    if out["hygiene_flags"]:
        print(f"  {len(out['hygiene_flags'])} hygiene flag(s) — publish these, do not drop the runs")
    print(f"  Written to {outpath}")
    _rule("═")
    print(textwrap.dedent("""
      Before publishing: the checklist asks for the verbatim answers alongside the
      scores, your own hygiene failures, and a stated verification status for your
      ground truths. A benchmark that omits any of the three is measuring less than
      it appears to.
    """).strip() + "\n")


def run_control(cfg, script):
    """Run a mechanical control — a local lookup that should answer every question.

    A control is not a result. It isolates what the benchmark measured: if a lookup
    over the same record answers everything the tested systems missed, the failures
    were access failures rather than reasoning failures.
    """
    import subprocess
    print("\nCONTROL CONDITION (mechanical lookup — not a benchmark result)\n")
    ok = 0
    for q in cfg["questions"]:
        try:
            r = subprocess.run([sys.executable, script, q["id"]],
                               capture_output=True, text=True, timeout=30)
            got = r.stdout.strip()
            hit = bool(got) and r.returncode == 0
        except Exception as e:
            got, hit = f"error: {e}", False
        ok += hit
        print(f"  {'✓' if hit else '✗'} {q['id']:5s} {got[:90]}")
    print(f"\n  Control: {ok}/{len(cfg['questions'])}")
    print("  This measures data access, not model quality, and should be reported as such.\n")


def main():
    ap = argparse.ArgumentParser(description="Administer a domain benchmark under a fixed protocol.")
    ap.add_argument("--config", required=True, help="benchmark.json with questions and ground truths")
    ap.add_argument("--system", help="name of the system being administered to")
    ap.add_argument("--control", help="path to a script answering by id, for the control condition")
    ap.add_argument("--out", default=None, help="output path for results JSON")
    a = ap.parse_args()

    with open(a.config, encoding="utf-8") as fh:
        cfg = json.load(fh)
    if not cfg.get("questions"):
        sys.exit("Config has no questions.")

    if a.control:
        run_control(cfg, a.control)
        return
    if not a.system:
        sys.exit("Pass --system NAME, or --control SCRIPT.")
    out = a.out or f"results_{a.system.lower().replace(' ','_')}.json"
    administer(cfg, a.system, out)


if __name__ == "__main__":
    main()
