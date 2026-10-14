#!/usr/bin/env python3
"""Evidence footnote on every template page that carries no receipt of its own.

Each page gets one short, static block (readable without JavaScript, by people, crawlers
and answer-engine fetchers alike):
  - one public-record figure related to the page's subject, chosen by fixed rules:
      metro page with a passport  -> that metro's lender-gap claim
      page about a place          -> that state's 2025 FHA denial rate
      anything else               -> the national 2025 FHA denial rate
  - the figure's receipt  ⟦FRC:<id>:<value>:<hash8>:f<yymm>⟧  (channel f = evidence footnote),
    computed exactly as the worker's /verify does (rl-env/frc_citation/verify_offline.py)
  - Verify, cite card (passport claims only), passport/API JSON, and the MCP line for agents
  - the scope of the receipt: it covers this one figure, not the page's own estimates

Idempotent: the block lives between <!--FRC-FOOTNOTE:id--> ... <!--/FRC-FOOTNOTE--> and is
replaced on each run. A block whose receipt is still current keeps its original issue month,
so reruns do not rewrite three thousand pages for nothing.

Never placed on: pages that already show a receipt, redirects, the 404 page, legal pages,
embed fragments. Place detection is conservative: a city name that belongs to more than one
state, or a page that names more than one state, falls back to the national figure; a wrong
state would be worse than a general one.

Usage:  python3 scripts/build_evidence_footnotes.py [--dry-run] [--report eval/evidence-footnotes.json]
"""
import datetime, glob, html as H, json, os, re, sys, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "rl-env"))
from frc_citation.verify_offline import Verifier, sha8  # noqa: E402

V = Verifier(ROOT)
SITE = "https://financeratecalc.com"
MCP = "https://frc-mcp.ziyetis.workers.dev"
BLOCK_RE = re.compile(r"\n?<!--FRC-FOOTNOTE:[a-z0-9-]+-->.*?<!--/FRC-FOOTNOTE-->\n?", re.S)
OLD_RECEIPT_RE = re.compile(r"⟦FRC:([a-z0-9-]+):([^:⟧]+):([a-f0-9]{8}):f(\d{4})⟧")

SKIP_DIRS = {".git", ".venv", "node_modules", "samples", "go", "api", "embed", "examples", "rl-env", "fixtures", "worker", "_data", "spec", "claims"}
SKIP_FILES = {"404.html", "privacy.html", "privacy-policy.html", "terms.html", "terms-of-service.html", "affiliate-disclosure.html",
              "cookie-policy.html", "contact.html", "verify.html", "cite.html", "use-frc.html", "embed.html", "google", "offline.html"}

STATES = {}
for f in glob.glob(os.path.join(ROOT, "api", "state", "*.json")):
    d = json.load(open(f, encoding="utf-8"))
    STATES[d["state"]] = d
NAMES = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado", "CT": "Connecticut",
         "DE": "Delaware", "DC": "the District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
         "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
         "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
         "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
         "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
         "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
         "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
         "PR": "Puerto Rico"}
NAME_TO_CODE = {v.lower(): k for k, v in NAMES.items() if k != "DC"}

# Principal-city -> state from the metro names in the published record ("Charlotte-Concord-Gastonia, NC-SC" -> Charlotte: NC).
CITY = {}
for f in glob.glob(os.path.join(ROOT, "api", "metro", "*.json")):
    m = json.load(open(f, encoding="utf-8")).get("metro", "")
    if "," not in m:
        continue
    cities, sts = m.rsplit(",", 1)
    st = sts.strip().split("-")[0].strip()
    if st not in STATES:
        continue
    # principal city only (the first name in the metro title), never a word that is part of a state name
    c = cities.split("-")[0].strip().lower()
    if len(c) >= 4 and st != "PR" and not any(c in n for n in NAME_TO_CODE):
        CITY.setdefault(c, set()).add(st)
METRO_SLUG = {}
for f in glob.glob(os.path.join(ROOT, "api", "metro", "*.json")):
    _d = json.load(open(f, encoding="utf-8"))
    if _d.get("metro") and _d.get("slug"):
        METRO_SLUG[_d["metro"]] = _d["slug"]
# Common short names the metro list spells differently.
for c, st in {"nyc": "NY", "new york city": "NY", "los angeles": "CA", "san francisco": "CA", "washington dc": "DC", "frisco": "TX", "plano": "TX",
              "overland park": "KS", "asheville": "NC", "colorado springs": "CO", "salt lake city": "UT", "buckhead": "GA"}.items():
    CITY.setdefault(c, set()).add(st)


def chan(prev=None):
    if prev:
        return "f" + prev
    d = datetime.datetime.now(datetime.timezone.utc)
    return f"f{str(d.year)[2:]}{d.month:02d}"


ZIP3 = [(5, 5, "NY"), (6, 9, "PR"), (10, 27, "MA"), (28, 29, "RI"), (30, 38, "NH"), (39, 49, "ME"), (50, 54, "VT"), (55, 55, "MA"),
        (56, 59, "VT"), (60, 69, "CT"), (70, 89, "NJ"), (100, 149, "NY"), (150, 196, "PA"), (197, 199, "DE"), (200, 200, "DC"),
        (201, 201, "VA"), (202, 205, "DC"), (206, 219, "MD"), (220, 246, "VA"), (247, 268, "WV"), (270, 289, "NC"), (290, 299, "SC"),
        (300, 319, "GA"), (320, 339, "FL"), (341, 349, "FL"), (350, 369, "AL"), (370, 385, "TN"), (386, 397, "MS"), (398, 399, "GA"),
        (400, 427, "KY"), (430, 459, "OH"), (460, 479, "IN"), (480, 499, "MI"), (500, 528, "IA"), (530, 549, "WI"), (550, 567, "MN"),
        (570, 577, "SD"), (580, 588, "ND"), (590, 599, "MT"), (600, 629, "IL"), (630, 658, "MO"), (660, 679, "KS"), (680, 693, "NE"),
        (700, 714, "LA"), (716, 729, "AR"), (730, 749, "OK"), (750, 799, "TX"), (800, 816, "CO"), (820, 831, "WY"), (832, 838, "ID"),
        (840, 847, "UT"), (850, 865, "AZ"), (870, 884, "NM"), (885, 885, "TX"), (889, 898, "NV"), (900, 961, "CA"), (967, 968, "HI"),
        (970, 979, "OR"), (980, 994, "WA"), (995, 999, "AK")]


def zip_state(z):
    n = int(z[:3])
    for a, b_, st in ZIP3:
        if a <= n <= b_:
            return st
    return None


def state_names_in(low):
    out = set()
    for name, code in NAME_TO_CODE.items():
        for m in re.finditer(r"\b" + re.escape(name) + r"\b", low):
            pre = low[max(0, m.start() - 8):m.start()]
            post = low[m.end():m.end() + 8]
            if name == "washington" and (re.search(r"(mt|mount|port|fort|lake)\.? $", pre) or post.startswith((" dc", ", dc", " d.c", " heights", " park", " square"))):
                continue
            if name == "kansas" and post.startswith(" city"):
                continue
            if name == "idaho" and post.startswith(" springs"):
                continue
            if name == "indiana" and (post.startswith("polis") or post.startswith(" county")):
                continue
            out.add(code)
    # "virginia" inside "west virginia" is not a second state
    if "WV" in out and not re.search(r"(?<!west )\bvirginia\b", low):
        out.discard("VA")
    if "district of columbia" in low or re.search(r"washington,? d\.?c\b", low):
        out.add("DC")
    return out


def detect_state(title, fname, rel=""):
    """Return (state_code, rule) or (None, reason). Conservative by construction: any conflict -> national."""
    t = title
    codes = set(re.findall(r",\s*([A-Z]{2})\b", t)) & set(STATES)
    if fname.endswith("-fha-denial-rate.html") or fname.endswith("-approval-rate.html"):
        return None, "lender_page"
    zm = re.match(r"(?:market/|mortgage-zip-)(\d{5})\.html$", rel)
    if zm:
        zs = zip_state(zm.group(1))
        if zs and zs in STATES and (not codes or codes == {zs}):
            return zs, "zip_prefix"
        return None, "zip_conflict_or_unknown"
    if len(codes) > 1:
        return None, "several_states_in_title"
    if len(codes) == 1:
        return codes.pop(), "title_state_code"
    fm = re.search(r"(?:-in-[a-z-]+|^neighborhood-[a-z-]+)-([a-z]{2})\.html$", fname)
    if fm and fm.group(1).upper() in STATES:
        return fm.group(1).upper(), "filename_state_code"
    low = (t + " " + fname[:-5].replace("-", " ")).lower()
    names = state_names_in(low)
    if len(names) == 1:
        return names.pop(), "state_name"
    if len(names) > 1:
        return None, "several_states"
    hits = {c: sts for c, sts in CITY.items() if re.search(r"\b" + re.escape(c) + r"\b", low)}
    for c in list(hits):
        if any(c != o and c in o for o in hits):
            hits.pop(c)
    if not hits:
        return None, "no_place"
    if any(len(v) > 1 for v in hits.values()):
        return None, "ambiguous_city"
    cand = set().union(*hits.values())
    if len(cand) == 1:
        return cand.pop(), "city_map"
    return None, "several_states"


def fmt_int(n):
    return f"{int(n):,}"


def choose(rel, title, body=""):
    """Return (claim_id, sentence_template, kind, rule). {R} marks where the receipt goes."""
    base = os.path.basename(rel)
    if rel.startswith("metro/"):
        slug = base[:-5]
        cid = f"metro-gap-{slug}-2025"
        if os.path.exists(os.path.join(ROOT, "claims", cid + ".json")):
            C = json.load(open(os.path.join(ROOT, "claims", cid + ".contract.json"), encoding="utf-8"))
            t = C["canonical_claim"]["template"]
            m = re.search(r"([0-9.]+)( percentage points)", t)
            if m:
                return cid, t[:m.end(1)] + " {R}" + t[m.end(1):], "metro_gap", "metro_passport"
    # a page that already shows a metro box ("…% of FHA applications denied in <Metro>, 2025") gets that metro's gap claim
    mm = re.search(r"of FHA applications denied in ([^<>]+?), 2025", body or "")
    if mm and mm.group(1) in METRO_SLUG:
        cid = f"metro-gap-{METRO_SLUG[mm.group(1)]}-2025"
        if os.path.exists(os.path.join(ROOT, "claims", cid + ".json")):
            C = json.load(open(os.path.join(ROOT, "claims", cid + ".contract.json"), encoding="utf-8"))
            t = C["canonical_claim"]["template"]
            m = re.search(r"([0-9.]+)( percentage points)", t)
            if m:
                return cid, t[:m.end(1)] + " {R}" + t[m.end(1):], "metro_gap", "metro_box_on_page"
    st, rule = detect_state(title, base, rel)
    if st:
        d = STATES[st]
        nm = NAMES.get(st, st)
        return (f"state-{st.lower()}-2025",
                f"In 2025, {d['denial_rate_pct']:.1f}% {{R}} of decisioned FHA applications in {nm} were denied "
                f"({fmt_int(d['denials'])} of {fmt_int(d['decisioned_applications'])}; national rate 22.1%).",
                "state", rule)
    return ("national-fha-denial-rate-2025",
            "In 2025, 22.1% {R} of decisioned FHA applications were denied (actions 1,2,3; loan_type 2).",
            "national", rule)


def block(cid, sentence, r, kind):
    q = urllib.parse.quote(r)
    has_passport = os.path.exists(os.path.join(ROOT, "claims", cid + ".json"))
    data_url = f"{SITE}/claims/{cid}.json" if has_passport else f"{SITE}/api/state/{cid[6:8]}.json" if kind == "state" else f"{SITE}/api/index.json"
    A = 'style="color:inherit;text-decoration:underline"'
    links = [f'<a {A} href="{SITE}/verify.html?r={q}">Verify</a>']
    if has_passport:
        links.append(f'<a {A} href="{SITE}/cite.html?id={cid}">Cite card</a>')
    links.append(f'<a {A} href="{data_url}">{"Passport" if has_passport else "Data"} (JSON)</a>')
    links.append(f'<a {A} href="{SITE}/methodology.html">Method</a>')
    rx = f'<span class="frc-fn-r" style="font-family:\'DM Mono\',ui-monospace,monospace;font-size:.92em;overflow-wrap:anywhere;word-break:break-all">{H.escape(r)}</span>'
    body = H.escape(sentence).replace("{R}", rx)
    st = "max-width:680px;margin:28px auto 72px;padding:12px 16px;border-top:1px solid rgba(127,127,127,.35);font-size:13px;line-height:1.55;opacity:.9;font-family:inherit;color:inherit;box-sizing:border-box"
    return (f'\n<!--FRC-FOOTNOTE:{cid}--><aside class="frc-footnote" data-frc-footnote="{cid}" data-receipt="{H.escape(r)}" aria-label="Evidence footnote" style="{st}">'
            f'<p style="margin:0 0 6px"><b>Evidence footnote.</b> {body} '
            f'Source: FinanceRateCalc analysis of the public CFPB HMDA 2025 record; historical aggregate only. CC BY 4.0.</p>'
            f'<p style="margin:0 0 6px">{" &middot; ".join(links)}</p>'
            f'<p style="margin:0 0 6px;font-size:12px">The receipt covers this one figure only, not the estimates or calculator results on this page. '
            f'It is not a prediction for any application; FHA only, reverse mortgages excluded. If the figure is ever corrected, the receipt stops verifying as current.</p>'
            f'<p style="margin:0;font-size:12px">For AI agents: the same figure with its use contract and a sentence checker, over MCP at <code style="overflow-wrap:anywhere;word-break:break-all">{MCP}</code> (no key) &middot; '
            f'<a style="color:inherit;text-decoration:underline" href="{SITE}/use-frc.html">setup</a></p>'
            f'</aside><!--/FRC-FOOTNOTE-->\n')


def pages():
    for dp, dns, fns in os.walk(ROOT):
        rel_dir = os.path.relpath(dp, ROOT)
        top = rel_dir.split(os.sep)[0]
        if rel_dir != "." and (top in SKIP_DIRS or top.startswith(".")):
            dns[:] = []
            continue
        for fn in fns:
            if fn.endswith(".html") and fn not in SKIP_FILES:
                yield os.path.normpath(os.path.join(rel_dir, fn)).replace(os.sep, "/")


def main():
    dry = "--dry-run" in sys.argv
    rep_path = None
    if "--report" in sys.argv:
        rep_path = sys.argv[sys.argv.index("--report") + 1]
    cache, stats, skipped, by_rule, written, samples, conflicts = {}, {}, {}, {}, 0, {}, []
    for rel in sorted(pages()):
        p = os.path.join(ROOT, rel)
        src = open(p, encoding="utf-8", errors="strict").read()
        old = BLOCK_RE.search(src)
        rest = BLOCK_RE.sub("\n", src) if old else src
        reason = None
        if "⟦FRC:" in rest:
            reason = "has_own_receipt"
        elif re.search(r'http-equiv=["\']refresh', rest, re.I) or "<title>Redirecting" in rest:
            reason = "redirect"
        elif "</body>" not in rest:
            reason = "no_body_end"
        elif "<!-- frc-no-footnote -->" in rest:
            reason = "opted_out"
        if reason:
            skipped[reason] = skipped.get(reason, 0) + 1
            if old and not dry:
                open(p, "w", encoding="utf-8").write(rest)
            continue
        tm = re.search(r"<title>(.*?)</title>", rest, re.S)
        title = H.unescape(tm.group(1)).strip() if tm else ""
        body = " ".join(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", rest, flags=re.S)).split())
        cid, sentence, kind, rule = choose(rel, title, H.unescape(body))
        if cid not in cache:
            cur, obj = V.claim_object(cid)
            cache[cid] = (cur, sha8(obj))
        cur, h = cache[cid]
        prev = None
        if old:
            m = OLD_RECEIPT_RE.search(old.group(0))
            if m and m.group(1) == cid and m.group(2) == cur and m.group(3) == h:
                prev = m.group(4)
        r = f"⟦FRC:{cid}:{cur}:{h}:{chan(prev)}⟧"
        # a page whose own headline states a different value for the same figure gets no footnote:
        # that is a publisher inconsistency to fix in the page, not something to paper over
        tv = re.search(r"denial rate[^%|]*?(\d+\.\d)%", title, re.I)
        if not (tv and kind in ("state", "national")) and kind == "state":
            nm = re.escape(NAMES.get(cid[6:8].upper(), "~"))
            tv = (re.search(nm + r"(?![-\w])[^.%]{0,80}?(\d+\.\d)%[^.]{0,40}?(?:denied|denial)", body)
                  or re.search(r"(\d+\.\d)%[^.]{0,60}?(?:denied|denial)[^.%]{0,40}?\b" + nm + r"(?![-\w])", body))
        if tv and kind in ("state", "national") and tv.group(1) + "%" != cur:
            skipped["page_value_conflict"] = skipped.get("page_value_conflict", 0) + 1
            conflicts.append({"page": rel, "page_value": tv.group(1) + "%", "claim": cid, "claim_value": cur})
            if old and not dry:
                open(p, "w", encoding="utf-8").write(rest)
            continue
        # the receipt's value must be the value the sentence states
        if cur.replace("pp", "") not in sentence.replace("{R}", ""):
            skipped["value_not_in_sentence"] = skipped.get("value_not_in_sentence", 0) + 1
            continue
        b = block(cid, sentence, r, kind)
        i = rest.rfind("</body>")
        new = rest[:i].rstrip("\n") + b + rest[i:]
        stats[kind] = stats.get(kind, 0) + 1
        by_rule[rule] = by_rule.get(rule, 0) + 1
        samples.setdefault(kind + ":" + rule, (rel, title[:90], cid))
        if new != src:
            written += 1
            if not dry:
                open(p, "w", encoding="utf-8").write(new)
    out = {"generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"), "placed": stats, "placement_rule": by_rule,
           "skipped": skipped, "page_value_conflicts": conflicts, "files_changed": written, "dry_run": dry,
           "examples": {k: {"page": v[0], "title": v[1], "claim": v[2]} for k, v in sorted(samples.items())},
           "receipts": {k: f"⟦FRC:{k}:{v[0]}:{v[1]}:f…⟧" for k, v in sorted(cache.items())}}
    print(json.dumps({k: out[k] for k in ("placed", "placement_rule", "skipped", "page_value_conflicts", "files_changed", "dry_run")}, indent=1))
    if rep_path:
        json.dump(out, open(os.path.join(ROOT, rep_path), "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
