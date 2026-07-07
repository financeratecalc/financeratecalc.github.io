/* FRC Denial Table Widget v1 — embed: <script src="https://financeratecalc.com/widget.js" async></script> */
(function(){
  var me=document.currentScript||document.querySelector('script[src*="financeratecalc.com/widget.js"]');
  var box=document.createElement('div');
  box.style.cssText='max-width:420px;background:#0b0d12;border:1px solid rgba(255,255,255,.12);border-radius:14px;padding:18px;font-family:system-ui,sans-serif;color:#fff;font-size:13px;line-height:1.5';
  box.innerHTML='<div style="opacity:.5">Loading FHA denial data\u2026</div>';
  me.parentNode.insertBefore(box,me);
  fetch('https://raw.githubusercontent.com/financeratecalc/financeratecalc.github.io/main/_data/lender_stress_index.json')
  .then(function(r){return r.json();})
  .then(function(d){
    var rows=[];
    for(var L in d){var h=d[L].denial_history;if(h&&h['2025']!=null)rows.push([L,h['2025']]);}
    rows.sort(function(a,b){return a[1]-b[1];});
    var html='<div style="font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:rgba(255,255,255,.4);margin-bottom:10px">FHA denial rates by lender \u00b7 2025</div>';
    function row(x,c){return '<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.06)"><span>'+x[0]+'</span><b style="font-family:monospace;color:'+c+'">'+x[1]+'%</b></div>';}
    rows.slice(0,3).forEach(function(x){html+=row(x,'#22c55e');});
    html+='<div style="text-align:center;color:rgba(255,255,255,.25);padding:3px 0">\u22ee</div>';
    rows.slice(-3).forEach(function(x){html+=row(x,'#e94560');});
    html+='<div style="margin-top:12px;display:flex;justify-content:space-between;align-items:center"><a href="https://financeratecalc.com/fha-denial-rates-by-lender.html?utm_source=widget" style="color:#C8A84B;font-weight:700;text-decoration:none;font-size:12.5px">Full table of 11 \u2192</a><a href="https://financeratecalc.com/?utm_source=widget" style="color:rgba(255,255,255,.35);text-decoration:none;font-size:10.5px">Data: FRC \u00b7 federal HMDA</a></div>';
    box.innerHTML=html;
  }).catch(function(){box.innerHTML='<a href="https://financeratecalc.com/fha-denial-rates-by-lender.html" style="color:#C8A84B">FHA denial rates by lender \u2192</a>';});
})();
