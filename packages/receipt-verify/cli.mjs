#!/usr/bin/env node
import { verify } from "./index.mjs";
const [receipt, manifest = "https://financeratecalc.com/.well-known/receipt.json"] = process.argv.slice(2);
if (!receipt) { console.error("usage: receipt-verify '⟦PREFIX:id:value:hash8⟧' [manifest-url]"); process.exit(2); }
const r = await verify(receipt, { manifest });
console.log(JSON.stringify(r, null, 1));
process.exit(r.status === "current" ? 0 : 1);
