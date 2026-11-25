// The list of every Figure Statement digest this publisher has issued, kept in the repository so that it is dated by commits
// the publisher cannot quietly rewrite: transparency/statement-digests.json. A digest is SHA-256 over the statement's
// to-be-signed structure (protected header and payload), so it does not depend on the signature bytes and can be computed
// here without the signing key: only the published key id goes into the header.
//   node scripts/build_statement_digests.mjs           add today's digests for figures whose statement is new or changed
//   node scripts/build_statement_digests.mjs --check   exit 1 if a figure's current digest is not in the list
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const OUT = path.join(ROOT, "transparency/statement-digests.json");
const pubDoc = JSON.parse(fs.readFileSync(path.join(ROOT, "transparency/statement-key.json"), "utf8"));
export async function currentDigests(root = ROOT) {
  const throwaway = await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);   // signs nothing that is kept
  const store = new Map([["stmt:key", JSON.stringify({ public_jwk: pubDoc.public_jwk, key_id: pubDoc.key_id, jwk: await crypto.subtle.exportKey("jwk", throwaway.privateKey), created: pubDoc.created })]]);
  const KV = { async get(k, t) { const v = store.get(k); return v == null ? null : (t === "json" ? JSON.parse(v) : v); }, async put(k, v) { store.set(k, v); }, async delete(k) { store.delete(k); },
    async getWithMetadata(k) { return { value: store.get(k) ?? null, metadata: null }; }, async list() { return { keys: [], list_complete: true }; } };
  const realFetch = globalThis.fetch;
  globalThis.fetch = async (u) => { const url = new URL(typeof u === "string" ? u : u.url); if (url.hostname !== "financeratecalc.com") throw new Error("network call blocked: " + url.href);
    const f = path.join(root, decodeURIComponent(url.pathname).slice(1)); return fs.existsSync(f) && fs.statSync(f).isFile() ? new Response(fs.readFileSync(f)) : new Response("not found", { status: 404 }); };
  if (!globalThis.caches) globalThis.caches = { default: { match: async () => undefined, put: async () => {} } };
  const tmp = path.join(os.tmpdir(), "frc-stmtd-" + process.pid + ".mjs"); fs.copyFileSync(path.join(root, "worker/index.js"), tmp);
  const worker = (await import(pathToFileURL(tmp).href)).default; fs.unlinkSync(tmp);
  const ids = JSON.parse(fs.readFileSync(path.join(root, "claims/index.json"), "utf8")).claims.filter(c => c.receipt).map(c => c.id), out = {};
  for (const id of ids) { const v = await (await worker.fetch(new Request("https://frc-mcp.ziyetis.workers.dev/statement/" + id + "?view=json"), { CREDITS: KV })).json();
    if (!v.reference || v.protected.kid !== pubDoc.key_id) throw new Error("no reference for " + id); out[id] = { digest: v.reference.digest.value, value: v.statement.value }; }
  globalThis.fetch = realFetch;
  return out;
}
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const cur = await currentDigests(), have = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, "utf8")) : { digests: {} };
  const missing = Object.keys(cur).filter(id => !(have.digests[id] || []).some(h => h.digest === cur[id].digest));
  if (process.argv.includes("--check")) { if (missing.length) { console.log("statement digests not listed for:", missing.slice(0, 8).join(", "), missing.length > 8 ? "…" : ""); process.exit(1); } console.log("statement digests: every current statement is listed"); process.exit(0); }
  const day = new Date().toISOString().slice(0, 10);
  for (const id of missing) have.digests[id] = [...(have.digests[id] || []), { digest: cur[id].digest, value: cur[id].value, first_listed: day }];
  const doc = { what: "Every digest of a Figure Statement this publisher has issued, per figure, oldest first. The last entry is the statement in force. Entries are only ever added.",
    digest_rule: "SHA-256 over the COSE Sig_structure [\"Signature1\", protected, h'', payload] of the statement (the ToBeSigned scheme); lowercase hex",
    key: "https://financeratecalc.com/transparency/statement-key.json", key_id: pubDoc.key_id, profile: "https://datatracker.ietf.org/doc/draft-yetis-scitt-figure-receipts/",
    history_begins: have.history_begins || day, updated: missing.length ? day : (have.updated || day), figures: Object.keys(have.digests).length, digests: Object.fromEntries(Object.keys(have.digests).sort().map(k => [k, have.digests[k]])) };
  fs.writeFileSync(OUT, JSON.stringify(doc, null, 1) + "\n");
  console.log(`statement digests: ${missing.length} added, ${doc.figures} figures listed`);
}
