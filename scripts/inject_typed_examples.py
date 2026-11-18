#!/usr/bin/env python3
"""Give the site's main text fields a typed example (assets/typed-placeholder.js): the field shows what to enter by
writing a real example, erasing it and writing the next. Receipt examples are read from the claim documents, so an
example is always a receipt that verifies today.

    python3 scripts/inject_typed_examples.py            # write
    python3 scripts/inject_typed_examples.py --check    # fail if a field's examples are missing or out of date
"""
import html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SCRIPT = '<script src="/assets/typed-placeholder.js" defer></script>'


def receipts():
    ids = ["national-fha-denial-rate-2025", "state-fl-2025", "state-tx-2025", "state-oh-2025"]
    return [json.load(open(f"claims/{i}.json", encoding="utf-8"))["receipt"] for i in ids if os.path.exists(f"claims/{i}.json")]


def fields():
    r = receipts()
    return {   # page -> [(field id, examples)]
        "verify.html": [("r", r)],
        "place-a-number.html": [("pn-figure", ["12.8%", "22.1%", "65,327", "37.4%"])],
        "denominator-map.html": [("pf", ["12.78", "22.08", "37.39", "8.24"])],
        "check-answer.html": [("t", ["About a quarter of FHA applicants are denied, so you will probably be denied too.",
                                     "The FHA denial rate is 22.1%.", "CrossCountry denied only 6.2% of FHA applications, so go with them.",
                                     "Fannie Mae requires a minimum credit score of 620."])],
    }


def apply(s, fid, examples):
    attr = ' data-typed="' + html.escape(json.dumps(examples, ensure_ascii=False), quote=True) + '"'
    m = re.search(r'<(input|textarea)\b[^>]*\bid="' + re.escape(fid) + r'"[^>]*>', s)
    if not m:
        return s, False
    tag = re.sub(r'\sdata-typed="[^"]*"', "", m.group(0))
    tag = tag[:-1].rstrip("/").rstrip() + attr + ">"
    s = s[:m.start()] + tag + s[m.end():]
    if SCRIPT not in s:
        s = s.replace("</body>", SCRIPT + "\n</body>", 1)
    return s, True


def main():
    bad = []
    for page, fs in fields().items():
        s = open(page, encoding="utf-8").read()
        t = s
        for fid, ex in fs:
            t, ok = apply(t, fid, ex)
            if not ok:
                bad.append(f"{page}: field #{fid} not found")
        if t != s:
            if "--check" in sys.argv:
                bad.append(f"{page}: typed examples missing or out of date")
            else:
                open(page, "w", encoding="utf-8").write(t)
    print("typed examples:", "current" if not bad else bad)
    sys.exit(1 if bad and "--check" in sys.argv else 0)


if __name__ == "__main__":
    main()
