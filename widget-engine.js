/*!
 * FRC Widget Engine v1 — "The Thinking Layer"
 * Embed: <script src="https://financeratecalc.com/widget-engine.js" data-frc-engine></script>
 * Bir broker sitesine gomulur; kullanicinin DTI + pesinatini alir,
 * FRC cercevesiyle (Climate + CLTV bandi + kapi esleme) cevap verir.
 * Veri: FRC public JSON (federal HMDA'dan islenmis). Credit sarti: "Data: FRC" gorunur kalir.
 */
(function(){
  var BASE = 'https://raw.githubusercontent.com/financeratecalc/financeratecalc.github.io/main/_data/';
  var host = document.currentScript;
  var div = document.createElement('div');
  div.style.cssText = 'font-family:system-ui,sans-serif;max-width:420px;background:#0b0d12;color:#fff;border:1px solid rgba(200,168,75,.35);border-radius:14px;padding:20px;line-height:1.5';
  div.innerHTML = '<div style="font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#C8A84B;margin-bottom:8px">FHA Reality Check</div>'
    + '<div style="font-size:13px;color:rgba(255,255,255,.6);margin-bottom:12px">Where does your file land on the federal map? (310,592 HMDA records)</div>'
    + '<label style="font-size:11px;color:rgba(255,255,255,.45)">Your DTI % <input id="frcDti" type="number" min="20" max="60" value="43" style="width:100%;padding:8px;margin:4px 0 10px;background:#08090c;border:1px solid rgba(255,255,255,.15);border-radius:8px;color:#fff"></label>'
    + '<label style="font-size:11px;color:rgba(255,255,255,.45)">Down payment % <input id="frcDown" type="number" min="0" max="50" value="10" style="width:100%;padding:8px;margin:4px 0 12px;background:#08090c;border:1px solid rgba(255,255,255,.15);border-radius:8px;color:#fff"></label>'
    + '<button id="frcRun" style="width:100%;padding:11px;background:#C8A84B;color:#000;border:none;border-radius:9px;font-weight:800;cursor:pointer">Read my coordinates</button>'
    + '<div id="frcOut" style="margin-top:12px"></div>'
    + '<div style="margin-top:10px;font-size:10px;color:rgba(255,255,255,.35)">Data: <a href="https://financeratecalc.com" target="_blank" style="color:rgba(200,168,75,.8)">FRC — FinanceRateCalc</a> · historical observation, not advice</div>';
  host.parentNode.insertBefore(div, host);

  var SURF=null, CLI=null;
  Promise.all([
    fetch(BASE+'decision_surfaces_2025.json').then(function(r){return r.json()}),
    fetch(BASE+'climate_scores.json').then(function(r){return r.json()})
  ]).then(function(res){ SURF=res[0]; CLI=res[1]; });

  function bandOf(cltv){
    var bands = SURF.cltv_bands;
    for (var i=0;i<bands.length;i++){
      var m = bands[i].replace('+','-999').split('-');
      if (cltv >= +m[0] && cltv <= +m[1]+0.99) return i;
    }
    return bands.length-1;
  }

  document.addEventListener('click', function(e){
    if (e.target.id !== 'frcRun' || !SURF) return;
    var dtiRaw = parseInt(document.getElementById('frcDti').value)||43;
    var dti = Math.max(36, Math.min(49, dtiRaw));
    var down = parseFloat(document.getElementById('frcDown').value)||10;
    var cltv = 100 - down;
    var row = bandOf(cltv), col = SURF.dti_axis.indexOf(dti);
    var cells = [];
    for (var L in SURF.surfaces){
      var v = SURF.surfaces[L][row][col];
      if (v !== null && v !== undefined) cells.push([L, v]);
    }
    cells.sort(function(a,b){return a[1]-b[1]});
    var out = document.getElementById('frcOut');
    var climate = CLI.current;
    var html = '<div style="font-size:12px;color:rgba(255,255,255,.5);margin-bottom:8px">Credit climate now: <b style="color:#C8A84B">'+climate.climate+'/100 ('+climate.label+')</b> · Your band: CLTV '+SURF.cltv_bands[row]+' × DTI '+dti+(dtiRaw<36?' (mapped from '+dtiRaw+' — at low DTI, denial is rarely DTI-driven)':'')+'</div>';
    if (!cells.length){
      html += '<div style="font-size:13px;color:rgba(255,255,255,.6)">No lender publishes enough volume at this exact coordinate (n&lt;50). The full map: <a href="https://financeratecalc.com/fha-denial-rates-by-lender.html" target="_blank" style="color:#C8A84B">financeratecalc.com</a></div>';
    } else {
      var best = cells[0], worst = cells[cells.length-1];
      html += '<div style="font-size:14px;margin-bottom:6px">At your coordinates, observed 2025 denial rates run <b style="color:#22c55e">'+best[1].toFixed(1)+'%</b> ('+best[0]+') to <b style="color:#e94560">'+worst[1].toFixed(1)+'%</b> ('+worst[0]+')'+(cells.length>2?' across '+cells.length+' lenders':'')+'.</div>';
      if (worst[1]-best[1] > 20) html += '<div style="font-size:12.5px;color:rgba(255,255,255,.55)">That is a <b>'+(worst[1]-best[1]).toFixed(0)+'-point spread</b> — at your down payment level, door choice matters enormously.</div>';
      html += '<a href="https://financeratecalc.com/zai-one.html" target="_blank" style="display:inline-block;margin-top:10px;font-size:12.5px;color:#C8A84B;font-weight:700">Full routing with Zai (free) →</a>';
    }
    out.innerHTML = html;
    try { if (typeof gtag === 'function') gtag('event', 'frc_widget_engine_run', {dti: dti, cltv_band: SURF.cltv_bands[row]}); } catch(e){}
  });
})();
