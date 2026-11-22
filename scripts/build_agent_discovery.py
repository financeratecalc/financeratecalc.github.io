#!/usr/bin/env python3
"""Files an agent looks for before it reads a page, built from what the site already publishes. Nothing new is said here.

  index.md                                   the home page as Markdown: same headings, sentences, tables and links as index.html.
                                             The worker answers `Accept: text/markdown` on / with it.
  .well-known/agent-skills/index.json        Agent Skills discovery index (schema 0.2.0): one entry per skill in /skills,
  .well-known/agent-skills/<name>/SKILL.md   with the sha256 of the copy served next to it.

  python3 scripts/build_agent_discovery.py           write
  python3 scripts/build_agent_discovery.py --check   exit 1 if any of them is out of date
"""
import hashlib, html, json, os, re, sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://financeratecalc.com"
SKIP = {"script", "style", "form", "nav", "button", "svg", "noscript", "head", "template"}
BLOCK = {"p", "div", "section", "ul", "ol", "table", "thead", "tbody", "header", "footer", "main", "small"}
VOID = {"br", "img", "input", "meta", "link", "hr", "source", "wbr"}


class Md(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.buf, self.skip, self.href, self.cell, self.row, self.rows = [], [], 0, [], None, None, None
        self.item = False

    def text(self):
        t = re.sub(r"\s+", " ", "".join(self.buf)).strip(); self.buf = []; return t

    def flush(self, prefix=""):
        t = self.text()
        if t: self.out.append(prefix + t)

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            if tag == "br" and not self.skip: self.buf.append(" ")
            return
        if self.skip or tag in SKIP: self.skip += 1; return
        a = dict(attrs)
        if tag in ("h1", "h2", "h3", "h4"): self.flush()
        elif tag == "li": self.flush("- " if self.item else ""); self.item = True
        elif tag == "table": self.flush(); self.rows = []
        elif tag == "tr": self.row = []
        elif tag in ("td", "th"): self.buf = []
        elif tag in BLOCK: self.flush("- " if self.item else ""); self.item = self.item and tag not in ("ul", "ol")
        elif tag == "a": self.href.append(a.get("href") or ""); self.buf.append("[")
        elif tag in ("b", "strong"): self.buf.append("**")
        elif tag == "code": self.buf.append("`")
        elif tag == "span": self.buf.append(" ")

    def handle_endtag(self, tag):
        if tag in VOID: return
        if self.skip: self.skip -= 1; return
        if tag in ("h1", "h2", "h3", "h4"):
            t = self.text()
            if t: self.out.append("#" * int(tag[1]) + " " + t)
        elif tag == "li": self.flush("- "); self.item = False
        elif tag in ("td", "th"):
            if self.row is not None: self.row.append(self.text().replace("|", "\\|"))
        elif tag == "tr":
            if self.rows is not None and self.row: self.rows.append(self.row)
            self.row = None
        elif tag == "table":
            if self.rows:
                n = max(len(r) for r in self.rows)
                lines = ["| " + " | ".join(r + [""] * (n - len(r))) + " |" for r in self.rows]
                lines.insert(1, "|" + " --- |" * n)
                self.out.append("\n".join(lines))
            self.rows = None
        elif tag in BLOCK: self.flush("- " if self.item else "")
        elif tag == "a":
            h = self.href.pop() if self.href else ""
            if h.startswith("/"): h = BASE + h
            self.buf.append("](" + h.replace(" ", "%20") + ")")
        elif tag in ("b", "strong"): self.buf.append("**")
        elif tag == "code": self.buf.append("`")

    def handle_data(self, d):
        if not self.skip: self.buf.append(d)


def home_markdown():
    src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    title = html.unescape(re.search(r"<title>(.*?)</title>", src, re.S).group(1)).strip()
    body = src[src.index("<h1"):]
    p = Md(); p.feed(body); p.close(); p.flush()
    blocks, md = [b for b in p.out if b and b not in ("- ",)], []
    for i, b in enumerate(blocks):                       # list items sit on consecutive lines, everything else gets a blank line
        md.append(b + ("\n" if b.startswith("- ") and i + 1 < len(blocks) and blocks[i + 1].startswith("- ") else "\n\n"))
    head = (f"---\ntitle: {json.dumps(title, ensure_ascii=False)}\nurl: {BASE}/\n"
            "note: The home page of financeratecalc.com as Markdown, generated from the same file as the HTML page. "
            "The receipt checker form and the interactive field of figures are left out; the receipts they show are in the text below.\n---\n\n")
    return head + "".join(md).rstrip() + "\n"


def skills():
    files, entries = {}, []
    sdir = os.path.join(ROOT, "skills")
    for name in sorted(os.listdir(sdir)):
        f = os.path.join(sdir, name, "SKILL.md")
        if not os.path.isfile(f): continue
        raw = open(f, "rb").read(); text = raw.decode("utf-8")
        fm = re.match(r"---\n(.*?)\n---\n", text, re.S)
        if not fm: sys.exit(f"{f}: no frontmatter")
        desc = re.search(r"^description:\s*(.+)$", fm.group(1), re.M).group(1).strip()
        nm = re.search(r"^name:\s*(.+)$", fm.group(1), re.M).group(1).strip()
        if nm != name: sys.exit(f"{f}: name '{nm}' does not match its folder")
        files[f".well-known/agent-skills/{name}/SKILL.md"] = raw
        entries.append({"name": name, "type": "skill-md", "description": desc,
                        "url": f"{BASE}/.well-known/agent-skills/{name}/SKILL.md", "digest": "sha256:" + hashlib.sha256(raw).hexdigest()})
    idx = {"$schema": "https://schemas.agentskills.io/discovery/0.2.0/schema.json", "skills": entries}
    files[".well-known/agent-skills/index.json"] = (json.dumps(idx, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    return files


def build():
    files = skills(); files["index.md"] = home_markdown().encode("utf-8"); return files


def write():
    for rel, data in build().items():
        f = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(f), exist_ok=True)
        open(f, "wb").write(data)
    return len(build())


if __name__ == "__main__":
    if "--check" in sys.argv:
        stale = [rel for rel, data in build().items() if not os.path.isfile(os.path.join(ROOT, rel)) or open(os.path.join(ROOT, rel), "rb").read() != data]
        if stale: print("out of date:", ", ".join(stale)); sys.exit(1)
        print("agent discovery files are current")
    else:
        print(f"wrote {write()} agent discovery files")
