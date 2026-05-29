/**
 * FRC Signals Embed v1
 * Source: FinanceRateCalc Research — financeratecalc.com
 * License: CC BY 4.0 — free to use with attribution
 * Usage: <script src="https://financeratecalc.com/frc-signals.js"></script>
 *        <div id="frc-signal-widget"></div>
 */
(function() {
  var FRC = {
    apiBase: 'https://financeratecalc.com',
    
    render: function(containerId) {
      var el = document.getElementById(containerId || 'frc-signal-widget');
      if (!el) return;
      
      fetch(FRC.apiBase + '/overlay-climate.json')
        .then(function(r) { return r.json(); })
        .then(function(climate) {
          return fetch(FRC.apiBase + '/signals.json')
            .then(function(r) { return r.json(); })
            .then(function(signals) {
              FRC._renderWidget(el, climate, signals);
            });
        })
        .catch(function() {
          // Fallback static render
          FRC._renderStatic(el);
        });
    },
    
    _renderWidget: function(el, climate, signals) {
      var ofi = climate.current_state.ofi;
      var state = climate.current_state.macro_state;
      var direction = climate.current_state.direction;
      var activeCount = signals.active_signals.length;
      var ofiColor = ofi <= 40 ? '#6bffb8' : ofi <= 55 ? '#f0a020' : '#ff6b6b';
      
      el.innerHTML = [
        '<div style="background:#08090c;border:1px solid rgba(200,164,74,0.3);border-radius:10px;padding:16px;font-family:DM Sans,sans-serif;max-width:280px;">',
        '<div style="font-size:9px;letter-spacing:0.18em;text-transform:uppercase;color:rgba(200,164,74,0.5);font-weight:700;margin-bottom:8px;">FRC Overlay Intelligence</div>',
        '<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:6px;">',
        '<span style="font-size:38px;font-weight:900;color:' + ofiColor + ';font-family:Georgia,serif;">' + ofi + '</span>',
        '<div><div style="font-size:11px;color:#fff;font-weight:700;">OFI</div><div style="font-size:10px;color:rgba(255,255,255,0.4);">Q2 2026</div></div>',
        '</div>',
        '<div style="font-size:11px;color:' + ofiColor + ';font-weight:700;margin-bottom:8px;">' + state + ' · ' + direction + '</div>',
        '<div style="font-size:10px;color:rgba(255,255,255,0.4);margin-bottom:10px;">' + activeCount + ' active signal' + (activeCount !== 1 ? 's' : '') + '</div>',
        '<div style="border-top:1px solid rgba(255,255,255,0.07);padding-top:8px;font-size:9px;color:rgba(255,255,255,0.25);">',
        'Source: <a href="https://financeratecalc.com/frc-research.html" target="_blank" style="color:rgba(200,164,74,0.4);text-decoration:none;">FRC Research</a>',
        '</div></div>'
      ].join('');
    },
    
    _renderStatic: function(el) {
      el.innerHTML = [
        '<div style="background:#08090c;border:1px solid rgba(200,164,74,0.3);border-radius:10px;padding:16px;font-family:DM Sans,sans-serif;max-width:280px;">',
        '<div style="font-size:9px;letter-spacing:0.18em;text-transform:uppercase;color:rgba(200,164,74,0.5);font-weight:700;margin-bottom:8px;">FRC Overlay Intelligence</div>',
        '<div style="font-size:38px;font-weight:900;color:#f0a020;font-family:Georgia,serif;margin-bottom:6px;">47</div>',
        '<div style="font-size:11px;color:#f0a020;font-weight:700;margin-bottom:8px;">MODERATE · Re-tightening</div>',
        '<div style="font-size:9px;color:rgba(255,255,255,0.25);border-top:1px solid rgba(255,255,255,0.07);padding-top:8px;">',
        'Source: <a href="https://financeratecalc.com/frc-research.html" target="_blank" style="color:rgba(200,164,74,0.4);text-decoration:none;">FRC Research</a>',
        '</div></div>'
      ].join('');
    },
    
    getCurrentOFI: function() {
      return fetch(FRC.apiBase + '/overlay-climate.json')
        .then(function(r) { return r.json(); })
        .then(function(d) { return d.current_state; });
    },
    
    getActiveSignals: function() {
      return fetch(FRC.apiBase + '/signals.json')
        .then(function(r) { return r.json(); })
        .then(function(d) { return d.active_signals; });
    }
  };
  
  window.FRCSignals = FRC;
  
  // Auto-render if container exists
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { FRC.render(); });
  } else {
    FRC.render();
  }
})();
