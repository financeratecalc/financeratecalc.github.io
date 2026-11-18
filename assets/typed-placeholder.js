/* A text field that shows what to type by typing it: the placeholder writes an example, pauses, erases it and writes the
   next. It stops the moment the field is focused or holds text, and does nothing at all for readers who ask for reduced
   motion (they keep the ordinary placeholder). Examples come from the field's data-typed attribute, a JSON list. */
(function () {
  "use strict";
  if (typeof document === "undefined") return;
  function start(el) {
    var list; try { list = JSON.parse(el.getAttribute("data-typed") || "[]"); } catch (e) { return; }
    if (!list.length) return;
    var still = el.getAttribute("placeholder") || list[0];
    if (!el.getAttribute("aria-label") && !el.labels || (el.labels && !el.labels.length && !el.getAttribute("aria-label"))) el.setAttribute("aria-label", still);
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    var i = 0, n = 0, dir = 1, timer = null;
    function busy() { return document.activeElement === el || el.value; }
    function step() {
      if (busy()) { el.setAttribute("placeholder", still); timer = null; return; }
      var text = list[i];
      n += dir;
      el.setAttribute("placeholder", text.slice(0, n) + (dir > 0 && n < text.length ? "▏" : ""));
      var wait = dir > 0 ? 55 : 22;
      if (dir > 0 && n >= text.length) { dir = -1; wait = 1700; }
      else if (dir < 0 && n <= 0) { dir = 1; i = (i + 1) % list.length; wait = 450; }
      timer = setTimeout(step, wait);
    }
    function resume() { if (!timer && !busy()) { n = 0; dir = 1; timer = setTimeout(step, 600); } }
    el.addEventListener("focus", function () { if (timer) { clearTimeout(timer); timer = null; } el.setAttribute("placeholder", still); });
    el.addEventListener("blur", resume);
    document.addEventListener("visibilitychange", function () { if (document.hidden && timer) { clearTimeout(timer); timer = null; } else if (!document.hidden) resume(); });
    resume();
  }
  function init() { var els = document.querySelectorAll("[data-typed]"); for (var k = 0; k < els.length; k++) start(els[k]); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
