#!/usr/bin/env python3
"""Every published HTML path, for the 404 page's generic resolver (assets/404-paths.json).
Rerun when pages are added or removed."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {".git", ".venv", "node_modules", "rl-env", "examples", "fixtures", "worker", "spec", "api", "embed", "_data", "scripts", "eval", "transparency", "samples", "go", ".github"}
paths = []
for dp, dn, fn in os.walk(ROOT):
    r = os.path.relpath(dp, ROOT)
    if r != "." and r.split(os.sep)[0] in SKIP:
        dn[:] = []; continue
    for f in fn:
        if f.endswith(".html") and f != "404.html" and not f.startswith("google"):
            p = "/" + (f if r == "." else os.path.join(r, f).replace(os.sep, "/"))
            s = open(os.path.join(dp, f), encoding="utf-8", errors="ignore").read(3000)
            if 'http-equiv="refresh"' in s or "<title>Redirecting" in s:
                continue
            paths.append(p[:-5])
paths.sort()
json.dump(paths, open(os.path.join(ROOT, "assets", "404-paths.json"), "w"), separators=(",", ":"))
print(len(paths), "paths")
