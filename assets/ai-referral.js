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
        gtag('event','direct_or_hidden_referrer',{landing_page: location.pathname});
      }
    }
  }catch(e){}
})();
