/* FRC Denial Climate badge — embed: <script src="https://financeratecalc.com/climate-badge.js" async></script> */
(function(){
  var me=document.currentScript||document.querySelector('script[src*="climate-badge.js"]');
  var el=document.createElement('a');
  el.href='https://financeratecalc.com/climate.html?utm_source=badge';
  el.style.cssText='display:inline-flex;align-items:center;gap:10px;background:#0b0d12;border:1px solid rgba(255,255,255,.15);border-radius:12px;padding:10px 16px;text-decoration:none;font-family:system-ui,sans-serif';
  me.parentNode.insertBefore(el,me);
  fetch('https://raw.githubusercontent.com/financeratecalc/financeratecalc.github.io/main/_data/climate_scores.json')
  .then(function(r){return r.json();})
  .then(function(d){
    var c=d.current, col=c.climate>=65?'#e94560':c.climate>=55?'#eab308':c.climate>=45?'#9ca3af':'#22c55e';
    el.innerHTML='<span style="font-size:9px;letter-spacing:.12em;color:rgba(255,255,255,.45);text-transform:uppercase">FRC Denial<br>Climate</span><b style="font-family:monospace;font-size:22px;color:'+col+'">'+c.climate+'</b><span style="font-size:10px;font-weight:700;letter-spacing:.1em;color:'+col+'">'+c.label+'</span>';
  }).catch(function(){el.innerHTML='<span style="color:#C8A84B;font-size:12px">FRC Denial Climate \u2192</span>';});
})();
