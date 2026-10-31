// receipt-verify: check a Receipt 1.0 claim receipt against its publisher, with no dependency on the publisher's server.
// Works in Node 18+ and in browsers (WebCrypto). Zero dependencies. Spec: https://financeratecalc.com/spec/receipt-1.0.md
//
//   import { parse, verify } from "receipt-verify";
//   const r = await verify("⟦FRC:state-oh-2025:23.0%:34beae06⟧", { manifest: "https://financeratecalc.com/.well-known/receipt.json" });
//   r.status  // "current" | "stale" | "hash-current-value-mismatch" | "unrecognized"
//
// How it decides, in order: the receipt is parsed; the publisher's manifest names the claim URL template and the hash
// rules; the claim document is fetched and its claim block hashed under every rule the manifest lists. Hash equals the
// document's and the quoted value equals the published value -> current. Hash equals but value differs -> the quote was
// altered. Hash differs but appears in the publisher's hash history -> stale (issued earlier, since corrected). Hash in
// neither -> unrecognized: the publisher never issued it as written. Offline: pass `claim` (and `history`) yourself.

const LB = "⟦", RB = "⟧";
const RX = new RegExp(`^${LB}?([A-Z0-9]{2,8}):([a-z0-9-]+):([^:${RB}]+):([a-f0-9]{8})(?::([a-z][0-9]{4}))?${RB}?$`);

export function parse(receipt) {
  const m = RX.exec(String(receipt || "").trim());
  return m ? { prefix: m[1], id: m[2], value: m[3], hash8: m[4], channel: m[5] || null } : null;
}

export const jcs = x => Array.isArray(x) ? x.map(jcs) : (x && typeof x === "object") ? Object.fromEntries(Object.keys(x).sort().map(k => [k, jcs(x[k])])) : x;

async function sha8hex(text) {
  const c = globalThis.crypto?.subtle ? globalThis.crypto : (await import("node:crypto")).webcrypto;
  const buf = await c.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 8);
}

// Hash rules named in a manifest's hash_rules[].id. Publishers add their own here or pass `rules` to verify().
export const HASH_RULES = {
  "jcs-sha256-8": claim => sha8hex(JSON.stringify(jcs(claim))),                                   // RFC 8785 canonical JSON
  "frc-0.1": claim => sha8hex(JSON.stringify(claim, Object.keys(claim).sort())),                  // legacy: top-level keys only
};

const getJSON = async (url, fetchImpl) => { const r = await (fetchImpl || fetch)(url, { headers: { Accept: "application/json" } }); if (!r.ok) throw new Error(`${r.status} ${url}`); return r.json(); };
const norm = v => String(v ?? "").trim();

/**
 * verify(receipt, options)
 *   options.manifest  URL of the publisher's /.well-known/receipt.json (fetched), or the manifest object itself
 *   options.claim     the claim document object (skips the fetch; offline use)
 *   options.history   the hash-history object (skips the fetch; offline use)
 *   options.rules     extra or overriding hash functions, { ruleId: async claim => hash8 }
 *   options.fetch     fetch implementation
 */
export async function verify(receipt, options = {}) {
  const p = parse(receipt);
  if (!p) return { status: "unrecognized", reason: "not a receipt", receipt };
  const f = options.fetch;
  let manifest = options.manifest;
  if (typeof manifest === "string") manifest = await getJSON(manifest, f);
  if (!manifest && !options.claim) return { status: "unrecognized", reason: "no manifest and no claim document", receipt, parsed: p };
  if (manifest && manifest.prefix && manifest.prefix !== p.prefix) return { status: "unrecognized", reason: `prefix ${p.prefix} is not this publisher's (${manifest.prefix})`, receipt, parsed: p };

  let claim = options.claim;
  const claimUrl = manifest?.claim_url_template ? manifest.claim_url_template.replace("{id}", p.id) : null;
  if (!claim) {
    if (!claimUrl) return { status: "unrecognized", reason: "manifest has no claim_url_template", receipt, parsed: p };
    try { claim = await getJSON(claimUrl, f); } catch (e) { return { status: "unrecognized", reason: `unknown claim id (${e.message})`, receipt, parsed: p, claim_url: claimUrl }; }
  }
  const block = claim.claim;
  if (!block || typeof block !== "object") return { status: "unrecognized", reason: "claim document has no claim block", receipt, parsed: p, claim_url: claimUrl };

  const rules = { ...HASH_RULES, ...(options.rules || {}) };
  const ruleIds = (manifest?.hash_rules || []).map(r => r.id).filter(id => rules[id]);
  if (!ruleIds.length) ruleIds.push("jcs-sha256-8");
  const hashes = {};
  for (const id of ruleIds) hashes[id] = await rules[id](block);
  const matched = ruleIds.find(id => hashes[id] === p.hash8) || null;
  const current = norm(claim.display_value);
  const base = { receipt, parsed: p, id: p.id, quoted_value: p.value, current_value: current, claim_url: claimUrl, hash_rule: matched, hashes,
    document_hash8: claim.hash8 || null, spec: manifest?.spec || "https://financeratecalc.com/spec/receipt-1.0.md", corrections: manifest?.corrections || null };

  if (matched) return { ...base, status: norm(p.value) === current ? "current" : "hash-current-value-mismatch",
    meaning: norm(p.value) === current ? "Hash and value match the publisher's current claim document." : "The hash is the publisher's but the quoted value is not; the quote was altered." };

  let history = options.history;
  if (!history && manifest?.hash_history) { try { history = await getJSON(manifest.hash_history, f); } catch { history = null; } }
  const issued = history?.hashes?.[p.id] || [];
  if (issued.includes(p.hash8)) return { ...base, status: "stale", meaning: "This receipt was issued for an earlier value of the claim, since corrected. Quote the current value with its current receipt.", history_url: manifest?.hash_history || null };
  return { ...base, status: "unrecognized", meaning: "The publisher never issued this receipt as written: its hash matches no value published for this claim, now or in the hash history. Forged, mistyped or truncated.", history_url: manifest?.hash_history || null };
}

export default verify;
