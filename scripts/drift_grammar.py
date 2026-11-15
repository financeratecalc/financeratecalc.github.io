#!/usr/bin/env python3
"""Compositional sentence grammar for the contract-drift training set.

The first generator wrote a handful of fixed templates per reason code, and the classifier learned those templates:
0.998 on sentences from the generator, 58% right-code on hand-written ones. This module widens the surface: each
sentence is assembled from independent slots (how the figure is stated x how the violation is worded x what it is
about), so one code is seen in hundreds of shapes instead of four. Still no model in the loop; every label is true
by construction. Phrasings that also occur in the held-out set (eval/drift-ood-set-c.jsonl) were taken out after
a first draft leaked them; build_drift_training_set.py now fails if a held-out sentence shares a long word run
with a grammar row. Clean rows include the awkward ones: sentences that use the trigger vocabulary (cause, forecast,
law, recommend, same borrower) to *decline* the move, which a keyword learner would flag.

Imported by build_drift_training_set.py; `python3 scripts/drift_grammar.py` prints a sample per code.
"""
import random

CAUSES = ["stricter underwriting", "tighter credit standards", "falling home values",
          "lender overlays", "weak credit scores among applicants", "thin home equity", "the cost of housing",
          "inflation", "stagnant wages", "a shortage of affordable homes", "lenders' appetite for profit",
          "new federal rules", "student loan balances", "the end of low-rate refinancing", "poor documentation by borrowers", "lender bias"]
BROAD = ["credit has dried up across the country",
         "most families are locked out of buying a home",
         "American households cannot borrow", "every would-be buyer is being shut out", "the mortgage market as a whole has seized up",
         "banks have stopped lending", "the US housing economy is in collapse", "no one with average credit can buy a house",
         "the whole country faces a credit crunch", "all borrowers are worse off", "renters will never become owners", "the financial system is failing everyone"]
LAWS = ["the Fair Housing Act", "the Equal Credit Opportunity Act", "fair-lending law", "federal anti-discrimination law", "ECOA", "the law", "civil rights law", "Regulation B"]
LEGAL_NOUNS = ["redlining", "illegal discrimination", "unlawful discrimination", "a fair-lending violation", "lending discrimination", "systemic bias that breaks the law", "an unlawful practice"]
PERSON = ["you", "a buyer like you", "someone in your position", "an applicant like you", "your household"]
YOURS = ["your application", "your file", "your loan", "your request", "your mortgage"]
CHANCE = ["chance", "risk", "probability", "likelihood", "odds"]
SAME = ["the same borrower", "the very same file", "one and the same applicant", "any particular applicant",
        "an otherwise identical borrower", "a borrower with the same credit profile", "the same exact loan file", ]
OTHER_PROG = {"FHA": ["mortgage", "home loan", "conventional loan", "VA", "USDA", "residential loan", "housing loan"],
              "VA": ["mortgage", "home loan", "FHA", "conventional loan", "government-backed loan"],
              "USDA": ["mortgage", "home loan", "FHA", "rural housing and conventional"],
              "conventional": ["mortgage", "home loan", "FHA", "government-backed loan"]}
DISCLAIM = ["why individual applications failed is outside what this file records", "past tallies like this one are not predictions about a future applicant",
            "a group share of this kind tells one household nothing about its own outcome", "no cause can be read off the percentage",
            "the site does not rank or endorse lenders from it", "whether any statute was violated is a separate question the number cannot answer",
            "it cannot show how one borrower would fare at two different doors", "other loan programs are outside this figure",
            "lenders see different mixes of applicants, which the rate does not adjust for", "treat it as history, not as guidance on where to apply",
            "legality is not something a denial share can settle", "the wider mortgage market is not what this figure measures",
            "the explanation for the level is unknown from these data", "each applicant's result depends on facts the aggregate does not contain"]


def cap(s):
    return s[0].upper() + s[1:]


def fact(r, f):
    """A fully qualified statement of the figure (year + decisioned + program + scope)."""
    P, w, v = f["P"], f["w"], f["v"]
    return r.choice([
        f"in 2025, {v} of decisioned {P} applications{w} were denied",
        f"{v} of the {P} applications{w} that reached a decision in 2025 were denied",
        f"among {P} applications{w} decided in 2025, {v} were denied",
        f"lenders denied {v} of the {P} applications{w} they decided in 2025",
        f"of decisioned {P} applications{w} in 2025, {v} ended in denial",
        f"the 2025 record shows {v} of decisioned {P} applications{w} were denied",
    ])


def np(r, f):
    P, w, v = f["P"], f["w"], f["v"]
    return r.choice([f"the {v} {P} denial rate{w} in 2025", f"a 2025 {P} denial rate of {v}{w}", f"the {v} denial rate on decisioned {P} applications{w} in 2025",
                     f"the 2025 {P} denial rate{w} ({v} of decisioned applications)", f"2025's {v} {P} denial rate{w}"])


def bare(r, f):
    """The figure with the year and/or the decisioned base dropped."""
    P, w, v = f["P"], f["w"], f["v"]
    return r.choice([f"{v} of {P} applications{w} are denied", f"{v} of {P} borrowers{w} get rejected", f"roughly {v} of people who apply for {P} financing{w} are denied", f"{v} of {P} applications{w} were denied",
                     f"the denial rate for {P} loans{w} stands at {v}", f"expect {P} denials{w} to run at {v}", f"in 2025, {v} of {P} applications{w} were denied",
                     f"{v} of decisioned {P} applications{w} are denied"])


def causal(r, f):
    c = r.choice(CAUSES)
    return r.choice([
        lambda: f"{cap(fact(r, f))} because of {c}.", lambda: f"{cap(fact(r, f))}, a result of {c}.", lambda: f"{cap(fact(r, f))}; {c} is the reason.", lambda: f"{cap(fact(r, f))}, owing to {c}.",
        lambda: f"{cap(c)} is behind {np(r, f)}.", lambda: f"{cap(c)} led to {np(r, f)}.",
        lambda: f"{cap(c)} produced {np(r, f)}.", lambda: f"{cap(np(r, f))} stems from {c}.", lambda: f"{cap(np(r, f))} can be traced to {c}.", lambda: f"{cap(np(r, f))} reflects {c}.", lambda: f"Blame {c} for {np(r, f)}.",
        lambda: f"{cap(np(r, f))} is what {c} does.", lambda: f"What accounts for {np(r, f)} is {c}.", lambda: f"Why were {f['v']} of decisioned {f['P']} applications{f['w']} denied in 2025? {cap(c)}.",
    ])()


def individual(r, f):
    v, P, w = f["v"], f["P"], f["w"]
    ch, pe, yo = r.choice(CHANCE), r.choice(PERSON), r.choice(YOURS)
    return r.choice([
        lambda: f"Given {np(r, f)}, {pe} can expect a {v} {ch} of denial.", lambda: f"{cap(fact(r, f))}, so {yo} has a {v} {ch} of being turned down.",
        lambda: f"{cap(yo)} will be denied with a {ch} of {v}, the 2025 {P} rate{w}.", lambda: f"{cap(fact(r, f))}, which means {pe} will most likely be approved.",
        lambda: f"{cap(fact(r, f))}; that is the {ch} that {yo} is refused.", lambda: f"{cap(pe)} should count on a {v} {ch} of rejection for a {P} loan{w}, as in 2025.", lambda: f"If {pe} applied for a {P} loan{w} today, the 2025 data say the {ch} of a no is {v}.", lambda: f"{cap(fact(r, f))}, so the forecast for {yo} is a {v} {ch} of refusal.",
        lambda: f"Based on {np(r, f)}, I would predict {yo} gets approved.", lambda: f"Here is what 2025 means for {pe}: a {v} {ch} that the lender says no to a {P} loan{w}.",
    ])()


def legal(r, f):
    law, n = r.choice(LAWS), r.choice(LEGAL_NOUNS)
    return r.choice([
        lambda: f"{cap(np(r, f))} violates {law}.", lambda: f"{cap(np(r, f))} runs afoul of {law}.", lambda: f"{cap(np(r, f))} is proof of {n}.",
        lambda: f"{cap(np(r, f))} is evidence of {n}.", lambda: f"{cap(fact(r, f))}, which is {n}.",
        lambda: f"{cap(fact(r, f))}; lenders broke {law}.", lambda: f"{cap(fact(r, f))}, in violation of {law}.",
        lambda: f"{cap(np(r, f))} gives denied applicants grounds to sue under {law}.",
        lambda: f"{cap(fact(r, f))}; this is illegal.", lambda: f"Under {law}, {np(r, f)} is unlawful.", lambda: f"{cap(np(r, f))} shows lenders are not complying with {law}.",
    ])()


def recommend(r, f):
    v, P, w = f["v"], f["P"], f["w"]
    L = f.get("lender")
    who = L or r.choice(["lenders whose 2025 denial rate was below 10%", "the lender at the top of the 2025 list", "lenders above the 2025 average"])
    good = r.choice(["Choose", "Pick", "Go with", "Apply to", "Use", "Your best option is", "We suggest", "I recommend"])
    bad = r.choice(["Avoid", "Skip", "Stay away from", "Do not bother with", "Cross off", "Do not waste an application on"])
    return r.choice([
        lambda: f"{good} {who} for a {P} loan{'' if L else w}: {fact(r, f)}.", lambda: f"{bad} {who}: {fact(r, f)}.",
        lambda: f"{cap(fact(r, f))}; borrowers should take their business to {who}.",
        lambda: f"Given {np(r, f)}, {who} {r.choice(['is', 'are'] if not L else ['is'])} the best place to apply.",
        lambda: f"{cap(fact(r, f))}, which makes {who} the worst option for {P} borrowers.", lambda: f"On 2025 {P} denial rates{w}, {who} {r.choice(['comes', 'come'] if not L else ['comes'])} out as the one to trust.",
        lambda: f"Rank lenders by 2025 {P} denial rate{w} and apply to {who} first.", lambda: f"{cap(fact(r, f))}. If approval matters, you ought to go to {who}.",
        lambda: f"{cap(np(r, f))} tells you which lenders are worth your time: {who}.", lambda: f"For {P} borrowers{w}, {who} {r.choice(['is', 'are'] if not L else ['is'])} the top pick on the 2025 numbers.",
    ])()


def mismatch(r, f):
    v, w, P = f["v"], f["w"], f["P"]
    base = P.split()[0]
    o = r.choice(OTHER_PROG.get(base, ["mortgage", "home loan"]))
    rest = P[len(base):]
    g = dict(f, P=(o + rest).strip())
    return r.choice([
        lambda: cap(fact(r, g)) + ".", lambda: cap(fact(r, g)) + ".", lambda: f"In 2025, {v} of all decisioned applications for home financing{w} were denied.",
    ])()


def qualifier(r, f):
    return cap(bare(r, f)) + "."


def same(r, f):
    v, P, w = f["v"], f["P"], f["w"]
    s = r.choice(SAME)
    return r.choice([
        lambda: f"In 2025, {s} faced a {v} denial rate for {P} loans{w}.", lambda: f"{cap(s)} was denied {v} of the time{w} under {P} in 2025.",
        lambda: f"All else equal, {s} met a {v} denial rate{w} on a 2025 {P} application.",
        lambda: f"{cap(fact(r, f))}: {s} would get a different answer at a different lender.", lambda: f"{cap(fact(r, f))}, meaning {s} is treated differently depending on where the file lands.", lambda: f"{cap(s)} is turned down at a rate of {v}{w} according to 2025 {P} decisions.", lambda: f"For {s}, the door matters: {fact(r, f)}.",
        lambda: f"{cap(fact(r, f))}, even for {s} applying twice.",
    ])()


def scope(r, f):
    b = r.choice(BROAD)
    return r.choice([
        lambda: f"{cap(fact(r, f))}, so {b}.", lambda: f"{cap(fact(r, f))}, which tells you {b}.",
        lambda: f"{cap(fact(r, f))}. In other words, {b}.", lambda: f"{cap(fact(r, f))}, a sign that {b}.", lambda: f"{cap(fact(r, f))}, meaning {b}.",
        lambda: f"{cap(np(r, f))} confirms that {b}.", lambda: f"{cap(np(r, f))} is all you need to know: {b}.",
    ])()


def clean(r, f):
    d = r.choice(DISCLAIM)
    return r.choice([
        lambda: cap(fact(r, f)) + ".", lambda: f"{cap(fact(r, f))}; {d}.", lambda: f"{cap(fact(r, f))}. {cap(d)}.", lambda: f"{cap(fact(r, f))} (historical aggregate; {d}).",
        lambda: f"{cap(fact(r, f))} (source: federal HMDA loan-level data).", lambda: f"{cap(fact(r, f))}, though {d}.", lambda: f"According to the HMDA record, {fact(r, f)}; {d}.",
        lambda: f"{cap(fact(r, f))}. {cap(r.choice(DISCLAIM))}, and {d}.",
    ])()


MAKERS = {"CAUSALITY_NOT_ESTABLISHED": causal, "INDIVIDUAL_PREDICTION_PROHIBITED": individual, "LEGAL_CONCLUSION_NOT_SUPPORTED": legal, "LENDER_RECOMMENDATION": recommend,
          "PROGRAM_MISMATCH": mismatch, "QUALIFIER_DELETED": qualifier, "SAME_APPLICANT_FRAMING": same, "SCOPE_TOO_BROAD": scope}


def grammar_rows(facts, per_code=450, n_clean=900, seed=20261115):
    """facts: [{P, w, v, id, lender?}] taken from receipted claims. Returns unique rows; label true by construction."""
    r = random.Random(seed)
    seen, rows = set(), []

    def add(text, codes, f, src):
        text = " ".join(text.split())
        if text in seen:
            return False
        seen.add(text)
        rows.append({"text": text, "codes": sorted(set(codes)), "claim_id": f["id"], "kind": "grammar", "source": "grammar:" + src})
        return True

    for code, mk in MAKERS.items():
        n = tries = 0
        while n < per_code and tries < per_code * 20:
            tries += 1
            f = r.choice(facts)
            t = mk(r, f)
            codes = [code]
            if code != "QUALIFIER_DELETED" and "2025" not in t:
                codes.append("QUALIFIER_DELETED")
            n += add(t, codes, f, code)
    n = tries = 0
    while n < n_clean and tries < n_clean * 20:
        tries += 1
        f = r.choice(facts)
        n += add(clean(r, f), [], f, "clean")
    return rows


if __name__ == "__main__":
    demo = [{"P": "FHA", "w": "", "v": "22.1%", "id": "demo"}, {"P": "VA purchase", "w": "", "v": "8.2%", "id": "demo"}, {"P": "FHA", "w": " in Texas", "v": "21.4%", "id": "demo"}]
    rr = random.Random(1)
    for code, mk in list(MAKERS.items()) + [("CLEAN", clean)]:
        print(code)
        for _ in range(4):
            print("   ", mk(rr, rr.choice(demo)))
