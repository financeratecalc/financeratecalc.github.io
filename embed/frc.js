/*! FinanceRateCalc embed v1.0 — CC BY 4.0
    Put FHA denial data from the complete 2025 federal record on your own page.

    <div data-frc="metro" data-value="cleveland-oh"></div>
    <div data-frc="lender" data-value="rocket-mortgage"></div>
    <div data-frc="state" data-value="oh"></div>
    <script src="https://financeratecalc.com/embed/frc.js" async></script>

    No tracking, no cookies, no dependencies. Data: CFPB HMDA 2025.
    Attribution line is part of the widget and is not removed — that is the licence. */
(function(){
  var API='https://financeratecalc.com/api/';
  var SITE='https://financeratecalc.com';
  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  function bgOf(el){
    /* walk up until a non-transparent background is found — the widget may sit inside a
       light card on a dark page, or the reverse, and must match its actual container */
    var n=el;
    while(n && n!==document.documentElement){
      try{
        var b=getComputedStyle(n).backgroundColor;
        if(b && b!=='transparent' && b.indexOf('rgba(0, 0, 0, 0)')!==0){
          var m=b.match(/[\d.]+/g);
          if(m && (m.length<4 || parseFloat(m[3])>0.15)) return m;
        }
      }catch(e){}
      n=n.parentElement;
    }
    try{ return getComputedStyle(document.body).backgroundColor.match(/[\d.]+/g); }catch(e){}
    return null;
  }
  function css(el){
    var dark=false;
    var bg=bgOf(el);
    if(bg) dark=(+bg[0]*299 + +bg[1]*587 + +bg[2]*114)/1000 < 140;
    return {fg:dark?'#f2f2f4':'#16181d', mut:dark?'rgba(255,255,255,.55)':'rgba(0,0,0,.5)',
            line:dark?'rgba(255,255,255,.13)':'rgba(0,0,0,.1)', acc:'#9a7d25',
            bgs:dark?'rgba(255,255,255,.04)':'rgba(0,0,0,.025)',
            good:'#1f9d55', bad:'#c0392b'};
  }
  function shell(c,title,sub,body,link){
    return '<div style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;'+
      'border:1px solid '+c.line+';border-radius:12px;padding:16px 18px;color:'+c.fg+';background:'+c.bgs+';max-width:640px;line-height:1.6;">'+
      '<div style="font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:'+c.acc+';font-weight:700;margin-bottom:6px;">'+esc(sub)+'</div>'+
      '<div style="font-size:17px;font-weight:700;margin-bottom:10px;">'+esc(title)+'</div>'+
      body+
      '<div style="margin-top:12px;padding-top:9px;border-top:1px solid '+c.line+';font-size:11px;color:'+c.mut+';line-height:1.65;">'+
      'Source: CFPB HMDA 2025, computed by <a href="'+link+'" style="color:'+c.acc+';text-decoration:none;font-weight:600;" target="_blank" rel="noopener">FinanceRateCalc</a>. '+
      'Decisioned applications; denial = action 3; reverse mortgages excluded. Rates reflect applicant mix as well as lender practice &mdash; historical observations, not predictions. '+
      '<a href="'+SITE+'/reconciliation.html" style="color:'+c.mut+';" target="_blank" rel="noopener">Not independently reproduced.</a> CC BY 4.0.'+
      '</div></div>';
  }
  function bar(c,v,max){
    var w=Math.max(2,Math.min(100,v/max*100));
    var col = v<10?c.good : v>40?c.bad : c.acc;
    return '<div style="height:7px;border-radius:4px;background:'+c.line+';overflow:hidden;"><div style="width:'+w+'%;height:100%;background:'+col+';"></div></div>';
  }
  function metro(el,d,c){
    var doors=(d.lenders||[]).filter(function(x){return x.decisioned_applications_here>=100;}).slice(0,6);
    var max=doors.length?Math.max.apply(null,doors.map(function(x){return x.denial_rate_pct;})):100;
    var rows=doors.map(function(x){
      return '<tr><td style="padding:6px 8px 6px 0;font-weight:600;font-size:13px;">'+esc(x.lender)+'</td>'+
        '<td style="padding:6px 0;width:44%;">'+bar(c,x.denial_rate_pct,max)+'</td>'+
        '<td style="padding:6px 0 6px 10px;text-align:right;font-variant-numeric:tabular-nums;font-size:13px;font-weight:700;">'+x.denial_rate_pct.toFixed(1)+'%</td></tr>';}).join('');
    var pen = d.small_loan_penalty ? '<div style="font-size:12.5px;color:'+c.mut+';margin-top:9px;">Loans under $150K were denied at <b style="color:'+c.fg+'">'+d.small_loan_denial_pct.toFixed(1)+'%</b> versus <b style="color:'+c.fg+'">'+d.big_loan_denial_pct.toFixed(1)+'%</b> above $250K &mdash; a '+d.small_loan_penalty.toFixed(2)+'&times; penalty.</div>' : '';
    var spread = d.spread_between_lenders_pts ? '<div style="font-size:12.5px;color:'+c.mut+';margin-top:6px;">A <b style="color:'+c.fg+'">'+d.spread_between_lenders_pts.toFixed(1)+'-point</b> spread between the highest-volume lenders here, in the same federal loan program.</div>' : '';
    el.innerHTML=shell(c,d.metro+': '+d.denial_rate_pct.toFixed(1)+'% of FHA applications denied',
      'FHA denials by lender · 2025',
      '<div style="font-size:12.5px;color:'+c.mut+';margin-bottom:10px;">'+d.decisioned_applications.toLocaleString()+' applications reached a credit decision. National rate: '+d.national_denial_rate_pct.toFixed(1)+'%.</div>'+
      '<table style="width:100%;border-collapse:collapse;">'+rows+'</table>'+spread+pen, SITE+d.page.replace(SITE,''));
  }
  function lender(el,d,c){
    var adj = d.peer_adjusted_ratio!=null ? '<div style="font-size:12.5px;color:'+c.mut+';margin-top:9px;">Standardized for its own applicant mix, it denies <b style="color:'+c.fg+'">'+d.peer_adjusted_ratio.toFixed(2)+'&times;</b> its expected rate.</div>' : '';
    el.innerHTML=shell(c,d.lender,'FHA record · 2025',
      '<div style="display:flex;gap:16px;flex-wrap:wrap;">'+
      '<div><div style="font-size:29px;font-weight:800;line-height:1;">'+d.denial_rate_pct.toFixed(1)+'%</div><div style="font-size:11px;color:'+c.mut+';margin-top:3px;">denied</div></div>'+
      '<div><div style="font-size:29px;font-weight:800;line-height:1;color:'+c.mut+'">'+d.peer_median_denial_rate_pct.toFixed(1)+'%</div><div style="font-size:11px;color:'+c.mut+';margin-top:3px;">peer median</div></div>'+
      '<div><div style="font-size:29px;font-weight:800;line-height:1;">'+d.decisioned_applications.toLocaleString()+'</div><div style="font-size:11px;color:'+c.mut+';margin-top:3px;">applications decided</div></div>'+
      '</div>'+adj, SITE+'/fha-denial-rates-top-100.html');
  }
  function state(el,d,c){
    var pen = d.small_loan_penalty ? '<div style="font-size:12.5px;color:'+c.mut+';margin-top:9px;">Under $150K: <b style="color:'+c.fg+'">'+d.small_loan_denial_pct.toFixed(1)+'%</b> denied. Above $250K: <b style="color:'+c.fg+'">'+d.big_loan_denial_pct.toFixed(1)+'%</b>. A '+d.small_loan_penalty.toFixed(2)+'&times; penalty on the cheapest way into a house.</div>' : '';
    el.innerHTML=shell(c,d.state+': '+d.denial_rate_pct.toFixed(1)+'% of FHA applications denied','FHA denials by state · 2025',
      '<div style="font-size:12.5px;color:'+c.mut+';">'+d.decisioned_applications.toLocaleString()+' applications reached a credit decision. National rate: '+d.national_denial_rate_pct.toFixed(1)+'%.</div>'+pen,
      SITE+'/salary-vs-denial-risk-by-state.html');
  }
  function render(el){
    var kind=el.getAttribute('data-frc'), val=(el.getAttribute('data-value')||'').toLowerCase().trim();
    if(!kind||!val) return;
    var c=css(el);
    el.innerHTML='<div style="font-family:-apple-system,sans-serif;font-size:12px;color:'+c.mut+';padding:14px;">Loading federal record…</div>';
    fetch(API+kind+'/'+encodeURIComponent(val)+'.json').then(function(r){
      if(!r.ok) throw 0; return r.json();
    }).then(function(d){
      if(kind==='metro') metro(el,d,c); else if(kind==='lender') lender(el,d,c); else state(el,d,c);
    }).catch(function(){
      el.innerHTML='<div style="font-family:-apple-system,sans-serif;font-size:12.5px;color:'+c.mut+';border:1px solid '+c.line+';border-radius:12px;padding:14px 16px;">'+
        'No published record for &ldquo;'+esc(val)+'&rdquo;. Institutions below 1,500 decisioned applications and metros below 500 are withheld rather than shown on thin counts. '+
        '<a href="'+SITE+'/embed.html" style="color:'+c.acc+';" target="_blank" rel="noopener">Find the right slug</a>.</div>';
    });
  }
  function init(){ Array.prototype.forEach.call(document.querySelectorAll('[data-frc]'),render); }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init); else init();
  window.FRCEmbed={render:render,refresh:init};
})();
