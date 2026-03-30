(function() {
  if (sessionStorage.getItem('sb_closed')) return;

  setTimeout(function() {
    var popup = document.createElement('div');
    popup.id = 'sb-popup';
    popup.innerHTML = `
      <div style="position:fixed;bottom:24px;right:24px;z-index:9999;width:300px;background:linear-gradient(135deg,#0d1f16,#1a3328);border:1px solid rgba(68,221,136,0.3);border-radius:16px;padding:20px;box-shadow:0 8px 32px rgba(0,0,0,0.4);animation:sbSlideIn 0.5s cubic-bezier(0.16,1,0.3,1);font-family:sans-serif;" id="sb-inner">
        <button onclick="document.getElementById('sb-popup').remove();sessionStorage.setItem('sb_closed','1')" style="position:absolute;top:10px;right:12px;background:none;border:none;color:rgba(255,255,255,0.4);font-size:18px;cursor:pointer;line-height:1;">×</button>
        <div style="font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:rgba(68,221,136,0.7);margin-bottom:8px;">Credit Score Too Low?</div>
        <div style="font-size:16px;font-weight:700;color:#f0ede8;margin-bottom:6px;line-height:1.3;">Fix Your Credit Before You Apply</div>
        <div style="font-size:12px;color:rgba(240,237,232,0.5);margin-bottom:14px;line-height:1.5;">Incorrect items on your report could be costing you 50–100 points. Professional repair works fast.</div>
        <a href="https://financeratecalc.com/go/credit-repair" target="_blank" rel="noopener sponsored" onclick="sessionStorage.setItem('sb_closed','1')" style="display:block;background:linear-gradient(135deg,#1a6644,#44dd88);color:#080810;padding:11px 20px;border-radius:10px;text-decoration:none;font-weight:700;font-size:13px;text-align:center;">Start Credit Repair with Sky Blue</a>
        <div style="font-size:10px;color:rgba(240,237,232,0.2);margin-top:10px;text-align:center;">Sponsored. Commission may be earned.</div>
      </div>
      <style>@keyframes sbSlideIn{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}</style>
    `;
    document.body.appendChild(popup);
  }, 15000);
})();
