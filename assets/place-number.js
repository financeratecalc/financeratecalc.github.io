/* Place a number: which cells of a pasted table reproduce a quoted figure?
   Runs entirely in the reader's browser. Nothing is uploaded, stored or sent anywhere.
   The same idea as the site's denominator map, for any table: a quoted figure is searched as a cell, a share of a
   row or column total, a ratio of two cells, a share of two or three cells, a percent change and a difference.
   A match shows a definition that CAN produce the figure from this table, not the one its author used. */
(function (root) {
  "use strict";

  function num(s) {
    if (s == null) return null;
    var t = String(s).trim();
    if (!t || /^[-–—.]+$/.test(t)) return null;
    var neg = /^\(.*\)$/.test(t) || /^[-−–]/.test(t);
    t = t.replace(/[()$€£₺%\s]/g, "").replace(/^[-−–+]/, "");
    if (/^\d{1,3}(,\d{3})+(\.\d+)?$/.test(t)) t = t.replace(/,/g, "");
    else if (/^\d+,\d+$/.test(t) && !/^\d{1,3},\d{3}$/.test(t)) t = t.replace(",", ".");
    if (!/^\d+(\.\d+)?$|^\.\d+$/.test(t)) return null;
    var v = parseFloat(t);
    return isFinite(v) ? (neg ? -v : v) : null;
  }

  function splitLine(line, sep) {
    if (sep === "space") return line.trim().split(/\s{2,}/);
    if (sep === ",") { // commas that are thousands separators stay inside their number
      var out = [], cur = "", q = false;
      for (var i = 0; i < line.length; i++) {
        var ch = line[i];
        if (ch === '"') q = !q;
        else if (ch === "," && !q) { out.push(cur); cur = ""; }
        else cur += ch;
      }
      out.push(cur);
      return out;
    }
    return line.split(sep);
  }

  function parseTable(text) {
    var lines = String(text || "").replace(/\r/g, "").split("\n").filter(function (l) { return l.trim(); });
    if (!lines.length) return { cells: [], rows: 0, cols: 0 };
    var sep = lines.some(function (l) { return l.indexOf("\t") >= 0; }) ? "\t" : lines.some(function (l) { return l.indexOf(";") >= 0; }) ? ";" :
      lines.some(function (l) { return l.indexOf("|") >= 0; }) ? "|" : lines.every(function (l) { return /\s{2,}/.test(l.trim()); }) ? "space" : ",";
    var grid = lines.map(function (l) { return splitLine(l, sep).map(function (c) { return c.trim().replace(/^"|"$/g, ""); }); })
      .filter(function (r) { return !r.every(function (c) { return /^[-:| ]*$/.test(c); }); });
    var hasHeader = grid.length > 1 && grid[0].filter(function (c) { return num(c) === null && c; }).length >= Math.max(1, grid[0].length - 1);
    var header = hasHeader ? grid[0] : null, body = hasHeader ? grid.slice(1) : grid;
    var firstIsLabel = body.filter(function (r) { return num(r[0]) === null && r[0]; }).length >= body.length / 2;
    var cells = [];
    body.forEach(function (r, i) {
      var rl = firstIsLabel ? r[0] : "row " + (i + 1);
      r.forEach(function (c, j) {
        if (firstIsLabel && j === 0) return;
        var v = num(c);
        if (v === null) return;
        var cl = header && header[j] ? header[j] : "column " + (j + 1);
        cells.push({ v: v, r: i, c: j, label: rl + " · " + cl });
      });
    });
    return { cells: cells, rows: body.length, cols: Math.max.apply(null, grid.map(function (r) { return r.length; })) };
  }

  function parseTarget(s) {
    var t = String(s || "").trim(), pct = /%/.test(t) || /percent|per cent|yüzde/i.test(t);
    var m = t.replace(/\s/g, "").match(/-?\d[\d,]*\.?\d*|-?\.\d+/);
    if (!m) return null;
    var raw = m[0], v = num(raw);
    if (v === null) return null;
    var dec = (raw.replace(/,/g, "").split(".")[1] || "").length;
    return { value: v, decimals: dec, pct: pct, tol: 0.5 * Math.pow(10, -dec) + 1e-9 };
  }

  function place(table, target, opts) {
    opts = opts || {};
    var C = table.cells, t = target.value, tol = target.tol, hits = [], tried = 0, triedPct = 0, n = C.length;
    function add(kind, rank, value, text) { hits.push({ kind: kind, rank: rank, value: value, off: Math.abs(value - t), text: text }); }
    function f(x) { return Math.abs(x) >= 1000 ? x.toLocaleString("en-US", { maximumFractionDigits: 2 }) : String(+x.toFixed(4)); }
    var i, j, k, a, b, c, x;
    for (i = 0; i < n; i++) { // 1. the figure is a cell
      tried++;
      if (Math.abs(C[i].v - t) <= tol) add("cell", 1, C[i].v, "the cell itself: " + C[i].label + " = " + f(C[i].v));
      if (target.pct && Math.abs(C[i].v) <= 1 && Math.abs(C[i].v * 100 - t) <= tol) add("cell", 1, C[i].v * 100, "the cell as a percentage: " + C[i].label + " = " + f(C[i].v));
    }
    var rows = {}, cols = {};
    C.forEach(function (q) { (rows[q.r] = rows[q.r] || []).push(q); (cols[q.c] = cols[q.c] || []).push(q); });
    function totals(groups, word) { // 2. share of its row or column total
      Object.keys(groups).forEach(function (key) {
        var g = groups[key]; if (g.length < 3) return;
        var sum = g.reduce(function (s, q) { return s + q.v; }, 0); if (sum <= 0) return;
        g.forEach(function (q) { tried++; triedPct++; x = 100 * q.v / sum;
          if (Math.abs(x - t) <= tol) add("share of total", 2, x, q.label + " as a share of its " + word + " total: " + f(q.v) + " / " + f(sum) + " = " + x.toFixed(2) + "%"); });
      });
    }
    totals(rows, "row"); totals(cols, "column");
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) { // 3-5. two cells
      if (i === j) continue; a = C[i]; b = C[j]; if (b.v === 0) continue;
      tried += 3; triedPct += 2;
      x = 100 * a.v / b.v;
      if (Math.abs(x - t) <= tol) add("ratio", 3, x, a.label + " divided by " + b.label + ": " + f(a.v) + " / " + f(b.v) + " = " + x.toFixed(2) + "%");
      if (!target.pct && Math.abs(a.v / b.v - t) <= tol) add("ratio", 3, a.v / b.v, a.label + " divided by " + b.label + ": " + f(a.v) + " / " + f(b.v) + " = " + f(a.v / b.v));
      x = 100 * (a.v - b.v) / Math.abs(b.v);
      if (Math.abs(x - t) <= tol) add("percent change", 5, x, "change from " + b.label + " to " + a.label + ": (" + f(a.v) + " − " + f(b.v) + ") / " + f(b.v) + " = " + x.toFixed(2) + "%");
      if (!target.pct && i < j && Math.abs(Math.abs(a.v - b.v) - Math.abs(t)) <= tol) add("difference", 5, a.v - b.v, "difference between " + a.label + " and " + b.label + ": " + f(a.v) + " − " + f(b.v) + " = " + f(a.v - b.v));
      if (i < j && a.v + b.v > 0 && (a.r === b.r || a.c === b.c)) { // share within a pair of the same row or column
        tried += 2; triedPct += 2;
        x = 100 * a.v / (a.v + b.v);
        if (Math.abs(x - t) <= tol) add("share of two", 4, x, a.label + " as a share of itself plus " + b.label + ": " + f(a.v) + " / (" + f(a.v) + " + " + f(b.v) + ") = " + x.toFixed(2) + "%");
        x = 100 * b.v / (a.v + b.v);
        if (Math.abs(x - t) <= tol) add("share of two", 4, x, b.label + " as a share of itself plus " + a.label + ": " + f(b.v) + " / (" + f(a.v) + " + " + f(b.v) + ") = " + x.toFixed(2) + "%");
      }
    }
    function triples(groups) { // 6. one cell over itself plus two others in the same row or column (the 'decisioned' shape)
      Object.keys(groups).forEach(function (key) {
        var g = groups[key]; if (g.length < 3 || g.length > 14) return;
        for (i = 0; i < g.length; i++) for (j = 0; j < g.length; j++) for (k = j + 1; k < g.length; k++) {
          if (i === j || i === k) continue; a = g[i]; b = g[j]; c = g[k];
          var den = a.v + b.v + c.v; if (den <= 0) continue;
          tried++; triedPct++; x = 100 * a.v / den;
          if (Math.abs(x - t) <= tol) add("share of three", 6, x, a.label + " as a share of itself plus " + b.label + " and " + c.label + ": " + f(a.v) + " / " + f(den) + " = " + x.toFixed(2) + "%");
        }
      });
    }
    triples(rows); triples(cols);
    hits.sort(function (p, q) { return p.rank - q.rank || p.off - q.off; });
    var seen = {}, uniq = hits.filter(function (h) { if (seen[h.text]) return false; seen[h.text] = 1; return true; });
    return { hits: uniq.slice(0, opts.max || 40), total: uniq.length, tried: tried, cells: n,
      expected_by_chance: +(triedPct * 2 * tol / 100).toFixed(1) }; // if formula results were spread evenly over 0-100%
  }

  var api = { num: num, parseTable: parseTable, parseTarget: parseTarget, place: place };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.FRCPlace = api;

  if (typeof document !== "undefined") document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("pn-go"); if (!btn) return;
    var out = document.getElementById("pn-out");
    function esc(s) { return String(s).replace(/[&<>]/g, function (ch) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[ch]; }); }
    function run() {
      var table = parseTable(document.getElementById("pn-table").value), target = parseTarget(document.getElementById("pn-figure").value);
      if (!table.cells.length) { out.innerHTML = "<p>No numbers found in the table. Paste rows with tabs, commas, semicolons or two or more spaces between columns.</p>"; return; }
      if (!target) { out.innerHTML = "<p>Type the figure you want to place, for example 12.8% or 65,327.</p>"; return; }
      var r = place(table, target);
      var head = "<p class='small'>" + table.cells.length + " numeric cells read; " + r.tried.toLocaleString("en-US") + " formulas tried; a result within " + (target.tol).toPrecision(1) + " of " + esc(String(target.value)) + " counts as a match.</p>";
      if (!r.total) { out.innerHTML = head + "<div class='card'><b>No match.</b> Nothing in this table reproduces the figure as a cell, a share, a ratio, a percent change or a difference. It may come from another table, another edition, or a definition this search does not try. That is not evidence the figure is wrong.</div>"; return; }
      var warn = r.expected_by_chance >= 1 ? "<div class='limit'>With a table this size, about " + r.expected_by_chance + " of the percentage formulas would land on any given figure by coincidence. Treat the list as candidates and prefer the simplest.</div>" : "";
      out.innerHTML = head + warn + "<div class='card'><b>" + r.total + " match" + (r.total === 1 ? "" : "es") + (r.total > r.hits.length ? " (first " + r.hits.length + " shown, simplest first)" : "") + ".</b><ol>" +
        r.hits.map(function (h) { return "<li>" + esc(h.text) + "</li>"; }).join("") + "</ol><span class='small'>A match is a definition that can produce the figure from this table. It does not show which one the figure's author used.</span></div>";
    }
    btn.addEventListener("click", run);
    var ex = document.getElementById("pn-example");
    if (ex) ex.addEventListener("click", function (e) { e.preventDefault();
      document.getElementById("pn-table").value = "Outcome\tAll purposes\tHome purchase\tRefinance\nOriginated\t882,114\t639,159\t235,390\nApproved, not accepted\t43,242\t17,425\t25,531\nDenied\t262,250\t96,186\t155,846\nWithdrawn\t276,228\t140,982\t127,468\nClosed incomplete\t99,536\t12,381\t81,486";
      document.getElementById("pn-figure").value = "22.1%"; run(); });
  });
})(typeof window !== "undefined" ? window : globalThis);
