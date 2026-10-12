// promptfoo assertion (type: javascript, value: file://gate_assert.js). The test's vars carry the case; the app's output is graded
// by FinanceRateCalc's deterministic gate. Returns pass/score/reason in promptfoo's GradingResult shape.
module.exports = async (output, context) => {
  const { judge } = await import("./gate.mjs");
  const c = context.vars.case;
  const r = await judge(c, output);
  const detail = r.gate ? " | gate: " + r.gate.verdict + (r.gate.violations && r.gate.violations.length ? " " + r.gate.violations.map(v => v.code).join(",") : "") : "";
  return { pass: r.pass, score: r.pass ? 1 : 0, reason: (r.pass ? "OK: " : "REPAIR: ") + r.reason + detail + " | expected: " + JSON.stringify(c.expected) + " | source: " + c.source_document + " — " + c.source_fragment + " | fix: " + c.fix_hint };
};
