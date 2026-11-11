/* <frc-receipt r="⟦FRC:id:value:hash8⟧"></frc-receipt>
   A small, dependency-free badge any page can place next to a number that came from FinanceRateCalc.
   It shows the figure, asks the public verify endpoint whether the receipt is still current, and links to the check.
   Nothing is tracked beyond the verify call itself (which is how the publisher counts that a figure was used).
   Usage:  <script src="https://financeratecalc.com/assets/receipt-badge.js" defer></script>
           The 2025 FHA denial rate was <frc-receipt r="⟦FRC:national-fha-denial-rate-2025:22.1%:ebf6b00b⟧"></frc-receipt>.
   Licence: CC BY 4.0. */
(function () {
  if (customElements.get("frc-receipt")) return;
  var API = "https://frc-mcp.ziyetis.workers.dev/verify?r=", SITE = "https://financeratecalc.com/verify.html?r=";
  var WORD = { current: "verified", stale: "superseded", unrecognized: "not issued", "hash-current-value-mismatch": "value altered", revised: "revised by publisher", offline: "receipt" };
  var COLOR = { current: "#1f8f5f", stale: "#b45309", unrecognized: "#b91c1c", "hash-current-value-mismatch": "#b91c1c", revised: "#b45309", offline: "#6b7280" };
  class FrcReceipt extends HTMLElement {
    connectedCallback() {
      var r = (this.getAttribute("r") || "").trim(), m = /FRC:([a-z0-9-]+):([^:\s⟧]+):([a-f0-9]{8})/i.exec(r);
      var root = this.attachShadow({ mode: "open" });
      if (!m) { root.textContent = this.textContent || ""; return; }
      var value = m[2];
      root.innerHTML = '<style>:host{white-space:nowrap}a{color:inherit;text-decoration:none;font:inherit}b{font-weight:inherit}' +
        '.s{display:inline-block;font:600 .68em/1.5 system-ui,sans-serif;padding:0 .5em;margin-left:.35em;border:1px solid currentColor;border-radius:999px;vertical-align:.12em}' +
        'a:hover .s,a:focus-visible .s{background:currentColor}a:hover .s span,a:focus-visible .s span{color:#fff}</style>' +
        '<a part="link" href="' + SITE + encodeURIComponent(r) + '" title="Receipt ' + r.replace(/"/g, "") + ' — click to check it"><b part="value"></b><span class="s" part="status"><span>receipt</span></span></a>';
      root.querySelector("b").textContent = value;
      var chip = root.querySelector(".s"), set = function (k, extra) { chip.style.color = COLOR[k]; chip.firstChild.textContent = WORD[k] + (extra || ""); };
      set("offline");
      fetch(API + encodeURIComponent(r), { headers: { Accept: "application/json" } }).then(function (x) { return x.json(); }).then(function (d) {
        if (d.valid === false) return set("unrecognized");
        if (d.status === "current" && d.publisher_revision) return set("revised", " → " + Number(d.publisher_revision.revised_to).toLocaleString("en-US"));
        set(d.status in WORD ? d.status : "offline");
      }).catch(function () { set("offline"); });
    }
  }
  customElements.define("frc-receipt", FrcReceipt);
})();
