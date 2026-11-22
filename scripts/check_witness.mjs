// Witness, end to end against the server source: an in-memory store, a manifest made by the site's own code, readers
// with a full copy, a short copy and a copy with a gap, the free allowance, the paid path, and the signature.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const RP = createRequire(import.meta.url)("../assets/read-proof.js");
const assert = (c, m) => { if (!c) { console.error("FAIL:", m); process.exit(1); } };
const store = new Map();
const KV = { async get(k, t) { const v = store.get(k); return v == null ? null : (t === "json" ? JSON.parse(v) : v); }, async put(k, v) { store.set(k, v); }, async delete(k) { store.delete(k); },
  async getWithMetadata(k) { return { value: store.get(k) ?? null, metadata: null }; },
  async list({ prefix }) { return { keys: [...store.keys()].filter(k => k.startsWith(prefix)).map(name => ({ name })), list_complete: true }; } };
globalThis.fetch = async (u, o = {}) => {
  const url = new URL(typeof u === "string" ? u : u.url);
  if (url.hostname === "api.lemonsqueezy.com") {
    const key = new URLSearchParams(String(o.body)).get("license_key");
    return new Response(JSON.stringify(key === "GOOD-KEY" ? { valid: true, license_key: { status: "active" }, meta: { variant_id: 2113947 } } : { valid: false }), { status: 200 });
  }
  throw new Error("network call blocked: " + url.href);
};
if (!globalThis.caches) globalThis.caches = { default: { match: async () => undefined, put: async () => {} } };
const tmp = path.join(os.tmpdir(), "frc-witness-" + process.pid + ".mjs");
fs.copyFileSync(path.join(ROOT, "worker/index.js"), tmp);
const mod = (await import(pathToFileURL(tmp).href)).default; fs.unlinkSync(tmp);
const env = { CREDITS: KV };
const call = async (p, body) => { const r = await mod.fetch(new Request("https://w.local" + p, body ? { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) } : {}), env); return { status: r.status, body: await r.json() }; };

const text = fs.readFileSync(path.join(ROOT, "eval/read-proof/fixture-agreement.txt"), "utf8"), all = RP.linesOf(text), man = await RP.manifest(text);
const quote = (copy, lines) => lines.map(L => { const hit = copy.find(x => x.n === L); return hit ? hit.t.split(/\s+/).slice(0, 4).join(" ") : "MISSING"; });
const full = all.map((t, i) => ({ n: i + 1, t })), half = full.slice(0, Math.floor(all.length / 2));
// a copy with a gap is renumbered by its reader, who does not know lines are missing
const gap = all.slice(0, Math.floor(all.length * 0.35)).concat(all.slice(Math.floor(all.length * 0.55))).map((t, i) => ({ n: i + 1, t }));
const ST = "The Buyer can leave early only under clause 14.3.";

assert((await call("/witness/register", { manifest: { ...man, kind: "x" } })).status === 400, "a manifest of another kind is refused");
assert((await call("/witness/challenge", { doc: man.doc, statement: ST })).status === 404, "no challenge for an unregistered document");
const reg = await call("/witness/register", { manifest: man });
assert(reg.status === 200 && reg.body.free_readings_left === 3 && !JSON.stringify(reg.body).includes(man.answers[5]), "registered; the manifest is not echoed");
assert((await call("/witness/register", { manifest: { ...man, answers: man.answers.slice().reverse() } })).status === 409, "a different manifest under the same id is refused");

const read = async (copy, extra) => { const c = await call("/witness/challenge", { doc: man.doc, statement: ST, ...(extra || {}) }); if (c.status !== 200) return { c }; return { c, a: await call("/witness/answer", { challenge_id: c.body.challenge_id, answers: quote(copy, c.body.lines) }) }; };
const r1 = await read(full);
assert(r1.c.body.lines.length === 6 && r1.c.body.draw_number_for_this_statement === 1, "six lines, first draw");
assert(r1.a.body.verdict === "read" && r1.a.body.shown === 6 && /^⟦WITNESS:[0-9a-f]{16}:6\/6:[0-9a-f]{16}⟧$/.test(r1.a.body.line), "a full copy is attested as read");
assert((await call("/witness/answer", { challenge_id: r1.c.body.challenge_id, answers: quote(full, r1.c.body.lines) })).status === 404, "a challenge is answered once");
assert(JSON.parse(r1.a.body.payload).line_offsets.every(o => o === 0), "exact quotations are recorded with offset 0");
const r2 = await read(half);
assert(r2.a.body.verdict !== "read" && r2.a.body.held.slice(0, 3).every(Boolean) && !r2.a.body.held.slice(3).some(Boolean) && r2.c.body.draw_number_for_this_statement === 2, "half a copy: the last three sixths are not shown, and the draw is counted");
const r3 = await read(gap);
assert(r3.a.body.verdict !== "read" && r3.a.body.held[0] && !r3.a.body.held[5], "a copy with a gap fails after the gap");
const p1 = JSON.parse(r1.a.body.payload), p2 = JSON.parse(r2.a.body.payload), p3 = JSON.parse(r3.a.body.payload);
assert(p1.seq === 1 && p1.prev === null && p2.prev === r1.a.body.payload_sha256 && p3.prev === r2.a.body.payload_sha256 && p3.seq === 3, "each attestation names the hash of the one before it");
assert(!r1.a.body.payload.includes("Buyer") && p1.statement_sha256.length === 64, "the statement itself is not stored, only its hash");

// the signature checks with the published key, and not after one character changes
const key = (await call("/witness/key")).body;
const pub = await crypto.subtle.importKey("jwk", key.public_jwk, { name: "ECDSA", namedCurve: "P-256" }, false, ["verify"]);
const sig = (s) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/")), c => c.charCodeAt(0));
const ok = (payload, s) => crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, pub, sig(s), new TextEncoder().encode(payload));
const got = (await call("/witness/attestation?id=" + p2.id)).body;
assert(await ok(got.payload, got.signature) && got.payload === r2.a.body.payload && p2.key_id === key.key_id, "a stored attestation verifies with the published key");
assert(!(await ok(got.payload.replace('"not shown to have been read"', '"read"'), got.signature)), "a changed verdict does not verify");
assert(!JSON.stringify(key).includes('"d"'), "the private key is not served");

// the fourth reading of the same document needs a credit
const r4 = await read(full);
assert(r4.c.status === 402 && r4.c.body.payment_by_agent_allowed === false && /lemonsqueezy/.test(r4.c.body.checkout_url), "after three free readings: payment required, by a human");
assert((await read(full, { license_key: "BAD-KEY" })).c.status === 402, "an invalid licence is not accepted");
const r5 = await read(full, { license_key: "GOOD-KEY" });
const credits = [...store.entries()].filter(([k, v]) => /^[0-9a-f]{32}$/.test(k)).map(([k, v]) => JSON.parse(v));
assert(r5.a.body.verdict === "read" && credits.length === 1 && credits[0].credits_used === 1, "with a licence the reading is attested and one credit is spent");
const st = (await call("/witness/status")).body;
assert(st.attestations === 4 && st.read === 2 && st.not_shown === 2 && st.chain_head === r5.a.body.payload_sha256, "the status reports the chain head and the counts");
assert(![...store.values()].some(v => String(v).includes("Supplier shall")), "no document text is stored");
console.log("witness: ok (full copy attested, short and gapped copies not shown, one answer per challenge, draws counted, chain linked, signature verifies, free allowance then credits)");
