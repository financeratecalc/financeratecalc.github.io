// Figure Statements through the server source: every figure with a receipt comes out as a COSE_Sign1 Signed Statement whose
// signature verifies with the published key, whose header names the Issuer and Subject, and whose payload is the canonical
// statement. The decoder and the signature check below are written apart from the server's encoder and use node:crypto.
// With --dump <dir> it also writes three statements and the key for an outside tool to check.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath, pathToFileURL } from "node:url";
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const assert = (c, m) => { if (!c) { console.error("FAIL:", m); process.exit(1); } };
const store = new Map();
const KV = { async get(k, t) { const v = store.get(k); return v == null ? null : (t === "json" ? JSON.parse(v) : v); }, async put(k, v) { store.set(k, v); }, async delete(k) { store.delete(k); },
  async getWithMetadata(k) { return { value: store.get(k) ?? null, metadata: null }; }, async list() { return { keys: [], list_complete: true }; } };
globalThis.fetch = async (u) => { const url = new URL(typeof u === "string" ? u : u.url); if (url.hostname !== "financeratecalc.com") throw new Error("network call blocked: " + url.href);
  const f = path.join(ROOT, decodeURIComponent(url.pathname).slice(1)); return fs.existsSync(f) && fs.statSync(f).isFile() ? new Response(fs.readFileSync(f)) : new Response("not found", { status: 404 }); };
if (!globalThis.caches) globalThis.caches = { default: { match: async () => undefined, put: async () => {} } };
const tmp = path.join(os.tmpdir(), "frc-stmt-" + process.pid + ".mjs"); fs.copyFileSync(path.join(ROOT, "worker/index.js"), tmp);
const worker = (await import(pathToFileURL(tmp).href)).default; fs.unlinkSync(tmp);
const env = { CREDITS: KV }, get = p => worker.fetch(new Request("https://frc-mcp.ziyetis.workers.dev" + p), env);

// a small CBOR reader: only what a COSE_Sign1 with this header needs
function read(b, i = 0) { const major = b[i] >> 5, info = b[i] & 31; let n = info, o = i + 1;
  if (info === 24) { n = b[o]; o += 1; } else if (info === 25) { n = b[o] << 8 | b[o + 1]; o += 2; } else if (info === 26) { n = b.readUInt32BE(o); o += 4; } else if (info > 23) throw new Error("length form not expected");
  if (major === 0) return [n, o]; if (major === 1) return [-1 - n, o];
  if (major === 2) return [b.subarray(o, o + n), o + n]; if (major === 3) return [b.subarray(o, o + n).toString("utf8"), o + n];
  if (major === 4) { const a = []; for (let k = 0; k < n; k++) { const [v, p] = read(b, o); a.push(v); o = p; } return [a, o]; }
  if (major === 5) { const m = new Map(); for (let k = 0; k < n; k++) { const [key, p] = read(b, o); const [v, q] = read(b, p); m.set(key, v); o = q; } return [m, o]; }
  if (major === 6) { const [v, p] = read(b, o); return [{ tag: n, value: v }, p]; }
  throw new Error("major type not expected"); }
const head = (major, n) => n < 24 ? Buffer.from([major << 5 | n]) : n < 256 ? Buffer.from([major << 5 | 24, n]) : Buffer.from([major << 5 | 25, n >> 8, n & 255]);
const bstr = x => Buffer.concat([head(2, x.length), x]);

const keyDoc = await (await get("/statement-key")).json();
assert(keyDoc.public_jwk.crv === "P-256" && keyDoc.registered_with_transparency_service === false && !JSON.stringify(keyDoc).includes('"d"'), "key document: public part only, and it says no transparency service");
const pub = crypto.createPublicKey({ key: keyDoc.public_jwk, format: "jwk" });
const jcs = x => Array.isArray(x) ? x.map(jcs) : (x && typeof x === "object") ? Object.fromEntries(Object.keys(x).sort().map(k => [k, jcs(x[k])])) : x;

async function check(id) {
  const r = await get("/statement/" + id); assert(r.status === 200 && /^application\/cose/.test(r.headers.get("content-type")), id + ": not served as COSE");
  const raw = Buffer.from(await r.arrayBuffer()), [top, end] = read(raw);
  assert(end === raw.length && top.tag === 18 && top.value.length === 4, id + ": not a tagged COSE_Sign1 of four items");
  const [prot, unprot, payload, sig] = top.value, [h] = read(prot);
  assert(unprot instanceof Map && unprot.size === 0, id + ": unprotected header must be empty before registration");
  assert(h.get(1) === -7 && h.get(3) === "application/json" && h.get(4).toString("utf8") === keyDoc.key_id, id + ": alg, content type or kid");
  const cwt = h.get(15); assert(cwt.get(1) === "https://financeratecalc.com" && cwt.get(2) === "https://financeratecalc.com/claims/" + id + ".json", id + ": iss or sub");
  const sigStructure = Buffer.concat([head(4, 4), head(3, 10), Buffer.from("Signature1"), bstr(prot), bstr(Buffer.alloc(0)), bstr(payload)]);
  assert(sig.length === 64 && crypto.verify("sha256", sigStructure, { key: pub, dsaEncoding: "ieee-p1363" }, sig), id + ": signature does not verify");
  const tampered = Buffer.from(payload); tampered[tampered.length - 2] ^= 1;
  assert(!crypto.verify("sha256", Buffer.concat([head(4, 4), head(3, 10), Buffer.from("Signature1"), bstr(prot), bstr(Buffer.alloc(0)), bstr(tampered)]), { key: pub, dsaEncoding: "ieee-p1363" }, sig), id + ": a changed payload must not verify");
  const st = JSON.parse(payload.toString("utf8")), doc = JSON.parse(fs.readFileSync(path.join(ROOT, "claims", id + ".json"), "utf8"));
  assert(payload.toString("utf8") === JSON.stringify(jcs(st)), id + ": payload is not in canonical form");
  assert(st.id === id && st.value === String(doc.display_value) && JSON.stringify(jcs(st.claim)) === JSON.stringify(jcs(doc.claim)) && (st.kind === "restated" || st.kind === "computed"), id + ": statement does not match the claim document");
  const h8 = crypto.createHash("sha256").update(JSON.stringify(jcs(st.claim))).digest("hex").slice(0, 8);
  assert(doc.receipt.includes(":" + h8), id + ": the token's digest is not the digest of the statement's claim member");
  if (st.kind === "restated") assert(st.source.document && /^[0-9a-f]{64}$/.test(st.source.sha256) && st.source.table, id + ": a restated figure must name its document, digest and table");
  if (doc.revision_status && doc.revision_status.revised_to != null) assert(st.source_revision && st.source_revision.value === doc.revision_status.revised_to && st.source_revision.marked_by_source === false, id + ": source revision missing");
  return { raw, st };
}
const ids = JSON.parse(fs.readFileSync(path.join(ROOT, "claims/index.json"), "utf8")).claims.filter(c => c.receipt).map(c => c.id);
let restated = 0, revised = 0; const kept = {};
for (const id of ids) { const { raw, st } = await check(id); if (st.kind === "restated") restated++; if (st.source_revision) revised++;
  if (["state-oh-2025", "official-hud-lpt-2026-08-serious-delinquency-rate", "national-fha-denial-rate-2025"].includes(id)) kept[id] = raw; }
let r = await get("/statement/no-such-figure"); assert(r.status === 404, "unknown id");
r = await get("/statement/..%2Findex"); assert(r.status === 400, "path characters refused");
const view = await (await get("/statement/state-oh-2025?view=json")).json();
assert(view.statement.value === "23.0%" && view.figure_token.includes("state-oh-2025") && /Not registered/.test(view.not_yet) && view.protected.cwt_claims.iss === "https://financeratecalc.com", "opened view");
assert(store.size === 1 && store.has("stmt:key"), "nothing is stored but the key");
const di = process.argv.indexOf("--dump");
if (di > 0) { const d = process.argv[di + 1]; fs.mkdirSync(d, { recursive: true }); fs.writeFileSync(path.join(d, "key.json"), JSON.stringify(keyDoc)); for (const [id, raw] of Object.entries(kept)) fs.writeFileSync(path.join(d, id + ".cose"), raw); }
console.log(`figure statements: ${ids.length} signed statements verify (${restated} restated, ${ids.length - restated} computed, ${revised} carrying a source revision); header, payload and token digest agree with the claim documents`);
