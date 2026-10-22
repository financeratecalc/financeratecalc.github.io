/* FRC — AI referral detector
   Amac: ziyaretcinin bir AI asistanindan gelip gelmedigini tespit edip GA4'e yazmak.
   Hicbir kisisel veri toplanmaz; sadece yonlendiren platformun adi. */
(function(){
  try{
    var AI = [
      [/chatgpt\.com|chat\.openai\.com|openai\.com/i,        'ChatGPT'],
      [/perplexity\.ai/i,                                    'Perplexity'],
      [/copilot\.microsoft\.com|bing\.com\/chat|edgeservices/i,'Copilot'],
      [/gemini\.google\.com|bard\.google\.com/i,             'Gemini'],
      [/claude\.ai|anthropic\.com/i,                         'Claude'],
      [/you\.com/i,                                          'You.com'],
      [/phind\.com/i,                                        'Phind'],
      [/poe\.com/i,                                          'Poe'],
      [/deepseek\.com/i,                                     'DeepSeek'],
      [/kagi\.com/i,                                         'Kagi'],
      [/manus\.im|manus\.ai/i,                               'Manus'],
      [/grok\.com|x\.ai/i,                                   'Grok'],
      [/mistral\.ai|lechat/i,                                'Mistral'],
      [/huggingface\.co/i,                                   'HuggingFace']
    ];
    var qs = new URLSearchParams(location.search);
    var utm = (qs.get('utm_source')||'').toLowerCase();
    var ref = document.referrer || '';
    var platform = '', how = '';

    // 1) utm izinden (ChatGPT bunu otomatik ekliyor)
    if(utm){
      for(var i=0;i<AI.length;i++){ if(AI[i][0].test(utm)){ platform=AI[i][1]; how='utm'; break; } }
    }
    // 2) referrer'dan
    if(!platform && ref){
      for(var j=0;j<AI.length;j++){ if(AI[j][0].test(ref)){ platform=AI[j][1]; how='referrer'; break; } }
    }

    if(platform){
      var payload = {ai_platform: platform, detection: how, landing_page: location.pathname};
      if(typeof gtag !== 'undefined'){ gtag('event','ai_referral', payload); }
      try{ sessionStorage.setItem('frc_ai_ref', platform); }catch(e){}
      // gorsel is: konsola not (gelistirme icin, kullaniciya gorunmez)
      if(window.console && console.debug) console.debug('[FRC] AI referral:', platform, how);
    } else {
      // AI olmayan ama referrer'siz gelen trafigi de isaretle (karsilastirma icin)
      if(!ref && !document.location.search && typeof gtag!=='undefined'){
        // Imza alanlari (kisisel veri degil): otomasyon bayragi, saat dilimi, tarayici markasi, ekran.
        // Referrer'siz "ilk ziyaret"lerin insan mi, bir cevap motorunun sayfa getiricisi mi oldugunu ayirmak icin.
        var fp = {landing_page: location.pathname};
        try{ fp.webdriver = navigator.webdriver ? 'yes' : 'no'; }catch(e){}
        try{ fp.tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; }catch(e){}
        try{ var b = (navigator.userAgentData && navigator.userAgentData.brands) ? navigator.userAgentData.brands.map(function(x){return x.brand+' '+x.version;}).join('|') : (navigator.userAgent||'').replace(/^Mozilla\/5\.0 \(/,'').slice(0,80); fp.ua_brand = b; }catch(e){}
        try{ fp.screen = (screen.width||0)+'x'+(screen.height||0)+(window.devicePixelRatio?('@'+window.devicePixelRatio):''); }catch(e){}
        try{ fp.langs = (navigator.languages||[]).slice(0,3).join(','); }catch(e){}
        gtag('event','direct_or_hidden_referrer', fp);
      }
    }
  }catch(e){}
})();

// Evidence footnote: which of its links get used (Verify, Cite card, JSON, Method, setup). No personal data.
(function(){
  try{
    document.addEventListener('click', function(e){
      var a = e.target && e.target.closest ? e.target.closest('.frc-footnote a') : null;
      if(!a || typeof gtag==='undefined') return;
      var box = a.closest('.frc-footnote');
      gtag('event','evidence_footnote_click', {link: (a.textContent||'').trim().slice(0,20), claim: box ? box.getAttribute('data-frc-footnote') : '', landing_page: location.pathname});
    }, true);
  }catch(e){}
})();

// Reverse receipts (2026-10-22): if a crawler has verified this page's receipt, say so next to it. Data: /transparency/crawl-ledger.json,
// rebuilt daily from the verify log (bots only; bot name, day, count, status). A verification is a check, not a citation.
(function(){
  try{
    var els = document.querySelectorAll('.frc-footnote[data-frc-footnote], .frc-receipt[data-receipt]');
    if(!els.length) return;
    var NAMES = {applebot:'Applebot', gptbot:'GPTBot', bingbot:'Bingbot', googlebot:'Googlebot', claudebot:'ClaudeBot', perplexitybot:'PerplexityBot', bytespider:'Bytespider'};
    fetch('/transparency/crawl-ledger.json', {cache:'force-cache'}).then(function(r){ return r.json(); }).then(function(L){
      var C = (L && L.claims) || {};
      els.forEach(function(el){
        var id = el.getAttribute('data-frc-footnote') || ((el.getAttribute('data-receipt')||'').match(/FRC:([a-z0-9-]+):/i)||[])[1];
        var e = id && C[id]; if(!e) return;
        var best = null; Object.keys(e).forEach(function(b){ if(!best || e[b].last > e[best].last) best = b; });
        if(!best) return;
        var n = Object.keys(e).reduce(function(a,b){ return a + e[b].n; }, 0);
        var s = document.createElement('span');
        s.className = 'frc-crawl-verified';
        s.style.cssText = 'display:block;font-size:11px;color:rgba(255,255,255,.45);margin-top:4px;';
        s.innerHTML = 'Receipt last verified by <b style="color:rgba(200,168,75,.9)">' + (NAMES[best] || best) + '</b> on ' + e[best].last + ' (' + n + ' crawler check' + (n===1?'':'s') + '; a check, not a citation) · <a href="/transparency/crawl-ledger.json" style="color:inherit">ledger</a>';
        el.appendChild(s);
      });
    }).catch(function(){});
  }catch(e){}
})();
