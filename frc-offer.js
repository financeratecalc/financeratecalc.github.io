// FRC Offer Trigger — scroll 70% or exit intent → show once per session
(function() {
  if (sessionStorage.getItem('frc_offer_shown')) return;

  // Don't show on pricing or checkout pages
  const path = window.location.pathname;
  if (path.includes('pricing') || path.includes('gumroad')) return;

  var shown = false;

  function showOffer() {
    if (shown) return;
    shown = true;
    sessionStorage.setItem('frc_offer_shown', '1');

    var el = document.createElement('div');
    el.id = 'frc-offer';
    el.innerHTML = `
      <div style="position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:9999;
        background:#0d1829;border:1px solid rgba(200,168,75,0.35);border-radius:14px;
        padding:16px 20px;display:flex;align-items:center;gap:16px;
        box-shadow:0 8px 40px rgba(0,0,0,0.6);max-width:480px;width:calc(100% - 32px);
        animation:frcSlideUp 0.4s ease;">
        <div style="flex:1;min-width:0;">
          <div style="font-size:13px;font-weight:700;color:#fff;margin-bottom:2px;">
            8 years of HMDA data. 6 lenders. Your file routed in 60 seconds.
          </div>
          <div style="font-size:11px;color:rgba(255,255,255,0.4);">
            Zai for Brokers — $49/mo · cancel anytime
          </div>
        </div>
        <a href="https://ziyetis.gumroad.com/l/ixxar" target="_blank" rel="noopener"
          style="flex-shrink:0;padding:9px 16px;background:#C8A84B;color:#000;
          border-radius:8px;font-weight:800;text-decoration:none;font-size:13px;white-space:nowrap;">
          Get it →
        </a>
        <button onclick="document.getElementById('frc-offer').remove()"
          style="flex-shrink:0;background:none;border:none;color:rgba(255,255,255,0.25);
          font-size:18px;cursor:pointer;padding:0;line-height:1;">×</button>
      </div>
    `;

    var style = document.createElement('style');
    style.textContent = '@keyframes frcSlideUp{from{opacity:0;transform:translateX(-50%) translateY(20px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}';
    document.head.appendChild(style);
    document.body.appendChild(el);

    // Auto-dismiss after 12 seconds
    setTimeout(function() {
      var e = document.getElementById('frc-offer');
      if (e) e.remove();
    }, 12000);
  }

  // Trigger 1: scroll 70%
  window.addEventListener('scroll', function() {
    var scrolled = (window.scrollY + window.innerHeight) / document.documentElement.scrollHeight;
    if (scrolled > 0.70) showOffer();
  }, { passive: true });

  // Trigger 2: exit intent (mouse leaves top of page on desktop)
  document.addEventListener('mouseleave', function(e) {
    if (e.clientY < 50) showOffer();
  });

  // Trigger 3: 45 seconds on page (engaged reader)
  setTimeout(showOffer, 45000);
})();
