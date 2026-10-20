#!/usr/bin/env python3
"""One page, one value: every figure for the same quantity on a state or lender page must agree
with the data file and the receipt.

Found 2026-10-20 by three outside readers (a denied borrower, a lender compliance officer, a
reporter): the Ohio page said 23.0% in the receipt and 22.9% in the direct answer; the
CrossCountry page said 6.2% eight times and 6.5% in the hero box. The 1 October stale-page fix
replaced the headline sentence and left the other spots. This check reads every state and lender
page and compares:

  state pages   receipt value, api/state/<st>.json, the "<rate> was <span class=mono>" sentence
  lender pages  headline sentence, receipt, hero <div class="big">, and the
                "loosened/tightened N pp since 2018" line against the 2018 card

Run without --fix in CI (exit 1 on any disagreement). With --fix, rewrite the stale spots to the
data value and log every replacement to eval/page-value-fix-<date>.json.
"""
import datetime, glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def state_pages():
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "fha-denial-rates-*.html"))):
        h = open(f, encoding="utf-8").read()
        r = re.search(r'data-receipt="⟦FRC:state-([a-z]{2})-2025:([\d.]+)%', h)
        if not r:
            continue
        st, rv = r.groups()
        api = f"{json.load(open(os.path.join(ROOT, 'api', 'state', st + '.json')))['denial_rate_pct']:.1f}"
        m = re.search(r'FHA denial rate in 2025 was <span class="mono">([\d.]+)%</span>', h)
        spots = {"receipt": rv, "api": api}
        if m:
            spots["direct_answer"] = m.group(1)
        if len(set(spots.values())) > 1:
            out.append((f, h, api, spots, m))
    return out


def lender_pages():
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "*-fha-denial-rate.html"))):
        h = open(f, encoding="utf-8").read()
        hl = re.search(r"FHA denial rate in 2025 was ([\d.]+)%", h)
        rc = re.search(r'data-receipt="⟦FRC:lender-[a-z0-9-]+-2025:([\d.]+)%', h)
        if not (hl or rc):
            continue
        big = re.search(r'<div class="big">([\d.]+)%</div>', h)
        pp = re.search(r"(loosened|tightened) ([\d.]+)pp since 2018", h)
        y18 = re.search(r'2018 rate</div><div class="v">([\d.]+)%', h)
        spots = {}
        if hl:
            spots["headline"] = hl.group(1)
        if big:
            spots["hero"] = big.group(1)
        if rc:
            spots["receipt"] = rc.group(1)
        truth = (rc or hl).group(1)  # the receipt is built from the data file; the headline is the fallback
        pp_fix = None
        if pp and y18:
            cur, old = float(truth), float(y18.group(1))
            word = "loosened" if cur < old else "tightened"
            exp = f"{abs(old - cur):.1f}"
            if exp != pp.group(2) or word != pp.group(1):
                pp_fix = (pp.group(0), f"{word} {exp}pp since 2018")
        if len(set(spots.values())) > 1 or pp_fix:
            out.append((f, h, truth, spots, big, pp_fix))
    return out


def main():
    fix = "--fix" in sys.argv
    log = {"generated": datetime.date.today().isoformat(), "state_pages": [], "lender_pages": []}
    bad = 0
    for f, h, api, spots, m in state_pages():
        bad += 1
        rel = os.path.relpath(f, ROOT)
        print(f"{rel}: {spots}")
        if fix and m and m.group(1) != api:
            h2 = h.replace(m.group(0), f'FHA denial rate in 2025 was <span class="mono">{api}%</span>', 1)
            open(f, "w", encoding="utf-8").write(h2)
            log["state_pages"].append({"page": rel, "direct_answer": m.group(1), "now": api})
    for f, h, cur, spots, big, pp_fix in lender_pages():
        bad += 1
        rel = os.path.relpath(f, ROOT)
        print(f"{rel}: {spots} {pp_fix or ''}")
        if fix:
            h2, ch = h, []
            if big and big.group(1) != cur:
                h2 = h2.replace(big.group(0), f'<div class="big">{cur}%</div>', 1); ch.append(("hero", big.group(1), cur))
            if pp_fix:
                h2 = h2.replace(pp_fix[0], pp_fix[1]); ch.append(("since_2018", pp_fix[0], pp_fix[1]))
            if ch:
                open(f, "w", encoding="utf-8").write(h2)
                log["lender_pages"].append({"page": rel, "changes": ch})
    if fix:
        p = os.path.join(ROOT, "eval", f"page-value-fix-{log['generated']}.json")
        json.dump(log, open(p, "w"), indent=1, ensure_ascii=False)
        print(f"fixed: {len(log['state_pages'])} state pages, {len(log['lender_pages'])} lender pages -> {os.path.relpath(p, ROOT)}")
        return 0
    print(f"pages with disagreeing values: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
