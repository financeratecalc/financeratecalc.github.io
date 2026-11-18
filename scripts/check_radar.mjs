// Figure Radar, end to end against the server source: an in-memory store, the site's own files, and a fake push service.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const assert = (c, m) => { if (!c) { console.error("FAIL:", m); process.exit(1); } };
const store = new Map();
const KV = { async get(k, t) { const v = store.get(k); return v == null ? null : (t === "json" ? JSON.parse(v) : v); }, async put(k, v) { store.set(k, v); }, async delete(k) { store.delete(k); },
  async list({ prefix }) { return { keys: [...store.keys()].filter(k => k.startsWith(prefix)).map(name => ({ name })), list_complete: true }; } };
const pushes = []; let pushStatus = 201, hideRevisions = 0;
globalThis.fetch = async (u, o = {}) => {
  const url = new URL(typeof u === "string" ? u : u.url);
  if (url.hostname === "financeratecalc.com") {
    const f = path.join(ROOT, decodeURIComponent(url.pathname));
    if (!fs.existsSync(f)) return new Response("not found", { status: 404 });
    let body = fs.readFileSync(f, "utf8");
    if (url.pathname === "/data/revisions.json" && hideRevisions) { const d = JSON.parse(body); d.items = d.items.slice(0, d.items.length - hideRevisions); body = JSON.stringify(d); }
    return new Response(body, { status: 200, headers: { "content-type": "application/json" } });
  }
  if (/fcm\.googleapis\.com$/.test(url.hostname)) { pushes.push({ url: url.href, headers: o.headers, body: o.body }); return new Response(null, { status: pushStatus }); }
  throw new Error("network call blocked: " + url.href);
};
if (!globalThis.caches) globalThis.caches = { default: { match: async () => undefined, put: async () => {} } };
const tmp = path.join(os.tmpdir(), "frc-radar-" + process.pid + ".mjs");
fs.copyFileSync(path.join(ROOT, "worker/index.js"), tmp);
const mod = (await import(pathToFileURL(tmp).href)).default; fs.unlinkSync(tmp);
const env = { CREDITS: KV };
const call = async (p, body) => { const r = await mod.fetch(new Request("https://w.local" + p, body ? { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) } : {}), env); return { status: r.status, body: await r.json() }; };
const tick = async () => { let p; await mod.scheduled({}, env, { waitUntil(x) { p = x; } }); await p; };
const EP = "https://fcm.googleapis.com/fcm/send/device-one", EP2 = "https://fcm.googleapis.com/fcm/send/device-two";

const key = await call("/radar/key");
const raw = Uint8Array.from(atob(key.body.publicKey.replace(/-/g, "+").replace(/_/g, "/")), c => c.charCodeAt(0));
assert(raw.length === 65 && raw[0] === 4 && (await call("/radar/key")).body.publicKey === key.body.publicKey, "one P-256 public key, stable across calls");
assert((await call("/radar/subscribe", { subscription: { endpoint: "https://evil.example/x" }, sources: ["hud-lpt"] })).status === 400, "an address that is not a browser push service is refused");
assert((await call("/radar/subscribe", { subscription: { endpoint: EP }, sources: ["nonsense"] })).status === 400, "at least one known report is required");
const sub = await call("/radar/subscribe", { subscription: { endpoint: EP }, sources: ["hud-lpt"] });
await call("/radar/subscribe", { subscription: { endpoint: EP2 }, sources: ["ginnie-iss"] });
assert(sub.status === 200 && sub.body.id.length === 32, "subscribe stores the device");
const stored = JSON.parse(store.get("radar:sub:" + sub.body.id));
assert(JSON.stringify(Object.keys(stored).sort()) === '["created","endpoint","sources"]', "only the push address, the reports and the date are stored");

hideRevisions = 2;                    // the ledger as it stood before the two newest entries
await tick();
assert(pushes.length === 0, "the first run records what exists and announces nothing");
hideRevisions = 0;                    // two revisions appear
await tick();
assert(pushes.length === 1 && pushes[0].url === EP, "a new revision in a chosen report reaches that device, and not the device watching another report");
const auth = pushes[0].headers.Authorization, m = /^vapid t=([^.]+)\.([^.]+)\.([^,]+), k=(.+)$/.exec(auth);
assert(m && m[4] === key.body.publicKey && !pushes[0].body, "the push is signed, names the public key and carries no content");
const pub = await crypto.subtle.importKey("raw", raw, { name: "ECDSA", namedCurve: "P-256" }, false, ["verify"]);
const d64 = s => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/")), c => c.charCodeAt(0));
assert(await crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, pub, d64(m[3]), new TextEncoder().encode(m[1] + "." + m[2])), "the signature verifies against the published key");
const claims = JSON.parse(new TextDecoder().decode(d64(m[2])));
assert(claims.aud === "https://fcm.googleapis.com" && claims.exp > Date.now() / 1000 && claims.exp < Date.now() / 1000 + 86400, "audience is the push service; expiry within a day");
const latest = await call("/radar/latest?e=" + sub.body.id);
assert(/printed figure changed/.test(latest.body.title) && /first printed/.test(latest.body.body), "the service worker is told which figure changed");
await tick();
assert(pushes.length === 1, "nothing is announced twice");

const t = await call("/radar/test", { endpoint: EP });
assert(t.body.ok && pushes.length === 2 && (await call("/radar/latest?e=" + sub.body.id)).body.title === "Figure Radar is on" && /changed/.test((await call("/radar/latest?e=" + sub.body.id)).body.title), "a test push shows the welcome once, then the latest event again");
assert((await call("/radar/test", { endpoint: EP })).status === 429, "one test a minute");
const st = await call("/radar/status");
assert(st.body.devices === 2 && st.body.by_report["hud-lpt"] === 1, "status publishes counts only");
const ev = await call("/radar/events");
assert(ev.body.events.length >= 5 && ev.body.events[0].at, "the event log is public, newest first");

pushStatus = 410; store.set("radar:state", JSON.stringify({ ...JSON.parse(store.get("radar:state")), seen: [] }));
await tick();
assert(!store.has("radar:sub:" + sub.body.id), "a device whose push address is gone is removed");
assert((await call("/radar/unsubscribe", { endpoint: EP2 })).body.ok && (await call("/radar/status")).body.devices === 0, "unsubscribe removes the device");
console.log("figure radar: key, subscribe, first run silent, revision announced once to the right device, signed empty push, test, status, cleanup all behave");
