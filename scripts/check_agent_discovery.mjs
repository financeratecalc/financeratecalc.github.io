// The front door for agents, through the server source with the static host played by the files in this repository:
// Link headers on the home page, Markdown on request, the API catalog, the server card, the skills index and its digests.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath, pathToFileURL } from "node:url";
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const assert = (c, m) => { if (!c) { console.error("FAIL:", m); process.exit(1); } };
const types = { ".html": "text/html; charset=utf-8", ".md": "text/markdown; charset=utf-8", ".json": "application/json" };
let originDown = false;
globalThis.fetch = async (u) => {
  const url = new URL(typeof u === "string" ? u : u.url);
  if (originDown) throw new Error("origin unreachable");
  if (url.hostname !== "financeratecalc.com") throw new Error("network call blocked: " + url.href);
  const rel = url.pathname === "/" ? "index.html" : url.pathname.slice(1), f = path.join(ROOT, rel);
  if (!fs.existsSync(f)) return new Response("not found", { status: 404 });
  return new Response(fs.readFileSync(f), { status: 200, headers: { "content-type": types[path.extname(f)] || "application/octet-stream", "vary": "Accept-Encoding" } });
};
if (!globalThis.caches) globalThis.caches = { default: { match: async () => undefined, put: async () => {} } };
const tmp = path.join(os.tmpdir(), "frc-door-" + process.pid + ".mjs");
fs.copyFileSync(path.join(ROOT, "worker/index.js"), tmp);
const mod = (await import(pathToFileURL(tmp).href)).default; fs.unlinkSync(tmp);
const get = (u, headers = {}, method = "GET") => mod.fetch(new Request(u, { method, headers }), {}, { passThroughOnException() {} });
const SITE = "https://financeratecalc.com";

// 1. A browser gets the page the static host serves, byte for byte, with the Link headers added.
let r = await get(SITE + "/", { accept: "text/html,application/xhtml+xml,*/*;q=0.8" });
const html = await r.text();
assert(r.status === 200 && html === fs.readFileSync(path.join(ROOT, "index.html"), "utf8"), "home page is not the static file unchanged");
assert(/text\/html/.test(r.headers.get("content-type")), "home page media type");
const link = r.headers.get("link") || "";
const links = [...link.matchAll(/<([^>]+)>;\s*rel="([^"]+)"/g)].map(m => ({ href: m[1], rel: m[2] }));
for (const rel of ["api-catalog", "service-desc", "service-doc", "agent-skills", "mcp-server-card", "alternate", "describedby", "license"]) assert(links.some(l => l.rel === rel), "Link header lacks rel=" + rel);
assert(/Accept/.test(r.headers.get("vary") || ""), "Vary: Accept missing on the page");

// 2. Every Link target exists: as a file in the repository, or as an address this code answers.
const answered = new Set(["/.well-known/api-catalog", "/.well-known/mcp/server-card.json"]);
for (const l of links) assert(answered.has(l.href) || fs.existsSync(path.join(ROOT, l.href.slice(1))), "Link target missing: " + l.href);

// 3. Markdown on request: the generated file, labelled as Markdown; q-values and other types do not confuse it.
r = await get(SITE + "/", { accept: "text/markdown, text/html;q=0.8" });
const md = await r.text();
assert(r.status === 200 && /^text\/markdown/.test(r.headers.get("content-type")), "markdown not served on request");
assert(md === fs.readFileSync(path.join(ROOT, "index.md"), "utf8") && md.includes("# Numbers in the dark"), "markdown is not index.md");
assert(/Accept/.test(r.headers.get("vary") || ""), "Vary: Accept missing on markdown");
r = await get(SITE + "/", { accept: "text/markdown" }, "HEAD");
assert(r.status === 200 && (await r.text()) === "", "HEAD with markdown");
r = await get(SITE + "/", { accept: "*/*" });
assert(/text\/html/.test(r.headers.get("content-type")), "*/* must stay HTML");

// 4. The Markdown says what the page says: every receipt and every heading of the page is in it.
const receipts = [...new Set([...html.replace(/<script[\s\S]*?<\/script>/g, "").matchAll(/<code>(⟦FRC:[^⟧<]+⟧)<\/code>/g)].map(m => m[1]))];
assert(receipts.length >= 3 && receipts.every(x => md.includes(x)), "a receipt on the page is missing from the Markdown");
const heads = [...html.matchAll(/<h2[^>]*>([\s\S]*?)<\/h2>/g)].map(m => m[1].replace(/<[^>]+>/g, "").replace(/&rsquo;/g, "’").replace(/&mdash;/g, "—").replace(/&amp;/g, "&").trim());
assert(heads.length >= 5 && heads.every(h => md.includes("## " + h)), "a heading on the page is missing from the Markdown: " + heads.find(h => !md.includes("## " + h)));

// 5. The API catalog is an RFC 9727 linkset with the right media type, and it names only things that exist.
r = await get(SITE + "/.well-known/api-catalog");
assert(r.status === 200 && /^application\/linkset\+json/.test(r.headers.get("content-type")) && /rfc9727/.test(r.headers.get("content-type")), "api-catalog media type");
const cat = await r.json();
assert(Array.isArray(cat.linkset) && cat.linkset.length === 2 && cat.linkset.every(e => e.anchor && e["service-desc"] && e["service-doc"]), "api-catalog shape");
for (const e of cat.linkset) for (const k of ["service-desc", "service-doc", "service-meta"]) for (const t of e[k] || []) {
  const u = new URL(t.href);
  if (u.hostname === "financeratecalc.com" && !answered.has(u.pathname)) assert(fs.existsSync(path.join(ROOT, u.pathname.slice(1))), "api-catalog names a missing file: " + t.href);
}
const spec = JSON.parse(fs.readFileSync(path.join(ROOT, "openapi.json"), "utf8"));
assert(spec.openapi && spec.paths, "openapi.json is not an OpenAPI description");

// 6. The server card on the site's domain is the one the server itself gives, and says where the server is and that it needs no login.
r = await get(SITE + "/.well-known/mcp/server-card.json");
const card = await r.json();
assert(card.serverInfo && card.endpoint === "https://frc-mcp.ziyetis.workers.dev" && card.transport === "streamable-http" && card.auth === "none", "server card");

// 7. Skills index: schema 0.2.0, each digest is the sha256 of the file served beside it, each file is the one in /skills.
const idx = JSON.parse(fs.readFileSync(path.join(ROOT, ".well-known/agent-skills/index.json"), "utf8"));
assert(idx.$schema === "https://schemas.agentskills.io/discovery/0.2.0/schema.json" && idx.skills.length >= 1, "skills index");
for (const s of idx.skills) {
  const f = path.join(ROOT, new URL(s.url).pathname.slice(1)), raw = fs.readFileSync(f);
  assert(s.type === "skill-md" && s.digest === "sha256:" + crypto.createHash("sha256").update(raw).digest("hex"), "digest of " + s.name);
  assert(raw.equals(fs.readFileSync(path.join(ROOT, "skills", s.name, "SKILL.md"))), s.name + " differs from /skills");
  assert(new RegExp("^---\\nname: " + s.name + "\\n").test(raw.toString("utf8")), s.name + " frontmatter");
}

// 8. Nothing else changes: other paths on the site host are not touched by the front door, and the server's own root is still the server.
r = await get("https://frc-mcp.ziyetis.workers.dev/", { accept: "text/markdown" });
assert(!/^text\/markdown/.test(r.headers.get("content-type") || ""), "the MCP endpoint must not turn into the home page");

// 9. If the static host cannot be reached, the failure is the static host's, not a new one made here.
originDown = true;
let threw = false; try { await get(SITE + "/", { accept: "text/markdown" }); } catch { threw = true; }
assert(threw, "an unreachable origin should surface as the origin's own failure");
console.log(`agent front door: ${links.length} Link relations, markdown ${md.length} chars with ${receipts.length} receipts and ${heads.length} headings, catalog of ${cat.linkset.length} interfaces, ${idx.skills.length} skill(s) with matching digest`);
