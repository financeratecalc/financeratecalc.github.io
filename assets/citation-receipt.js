/* FinanceRateCalc — Citation-to-Value measurement (first-party only)
   Records: did an AI/search citation land here, and what evidence action followed?
   No fabricated attribution: when the referrer is absent we record unknown_referrer
   rather than guessing a platform. No personal data, no fingerprinting. */
(function () {
  if (!window.gtag) return;
  var AI = [
    [/chatgpt\.com|openai\.com/i, 'chatgpt'],
    [/perplexity\.ai/i, 'perplexity'],
    [/claude\.ai|anthropic\.com/i, 'claude'],
    [/gemini\.google|bard\.google|aistudio\.google/i, 'gemini'],
    [/copilot\.microsoft|bing\.com\/chat/i, 'copilot'],
    [/x\.com\/i\/grok|grok\.com/i, 'grok'],
    [/deepseek\.com/i, 'deepseek'],
    [/meta\.ai/i, 'meta_ai'],
    [/huggingface\.co/i, 'huggingface'],
    [/ssrn\.com|papers\.ssrn/i, 'ssrn'],
    [/github\.com/i, 'github'],
    [/activerain\.com/i, 'activerain']
  ];
  var SEARCH = [[/bing\.com/i, 'bing'], [/google\./i, 'google'], [/duckduckgo/i, 'ddg'], [/search\.yahoo/i, 'yahoo']];

  var ref = document.referrer || '';
  var qs = new URLSearchParams(location.search);
  var utm = qs.get('utm_source') || '';
  var channel = null, kind = null;

  function match(list, s) { for (var i = 0; i < list.length; i++) if (list[i][0].test(s)) return list[i][1]; return null; }

  channel = match(AI, ref) || match(AI, utm);
  if (channel) { kind = 'ai_citation'; }
  else {
    channel = match(SEARCH, ref) || match(SEARCH, utm);
    if (channel) kind = 'search';
    else if (!ref && !utm) { channel = 'unknown_referrer'; kind = 'direct_or_unknown'; }
    else if (ref) { channel = 'referral'; kind = 'referral'; }
  }

  // Which claim page did the citation land on?
  var claim = (document.querySelector('meta[name="frc-claim-id"]') || {}).content || location.pathname;

  if (kind === 'ai_citation' || kind === 'search') {
    gtag('event', 'citation_landing', { channel: channel, kind: kind, claim: claim });
    try { sessionStorage.setItem('frc_channel', channel); sessionStorage.setItem('frc_kind', kind); } catch (e) {}
  }

  // Evidence actions — the paid or near-paid events that follow a citation
  window.frcEvidence = function (action, extra) {
    var ch = null, kd = null;
    try { ch = sessionStorage.getItem('frc_channel'); kd = sessionStorage.getItem('frc_kind'); } catch (e) {}
    gtag('event', 'evidence_action', Object.assign({
      action: action, channel: ch || 'unattributed', kind: kd || 'unattributed', claim: claim
    }, extra || {}));
  };

  // Auto-wire the standard evidence surfaces
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a');
    if (!a) return;
    var h = a.getAttribute('href') || '';
    if (/\/claims\//.test(h)) window.frcEvidence('verify_claim', { target: h });
    else if (/lender-outlier-screen-2025\.csv|\/data\//.test(h)) window.frcEvidence('evidence_download', { target: h });
    else if (/\/join-kit\//.test(h)) window.frcEvidence('join_kit_open', { target: h });
    else if (/\/claim-audit/.test(h)) window.frcEvidence('test_claim', { target: h });
    else if (/\/mcp-integration|\/mcp-server/.test(h)) window.frcEvidence('mcp_surface_open', { target: h });
    else if (/lemonsqueezy\.com\/checkout/.test(h)) window.frcEvidence('checkout_started', { target: h });
    else if (/\/reconciliation|\/null-results|\/corrections/.test(h)) window.frcEvidence('method_open', { target: h });
  }, true);
})();
