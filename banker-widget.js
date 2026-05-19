// FRC Banker AI Widget — loads on every page
(function(){
  if(document.getElementById('frc-widget')) return;

  var SYSTEM = `You are a 23-year banking professional and founder of FinanceRateCalc.com. You speak with calm authority, use real numbers, and are on the consumer's side. Be direct and concise — 2-3 paragraphs max. Current 2026 rates: ~6.4-6.8% for 30-yr fixed. Always add brief disclaimer at end. Never guarantee approvals or name specific lenders.`;

  var msgs = [];
  var loading = false;

  // Inject styles
  var style = document.createElement('style');
  style.textContent = `
    #frc-widget { position:fixed; bottom:20px; right:20px; z-index:9999; font-family:'Inter',sans-serif; }
    #frc-bubble { width:52px; height:52px; background:linear-gradient(135deg,#C8A84B,#f0d060); border-radius:50%; cursor:pointer; display:flex; align-items:center; justify-content:center; box-shadow:0 4px 20px rgba(200,168,75,0.4); transition:transform 0.2s; }
    #frc-bubble:hover { transform:scale(1.08); }
    #frc-bubble svg { width:22px; height:22px; fill:#0B132B; }
    #frc-dot { position:absolute; top:0; right:0; width:12px; height:12px; background:#22c55e; border-radius:50%; border:2px solid #fff; }
    #frc-panel { position:absolute; bottom:64px; right:0; width:340px; background:#0B132B; border-radius:16px; overflow:hidden; box-shadow:0 20px 60px rgba(0,0,0,0.5); display:none; flex-direction:column; border:1px solid rgba(255,255,255,0.1); }
    #frc-header { padding:14px 16px; background:rgba(255,255,255,0.05); border-bottom:1px solid rgba(255,255,255,0.08); display:flex; align-items:center; justify-content:space-between; }
    #frc-header-left { display:flex; align-items:center; gap:8px; }
    #frc-av { width:30px; height:30px; border-radius:50%; background:linear-gradient(135deg,#C8A84B,#f0d060); display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:800; color:#0B132B; }
    #frc-hname { font-size:13px; font-weight:700; color:#fff; }
    #frc-hsub { font-size:10px; color:rgba(255,255,255,0.35); }
    #frc-close { background:none; border:none; color:rgba(255,255,255,0.4); cursor:pointer; font-size:18px; line-height:1; padding:0; }
    #frc-close:hover { color:#fff; }
    #frc-msgs { height:260px; overflow-y:auto; padding:14px; display:flex; flex-direction:column; gap:10px; }
    #frc-msgs::-webkit-scrollbar { width:4px; }
    #frc-msgs::-webkit-scrollbar-track { background:transparent; }
    #frc-msgs::-webkit-scrollbar-thumb { background:rgba(255,255,255,0.15); border-radius:2px; }
    .frc-msg { display:flex; gap:8px; }
    .frc-msg.u { flex-direction:row-reverse; }
    .frc-msg-av { width:24px; height:24px; border-radius:50%; flex-shrink:0; display:flex; align-items:center; justify-content:center; font-size:9px; font-weight:800; }
    .frc-msg.a .frc-msg-av { background:linear-gradient(135deg,#C8A84B,#f0d060); color:#0B132B; }
    .frc-msg.u .frc-msg-av { background:rgba(255,255,255,0.1); color:rgba(255,255,255,0.6); font-size:12px; }
    .frc-bub { padding:9px 12px; border-radius:10px; font-size:12px; line-height:1.65; max-width:240px; }
    .frc-msg.a .frc-bub { background:rgba(255,255,255,0.07); color:rgba(255,255,255,0.85); }
    .frc-msg.u .frc-bub { background:rgba(200,168,75,0.2); color:#fff; }
    .frc-typing { display:flex; align-items:center; gap:3px; padding:9px 12px; }
    .frc-typing span { width:5px; height:5px; border-radius:50%; background:rgba(255,255,255,0.4); animation:frcBounce 1.4s ease-in-out infinite; }
    .frc-typing span:nth-child(2) { animation-delay:0.2s; }
    .frc-typing span:nth-child(3) { animation-delay:0.4s; }
    @keyframes frcBounce { 0%,60%,100%{transform:translateY(0);} 30%{transform:translateY(-5px);} }
    #frc-input-row { padding:10px 12px; border-top:1px solid rgba(255,255,255,0.07); display:flex; gap:8px; }
    #frc-inp { flex:1; background:rgba(255,255,255,0.07); border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:8px 10px; font-size:12px; color:#fff; outline:none; font-family:'Inter',sans-serif; }
    #frc-inp::placeholder { color:rgba(255,255,255,0.25); }
    #frc-inp:focus { border-color:rgba(200,168,75,0.5); }
    #frc-send { width:32px; height:32px; background:#C8A84B; border:none; border-radius:7px; cursor:pointer; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
    #frc-send:hover { background:#f0d060; }
    #frc-send svg { width:14px; height:14px; fill:#0B132B; }
    #frc-send:disabled { opacity:0.4; cursor:not-allowed; }
    #frc-footer { text-align:center; padding:6px; font-size:9px; color:rgba(255,255,255,0.2); border-top:1px solid rgba(255,255,255,0.05); }
    #frc-footer a { color:rgba(200,168,75,0.5); text-decoration:none; }
    @media(max-width:400px){ #frc-panel{ width:calc(100vw - 40px); right:0; } }
  `;
  document.head.appendChild(style);

  // Build widget HTML
  var widget = document.createElement('div');
  widget.id = 'frc-widget';
  widget.innerHTML = `
    <div id="frc-panel">
      <div id="frc-header">
        <div id="frc-header-left">
          <div id="frc-av">ZY</div>
          <div>
            <div id="frc-hname">Zai · FRC Banker AI</div>
            <div id="frc-hsub">Hi, I'm Zai — 23 years of banking in a chat.</div>
          </div>
        </div>
        <button id="frc-close" onclick="toggleFRC()">×</button>
      </div>
      <div id="frc-msgs"></div>
      <div id="frc-input-row">
        <input id="frc-inp" placeholder="Ask about rates, credit, mortgages..." onkeydown="if(event.key==='Enter') frcSend()">
        <button id="frc-send" onclick="frcSend()">
          <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
        </button>
      </div>
      <div id="frc-footer">Educational only · Not financial advice · <a href="/frc-banker-ai.html">Full screen →</a></div>
    </div>
    <div id="frc-bubble" onclick="toggleFRC()" title="Chat with Zai · FRC Banker AI">
      <div id="frc-dot"></div>
      <span style="font-size:22px;line-height:1;">👨‍💼</span>
    </div>
  `;
  document.body.appendChild(widget);

  var open = false;

  window.toggleFRC = function(){
    open = !open;
    document.getElementById('frc-panel').style.display = open ? 'flex' : 'none';
    if(open && msgs.length === 0){
      frcAddMsg('a', "Hi, I'm Zai 👨‍💼 — 23 years of banking, condensed into a chat. Ask me anything: why you were denied, what rate you should be getting, or what your bank isn't telling you.");
    }
    if(open) setTimeout(function(){ document.getElementById('frc-inp').focus(); }, 100);
  };

  function frcAddMsg(role, text){
    var box = document.getElementById('frc-msgs');
    var div = document.createElement('div');
    div.className = 'frc-msg ' + role;
    div.innerHTML = '<div class="frc-msg-av">' + (role==='a'?'👨‍💼':'👤') + '</div>' +
      '<div class="frc-bub">' + text.replace(/\n/g,'<br>').replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>') + '</div>';
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  }

  function frcTyping(){
    var box = document.getElementById('frc-msgs');
    var div = document.createElement('div');
    div.className = 'frc-msg a'; div.id = 'frc-typing';
    div.innerHTML = '<div class="frc-msg-av">ZY</div><div class="frc-bub"><div class="frc-typing"><span></span><span></span><span></span></div></div>';
    box.appendChild(div); box.scrollTop = box.scrollHeight;
  }

  window.frcSend = async function(){
    var inp = document.getElementById('frc-inp');
    var text = inp.value.trim();
    if(!text || loading) return;
    loading = true;
    document.getElementById('frc-send').disabled = true;
    inp.value = '';
    frcAddMsg('u', text);
    msgs.push({role:'user', content:text});
    frcTyping();

    try{
      var res = await fetch('https://api.anthropic.com/v1/messages',{
        method:'POST',
        headers:{
          'Content-Type':'application/json',
          'x-api-key':window._AKEY||'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',
          'anthropic-version':'2023-06-01',
          'anthropic-dangerous-direct-browser-access':'true'
        },
        body:JSON.stringify({
          model:'claude-sonnet-4-20250514',
          max_tokens:600,
          system:SYSTEM,
          messages:msgs
        })
      });
      var data = await res.json();
      var t = document.getElementById('frc-typing');
      if(t) t.remove();
      if(data.content&&data.content[0]){
        var reply = data.content[0].text;
        msgs.push({role:'assistant', content:reply});
        frcAddMsg('a', reply);
      } else {
        frcAddMsg('a',(data.error&&data.error.message)||'Sorry, try again.');
      }
    } catch(e){
      var t2 = document.getElementById('frc-typing');
      if(t2) t2.remove();
      frcAddMsg('a','Connection issue. Please try again.');
    }
    loading = false;
    document.getElementById('frc-send').disabled = false;
  };
})();
