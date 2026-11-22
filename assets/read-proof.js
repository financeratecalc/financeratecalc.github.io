/* Reading proof for any text document (Reading Proof 0.2). Runs in a browser and in Node; nothing is sent anywhere.
   spec/reading-proof-0.2.md describes it; scripts/read_proof.py is the same thing in Python. */
(function (root) {
  "use strict";
  var K = 6, MIN_LINES = 60;
  async function sha(s) {
    var b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
    return Array.prototype.map.call(new Uint8Array(b), function (x) { return x.toString(16).padStart(2, "0"); }).join("");
  }
  function norm(s) { return String(s).normalize("NFKC").toLowerCase().replace(/\s+/g, " ").trim(); }
  function toks(line) { return String(line).normalize("NFKC").toLowerCase().match(/[\p{L}\p{N}.]+/gu) || []; }
  function answer(line) { return toks(line).slice(0, 4).join(" "); }                                  // the first four words of letters and digits
  function answerWs(line) { return toks(String(line).trim().split(/\s+/).slice(0, 4).join(" ")).join(" "); }  // the first four items between spaces
  function linesOf(text) { return String(text).split(/\r\n|\r|\n/).filter(function (l) { return toks(l).length >= 4; }); }
  async function manifest(text) {
    var ls = linesOf(text);
    if (ls.length < MIN_LINES) throw new Error("The document has " + ls.length + " lines of four words or more; at least " + MIN_LINES + " are needed.");
    var doc = (await sha(ls.map(norm).join("\n"))).slice(0, 16), a4 = [], a3 = [];
    for (var i = 0; i < ls.length; i++) {
      a4.push((await sha(doc + "|" + (i + 1) + "|" + answer(ls[i]))).slice(0, 12));
      a3.push((await sha(doc + "|" + (i + 1) + "|" + answerWs(ls[i]))).slice(0, 12));
    }
    return { kind: "reading-proof-0.2", doc: doc, lines: ls.length, answers: a4, answers_ws: a3 };
  }
  async function cells(man, statement, date) {
    var h = await sha(man.doc + "|" + date + "|" + norm(statement)), size = Math.floor(man.lines / K), out = [];
    for (var j = 0; j < K; j++) out.push(j * size + parseInt(h.slice(8 * (j + 1), 8 * (j + 2)), 16) % size + 1);
    return { h8: h.slice(0, 8), lines: out };
  }
  async function proofLine(man, statement, date, answers) {
    var c = await cells(man, statement, date);
    return "⟦READ:" + man.doc + ":" + date + ":" + c.h8 + ":" + answers.join(";") + "⟧";
  }
  async function verify(man, statement, proof) {
    var m = /⟦READ:([0-9a-f]{16}):(\d{4}-\d\d-\d\d):([0-9a-f]{8}):([^⟧]*)⟧/.exec(String(proof));
    if (!m) return { verdict: "no proof line" };
    if (m[1] !== man.doc) return { verdict: "proof is for another document" };
    var c = await cells(man, statement, m[2]);
    if (m[3] !== c.h8) return { verdict: "proof belongs to a different statement" };
    var got = m[4].split(";"), held = [], offs = [];
    async function at(a, L) {
      if (L < 1 || L > man.lines) return false;
      if (toks(a).length >= 4 && (await sha(man.doc + "|" + L + "|" + answer(a))).slice(0, 12) === man.answers[L - 1]) return true;
      return toks(answerWs(a)).length >= 2 && (await sha(man.doc + "|" + L + "|" + answerWs(a))).slice(0, 12) === man.answers_ws[L - 1];
    }
    for (var i = 0; i < K; i++) {   // the line itself, or the one above or below: readers slip by one line about one time in fifteen
      var a = got[i] || "", L = c.lines[i], o = null;
      if (await at(a, L)) o = 0; else if (await at(a, L - 1)) o = -1; else if (await at(a, L + 1)) o = 1;
      offs.push(o); held.push(o !== null);
    }
    var miss = []; held.forEach(function (v, i) { if (!v) miss.push(i + 1); });
    return { verdict: miss.length ? "not shown to have been read" : "read", date: m[2], lines_asked: c.lines, held: held, line_offsets: offs, document_sixths_not_shown: miss };
  }
  var api = { K: K, MIN_LINES: MIN_LINES, norm: norm, toks: toks, answer: answer, linesOf: linesOf, manifest: manifest, cells: cells, proofLine: proofLine, verify: verify };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.ReadProof = api;
})(typeof self !== "undefined" ? self : this);
