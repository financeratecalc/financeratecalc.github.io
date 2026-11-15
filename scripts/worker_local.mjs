// Run the server source (worker/index.js) locally: tool calls go through the real request handler, and every fetch the
// worker makes to financeratecalc.com is answered from the files in this repository. No network, no deploy.
//   import { callTool } from "./worker_local.mjs";  const r = await callTool("get_rule", {});
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const realFetch = globalThis.fetch;
globalThis.fetch = async (u, o) => {
  const url = new URL(typeof u === "string" ? u : u.url);
  if (url.hostname === "financeratecalc.com") {
    const f = path.join(ROOT, decodeURIComponent(url.pathname));
    if (!fs.existsSync(f)) return new Response("not found", { status: 404 });
    return new Response(fs.readFileSync(f), { status: 200, headers: { "content-type": f.endsWith(".json") ? "application/json" : "text/plain" } });
  }
  throw new Error("worker_local: network call blocked: " + url.href);
};
if (!globalThis.caches) globalThis.caches = { default: { match: async () => undefined, put: async () => {} } };
const tmp = path.join(os.tmpdir(), "frc-worker-local-" + process.pid + ".mjs");
fs.copyFileSync(path.join(ROOT, "worker/index.js"), tmp);
const mod = await import(pathToFileURL(tmp).href);
fs.unlinkSync(tmp);
const ctx = { waitUntil() {}, passThroughOnException() {} };
let id = 0;
export async function rpc(method, params) {
  const req = new Request("https://frc-mcp.local/", { method: "POST", headers: { "content-type": "application/json", accept: "application/json, text/event-stream", "user-agent": "frc-local-test" },
    body: JSON.stringify({ jsonrpc: "2.0", id: ++id, method, params }) });
  const res = await mod.default.fetch(req, {}, ctx);
  const text = await res.text();
  const m = text.match(/^data: (.*)$/m);
  return JSON.parse(m ? m[1] : text);
}
export async function callTool(name, args) {
  const r = await rpc("tools/call", { name, arguments: args || {} });
  if (r.error) throw new Error(JSON.stringify(r.error));
  const c = r.result.content[0].text;
  try { return JSON.parse(c); } catch { return { _text: c, _isError: !!r.result.isError }; }
}
export { realFetch };
