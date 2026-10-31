// Offline tests with the documents in hand; no network. Run: node test.mjs
import { parse, verify, jcs } from "./index.mjs";
import fs from "node:fs";
const root = new URL("../../", import.meta.url).pathname;
const manifest = JSON.parse(fs.readFileSync(root + ".well-known/receipt.json", "utf8"));
const claim = JSON.parse(fs.readFileSync(root + "claims/state-oh-2025.json", "utf8"));
const history = JSON.parse(fs.readFileSync(root + "transparency/receipt-hash-history.json", "utf8"));
const nat = JSON.parse(fs.readFileSync(root + "claims/national-fha-denial-rate-2025.json", "utf8"));
let fails = 0; const t = (name, ok, extra = "") => { console.log((ok ? "PASS" : "FAIL"), name, extra); if (!ok) fails++; };
t("parse", JSON.stringify(parse("⟦FRC:state-oh-2025:23.0%:34beae06:s2610⟧")) === JSON.stringify({ prefix: "FRC", id: "state-oh-2025", value: "23.0%", hash8: "34beae06", channel: "s2610" }));
t("parse rejects junk", parse("FRC state-oh") === null);
t("jcs sorts nested keys", JSON.stringify(jcs({ b: { z: 1, a: 2 }, a: [ { y: 1, x: 2 } ] })) === '{"a":[{"x":2,"y":1}],"b":{"a":2,"z":1}}');
const cur = await verify(claim.receipt, { manifest, claim, history });
t("current receipt -> current", cur.status === "current" && cur.hash_rule === "jcs-sha256-8", cur.status);
const alt = await verify(claim.receipt.replace("23.0%", "32.0%"), { manifest, claim, history });
t("altered value -> hash-current-value-mismatch", alt.status === "hash-current-value-mismatch", alt.status);
const forged = await verify("⟦FRC:state-oh-2025:23.0%:deadbeef⟧", { manifest, claim, history });
t("unknown hash -> unrecognized", forged.status === "unrecognized", forged.status);
const old = (history.hashes["national-fha-denial-rate-2025"] || []).find(h => h !== nat.hash8);
if (old) { const st = await verify(`⟦FRC:national-fha-denial-rate-2025:21.7%:${old}⟧`, { manifest, claim: nat, history }); t("earlier issued hash -> stale", st.status === "stale", st.status); }
const wrong = await verify("⟦XYZ:state-oh-2025:23.0%:34beae06⟧", { manifest, claim, history });
t("other prefix -> unrecognized", wrong.status === "unrecognized" && /prefix/.test(wrong.reason));
console.log(fails ? `${fails} failing` : "all passing"); process.exit(fails ? 1 : 0);
