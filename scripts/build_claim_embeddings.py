#!/usr/bin/env python3
"""Embeddings of every receipted claim's canonical sentence, for check-answer's in-browser meaning match.

Model: sentence-transformers/all-MiniLM-L6-v2 (mean pooling, L2-normalised), the same weights the page loads through
transformers.js (Xenova/all-MiniLM-L6-v2, quantised). Output assets/claim-embeddings.json: ids, labels, values and
a base64 Float32 matrix (386 x 384). Runs in CI; the browser never calls a server for this.

    python3 scripts/build_claim_embeddings.py
"""
import base64
import glob
import json
import os

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "claim-embeddings.json")


def main():
    docs = []
    for p in sorted(glob.glob(os.path.join(ROOT, "claims", "*.json"))):
        if p.endswith(".contract.json") or p.endswith("index.json"):
            continue
        d = json.load(open(p, encoding="utf-8"))
        if "receipt" not in d or "id" not in d:
            continue
        cp = os.path.join(ROOT, "claims", f"{d['id']}.contract.json")
        K = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {}
        tmpl = (K.get("canonical_claim") or {}).get("template")
        sent = tmpl.replace("{value}", d["display_value"]) if tmpl else f"{d['id']}: {d['display_value']}"
        docs.append((d["id"], d["display_value"], sent, d.get("verify_url"), d.get("canonical_url")))
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    E = model.encode([s for _, _, s, _, _ in docs], normalize_embeddings=True, batch_size=64, show_progress_bar=False).astype(np.float32)
    out = {"model": "sentence-transformers/all-MiniLM-L6-v2", "browser_model": "Xenova/all-MiniLM-L6-v2", "dim": int(E.shape[1]), "n": len(docs),
           "ids": [d[0] for d in docs], "values": [d[1] for d in docs], "sentences": [d[2] for d in docs], "verify": [d[3] for d in docs], "claim": [d[4] for d in docs],
           "matrix_b64": base64.b64encode(E.tobytes()).decode("ascii"),
           "note": "Row i is the L2-normalised embedding of sentences[i]. Cosine similarity = dot product."}
    json.dump(out, open(OUT, "w", encoding="utf-8"))
    print(f"{len(docs)} claims, {os.path.getsize(OUT):,} bytes -> {OUT}")


if __name__ == "__main__":
    main()
