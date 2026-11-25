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
let HIST = null;   // when set, stands in for the published digest list
let BREAK = null;  // when set, a function of the path that returns a status to fail with (a read that goes wrong)
globalThis.fetch = async (u) => { const url = new URL(typeof u === "string" ? u : u.url); if (url.hostname !== "financeratecalc.com") throw new Error("network call blocked: " + url.href);
  if (BREAK) { const code = BREAK(url.pathname); if (code === "throw") throw new Error("connection reset"); if (code) return new Response("x", { status: code }); }
  if (HIST && url.pathname === "/transparency/statement-digests.json") return new Response(JSON.stringify(HIST));
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
  assert(Array.isArray(st.limits) && st.limits.length > 0, id + ": a statement must carry its limits");
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
// A reference that survives re-signing: two fetches give different signature bytes and the same ToBeSigned digest; the digest
// is the SHA-256 of the Sig_structure, computed here from the bytes served.
const tbs = raw => { const [top] = read(raw), [prot, , payload] = top.value; return crypto.createHash("sha256").update(Buffer.concat([head(4, 4), head(3, 10), Buffer.from("Signature1"), bstr(prot), bstr(Buffer.alloc(0)), bstr(payload)])).digest("hex"); };
const a1 = Buffer.from(await (await get("/statement/state-oh-2025")).arrayBuffer()), a2 = Buffer.from(await (await get("/statement/state-oh-2025")).arrayBuffer());
assert(!a1.equals(a2) && tbs(a1) === tbs(a2) && tbs(a1) === view.reference.digest.value && view.reference.digest.scheme === "ToBeSigned" && view.reference.sub.endsWith("/claims/state-oh-2025.json"), "the reference digest must not depend on the signature bytes");
let st = await (await get("/statement/state-oh-2025?digest=" + tbs(a1))).json(); assert(st.state === "current" && st.current_value === "23.0%", "current digest");
st = await (await get("/statement/state-oh-2025?digest=" + "0".repeat(64))).json(); assert(st.state === "unrecognized", "a digest never issued");
assert((await get("/statement/state-oh-2025?digest=xyz")).status === 400, "malformed digest");
// the late-correction case: the statement in force when an agent pinned it is replaced afterwards
const old = "ab".repeat(32); HIST = { digests: { "state-oh-2025": [{ digest: old, first_listed: "2026-11-25" }, { digest: tbs(a1), first_listed: "2026-11-26" }] } };
st = await (await get("/statement/state-oh-2025?digest=" + old)).json(); assert(st.state === "superseded" && st.current_digest === tbs(a1), "an earlier digest reports superseded and gives the current one");
st = await (await get("/statement/official-hud-lpt-2026-08-serious-delinquency-rate?digest=" + tbs(Buffer.from(await (await get("/statement/official-hud-lpt-2026-08-serious-delinquency-rate")).arrayBuffer())))).json();
assert(st.state === "current" && st.source_revision && st.source_revision.value === 6.48, "a current statement still reports that the source restated the figure");
// the test Subject: two statements really issued in order; the first reports superseded, the second current, and neither is a published figure
const tv = async q => (await get("/statement/test-late-correction" + q));
const t1 = Buffer.from(await (await tv("?rev=1")).arrayBuffer()), t2 = Buffer.from(await (await tv("")).arrayBuffer());
const [tt] = read(t2), [th] = read(tt.value[0]); assert(th.get(15).get(2) === "https://financeratecalc.com/spec/ietf/vectors/test-late-correction.json", "test Subject");
const p1 = JSON.parse(read(t1)[0].value[2].toString("utf8")), p2 = JSON.parse(tt.value[2].toString("utf8"));
assert(!p1.source_revision && p2.source_revision.value === 6.48 && /Test fixture/.test(p1.test) && /Test fixture/.test(p2.test) && tbs(t1) !== tbs(t2), "the two revisions differ by the source revision and say they are tests");
HIST = { digests: {}, test_vectors: { "test-late-correction": [{ digest: tbs(t1), revision: 1 }, { digest: tbs(t2), revision: 2 }] } };
st = await (await tv("?digest=" + tbs(t1))).json(); assert(st.state === "superseded" && st.current_digest === tbs(t2) && st.test_subject === true, "the first revision is superseded");
st = await (await tv("?digest=" + tbs(t2))).json(); assert(st.state === "current", "the second revision is in force");
st = await (await tv("?digest=" + "0".repeat(64))).json(); assert(st.state === "unrecognized", "a digest never issued for the test Subject");
assert((await tv("?rev=3")).status === 404 && !ids.includes("test-late-correction"), "no third revision, and the test Subject is not a figure");
const built = JSON.parse(fs.readFileSync(path.join(ROOT, "spec/ietf/vectors/hud-lpt-2026-08-earlier-form.constructed.json"), "utf8"));
assert(built.issued === false && built.digest === crypto.createHash("sha256").update(Buffer.from(built.to_be_signed_hex, "hex")).digest("hex") && !JSON.parse(built.payload_utf8).source_revision, "the constructed earlier form is labelled as not issued and its digest follows from its bytes");
// A statement is signed only from complete inputs. On 2026-11-25 an outside reader was served a signed statement for
// metro-gap-fort-wayne-in-2025 without its limits member, because the read of the contract file had failed. Whatever goes
// wrong with a read, the answer is 503 and no signature; the stray digest stays on the list, marked as issued in error.
const FW = "metro-gap-fort-wayne-in-2025", fwGood = tbs(Buffer.from(await (await get("/statement/" + FW)).arrayBuffer()));
for (const [what, fail] of [["contract 500", p => p.endsWith(".contract.json") ? 500 : 0], ["contract 404", p => p.endsWith(".contract.json") ? 404 : 0], ["contract reset", p => p.endsWith(".contract.json") ? "throw" : 0], ["claim 502", p => p.endsWith(FW + ".json") ? 502 : 0], ["claim reset", p => p.endsWith(FW + ".json") ? "throw" : 0]]) {
  BREAK = fail; const rr = await get("/statement/" + FW), rj = await get("/statement/" + FW + "?view=json"); BREAK = null;
  assert(rr.status === 503 && rr.headers.get("retry-after") && !/cose/.test(rr.headers.get("content-type")) && rj.status === 503, "a failed read (" + what + ") must give 503 and no signed statement"); }
BREAK = p => p.endsWith("statement-digests.json") ? 500 : 0; r = await get("/statement/" + FW + "?digest=" + fwGood); BREAK = null;
assert(r.status === 503, "no answer about a digest when the list cannot be read");
HIST = null; const FWBAD = "bf059ab518eea35ffebe0bcd5da1739aa7280dcc5f7c0a74eae58057f9ed7946";
st = await (await get("/statement/" + FW + "?digest=" + FWBAD)).json(); if (process.env.DBG) console.log(st, fwGood); assert(st.state === "issued_in_error" && /limits/.test(st.note_on_this_digest) && st.current_digest === fwGood, "the statement served by mistake is named as such");
st = await (await get("/statement/" + FW + "?digest=" + fwGood)).json(); assert(st.state === "current", "the Fort Wayne statement in force");
// the published list, built with the published key id, names the statement in force for every figure
HIST = null; const { currentDigests } = await import("./build_statement_digests.mjs"); const listed = JSON.parse(fs.readFileSync(path.join(ROOT, "transparency/statement-digests.json"), "utf8"));
const cur = await currentDigests(); let unlisted = 0; for (const id of ids) if (!(listed.digests[id] || []).some(h => h.digest === cur[id].digest)) unlisted++;
const pubKey = JSON.parse(fs.readFileSync(path.join(ROOT, "transparency/statement-key.json"), "utf8"));
assert(pubKey.key_id === crypto.createHash("sha256").update(pubKey.public_jwk.x + "." + pubKey.public_jwk.y).digest("hex").slice(0, 16) && listed.key_id === pubKey.key_id, "published key id does not follow from the published key");
if (unlisted) console.log(`note: ${unlisted} current statement digest(s) not yet in the published list`);
const di = process.argv.indexOf("--dump");
if (di > 0) { const d = process.argv[di + 1]; fs.mkdirSync(d, { recursive: true }); fs.writeFileSync(path.join(d, "key.json"), JSON.stringify(keyDoc)); for (const [id, raw] of Object.entries(kept)) fs.writeFileSync(path.join(d, id + ".cose"), raw); }
console.log(`figure statements: ${ids.length} signed statements verify (${restated} restated, ${ids.length - restated} computed, ${revised} carrying a source revision); header, payload and token digest agree with the claim documents`);
