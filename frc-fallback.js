
// FRC Fallback System — tüm widget'larda kullan
async function fetchOFIData(url) {
  try {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error('Network error');
    const data = await resp.json();
    
    // Sanity check
    if (data.ofi_current && (data.ofi_current < 20 || data.ofi_current > 80)) {
      throw new Error('OFI out of range');
    }
    return data;
  } catch(e) {
    console.warn('FRC data fetch failed, using fallback:', e.message);
    return {
      ofi_current: 47,
      quarter: "Q2 2026", 
      status: "MODERATE",
      disconnect_index: -16.6,
      fallback_mode: true,
      fallback_message: "Data updating — check back in 1 hour"
    };
  }
}
