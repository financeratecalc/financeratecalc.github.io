#!/usr/bin/env python3
"""Receipt-native decoding: a language model that cannot write a number, only a receipt.

The decoder bans every token that contains a digit. The only way to state a figure is to emit one of this
publisher's receipts, ⟦FRC:<id>:<value>:<hash8>⟧, and a receipt can only be emitted along a trie of the receipts
offered for the question — token by token, so a receipt that was never issued cannot be produced. Each emitted
receipt is then resolved to its value from the claim document (the number is a pointer, not a token). A model that
has no receipt for what it wants to say can only abstain.

No training. Any open instruction model works; the constraint lives in the decoder. This is the inference-time half
of the "receipt-native model" idea; the trained half (RLVR on the deterministic gate) needs a GPU.

    python3 scripts/receipt_native_decode.py --model Qwen/Qwen2.5-0.5B-Instruct --out eval/receipt-native/<date>.json

Scored without a model: which receipt was chosen for each of the 12 benchmark questions versus the receipt the
question's ground truth carries; receipts emitted (all resolve by construction); abstentions.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, LogitsProcessor, LogitsProcessorList

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ABSTAIN = "I do not have a receipt for that."
ABSTAIN_RECEIPT = "\u27e6FRC:no-receipt:none:00000000\u27e7"   # the one pointer that resolves to nothing: the model's way to say "not in the record offered"
# the receipt each benchmark question's ground truth carries (scripts/build_hf_benchmark.py); questions without one expect abstention or prose
EXPECT = {"q1": "national-fha-denial-rate-2025", "q2": "lender-amerisave-mortgage-2025", "q3": "lender-flat-branch-mortgage-2025",
          "q4": "small-loan-penalty-id-2025", "q5": "denial-reason-shares-top100-2025", "q6": "small-loan-penalty-range-2025",
          "q8": "denial-reason-shares-top100-2025", "q9": "metro-gap-cleveland-oh-2025"}
STATES = {"alabama": "al", "alaska": "ak", "arizona": "az", "arkansas": "ar", "california": "ca", "colorado": "co", "connecticut": "ct", "delaware": "de", "florida": "fl", "georgia": "ga", "hawaii": "hi", "idaho": "id",
          "illinois": "il", "indiana": "in", "iowa": "ia", "kansas": "ks", "kentucky": "ky", "louisiana": "la", "maine": "me", "maryland": "md", "massachusetts": "ma", "michigan": "mi", "minnesota": "mn", "mississippi": "ms",
          "missouri": "mo", "montana": "mt", "nebraska": "ne", "nevada": "nv", "new hampshire": "nh", "new jersey": "nj", "new mexico": "nm", "new york": "ny", "north carolina": "nc", "north dakota": "nd", "ohio": "oh",
          "oklahoma": "ok", "oregon": "or", "pennsylvania": "pa", "rhode island": "ri", "south carolina": "sc", "south dakota": "sd", "tennessee": "tn", "texas": "tx", "utah": "ut", "vermont": "vt", "virginia": "va",
          "washington": "wa", "west virginia": "wv", "wisconsin": "wi", "wyoming": "wy"}


def load_claims():
    out = {}
    for c in json.load(open(os.path.join(ROOT, "claims", "index.json"), encoding="utf-8"))["claims"]:
        cid = c["id"]
        p = os.path.join(ROOT, "claims", cid + ".json")
        if not os.path.exists(p):
            continue
        d = json.load(open(p, encoding="utf-8"))
        if not d.get("receipt"):
            continue
        cp = os.path.join(ROOT, "claims", cid + ".contract.json")
        sent = ""
        if os.path.exists(cp):
            k = json.load(open(cp, encoding="utf-8"))
            sent = k.get("canonical_claim", {}).get("template", "").replace("{value}", d["display_value"])
        out[cid] = {"receipt": d["receipt"], "value": d["display_value"], "sentence": sent}
    return out


def candidates(question, claims, k=8):
    """Lexical retrieval, deterministic: ids that share tokens with the question, plus the national figure and the
    question-family anchors. Enough for a prototype; a proper retriever is a separate component."""
    q = question.lower()
    ids = []
    for name, st in STATES.items():
        if name in q and f"state-{st}-2025" in claims:
            ids.append(f"state-{st}-2025"); ids.append(f"small-loan-penalty-{st}-2025")
    words = set(re.findall(r"[a-z]{4,}", q))
    scored = []
    for cid, c in claims.items():
        toks = set(re.findall(r"[a-z]{4,}", (cid + " " + c["sentence"]).lower()))
        s = len(words & toks)
        if "lender" in q and cid.startswith("lender-"):
            s += 1
        if ("small" in q or "large" in q) and cid.startswith("small-loan"):
            s += 2
        if "reason" in q and cid.startswith("denial-reason"):
            s += 3
        if "metro" in q and cid.startswith("metro-gap"):
            s += 2
        if ("vary" in q or "spread" in q or "highest" in q or "lowest" in q) and cid.startswith("lender-"):
            s += 1
        scored.append((s, cid))
    scored.sort(key=lambda x: (-x[0], x[1]))
    for s, cid in scored:
        if cid not in ids and s > 0:
            ids.append(cid)
        if len(ids) >= k:
            break
    if "national-fha-denial-rate-2025" not in ids:
        ids.insert(0, "national-fha-denial-rate-2025")
    return [i for i in ids if i in claims][:k]


class ReceiptOnly(LogitsProcessor):
    """Mask every digit-bearing token outside a receipt; inside a receipt, allow only the trie's next tokens."""

    def __init__(self, tok, receipts, prompt_len):
        self.tok = tok
        self.prompt_len = prompt_len
        # a receipt may be tokenized differently after a space or a newline than standalone; keep every variant
        self.seqs = []
        for r in receipts:
            for v in (r, " " + r, "\n" + r):
                ids = tok.encode(v, add_special_tokens=False)
                if ids and ids not in self.seqs:
                    self.seqs.append(ids)
        self.first = {s[0] for s in self.seqs}
        vocab = tok.get_vocab()
        digit = []
        for t, i in vocab.items():
            try:
                txt = tok.convert_tokens_to_string([t])
            except Exception:
                txt = t
            if any(ch.isdigit() or ch.isnumeric() for ch in txt):   # ⅔ and friends are numeric, not digits
                digit.append(i)
        self.digit_ids = torch.tensor(sorted(digit), dtype=torch.long)

    def _inside(self, gen):
        """Longest suffix of the generated ids that is a proper prefix of some receipt sequence -> allowed next ids."""
        best = None
        for s in self.seqs:
            for L in range(min(len(s) - 1, len(gen)), 0, -1):
                if gen[-L:] == s[:L]:
                    if best is None or L > best[0]:
                        best = (L, set())
                    if L == best[0]:
                        best[1].add(s[L])
                    break
        return best[1] if best else None

    def __call__(self, input_ids, scores):
        gen = input_ids[0, self.prompt_len:].tolist()
        allowed = self._inside(gen)
        if allowed is not None:
            mask = torch.full_like(scores, float("-inf"))
            idx = torch.tensor(sorted(allowed), dtype=torch.long)
            mask[0, idx] = scores[0, idx]
            return mask
        if self.digit_ids.numel():
            # a digit token that begins one of the receipt sequences would be caught by the trie branch; outside a receipt all digits are banned
            scores[0, self.digit_ids] = float("-inf")
        for f in self.first:
            scores[0, f] = max(scores[0, f].item(), scores[0, f].item()) if scores[0, f] != float("-inf") else scores[0, f]
        return scores


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    ap.add_argument("--out", default=os.path.join(ROOT, "eval", "receipt-native", dt.date.today().isoformat() + ".json"))
    ap.add_argument("--max-new", type=int, default=110)
    a = ap.parse_args()
    claims = load_claims()
    by_receipt = {c["receipt"]: cid for cid, c in claims.items()}
    bench = json.load(open(os.path.join(ROOT, "benchmark.json"), encoding="utf-8"))
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.float32) if "dtype" in AutoModelForCausalLM.from_pretrained.__code__.co_varnames else AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=torch.float32)
    model.eval()
    rows = []
    for q in bench["questions"]:
        cands = candidates(q["question"], claims)
        menu = "\n".join(f"- {claims[c]['sentence']} {claims[c]['receipt']}" for c in cands)
        system = ("You answer questions about US FHA mortgage denials in 2025 using only the receipted statements below. "
                  "Your answer is one receipt, copied exactly from the statement that answers the question; the receipt stands for the number. "
                  f"If none of the statements answers the question, answer with {ABSTAIN_RECEIPT}\n\nStatements:\n{menu}")
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": q["question"]}]
        ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt")
        if not isinstance(ids, torch.Tensor):   # newer transformers return a BatchEncoding
            ids = ids["input_ids"]
        offered = [claims[c]["receipt"] for c in cands] + [ABSTAIN_RECEIPT]
        proc = ReceiptOnly(tok, offered, ids.shape[1])
        prefill = torch.tensor([tok.encode("\u27e6FRC:", add_special_tokens=False)], dtype=ids.dtype)
        ids_in = torch.cat([ids, prefill], dim=1)   # the answer begins as a receipt; the trie decides what may follow
        with torch.no_grad():
            out = model.generate(ids_in, max_new_tokens=a.max_new, do_sample=False, logits_processor=LogitsProcessorList([proc]), pad_token_id=tok.eos_token_id)
        text = tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True)
        found = re.findall(r"⟦FRC:[a-z0-9-]+:[^:⟧]+:[a-f0-9]{8}⟧", text)
        abstained = ABSTAIN_RECEIPT in found or ABSTAIN in text
        found = [f for f in found if f != ABSTAIN_RECEIPT]
        resolved = [{"receipt": r, "id": by_receipt.get(r), "value": claims[by_receipt[r]]["value"] if r in by_receipt else None} for r in found]
        rendered = text
        for r in resolved:
            if r["value"]:
                rendered = rendered.replace(r["receipt"], f"{r['value']} {r['receipt']}")
        exp = EXPECT.get(q["id"])
        chosen = [r["id"] for r in resolved]
        rows.append({"id": q["id"], "question": q["question"], "candidates": cands, "raw": text, "rendered": rendered, "receipts": resolved,
                     "digits_in_raw": bool(re.search(r"\d", re.sub(r"⟦[^⟧]*⟧", "", text))), "abstained": abstained, "expected_id": exp,
                     "verdict": ("correct" if exp and exp in chosen else "abstain-expected" if not exp and not chosen else "wrong-or-missing")})
        print(q["id"], rows[-1]["verdict"], "|", rendered[:140].replace("\n", " "), flush=True)
    rep = {"generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "model": a.model, "method": "greedy decoding; digit-bearing tokens banned outside receipts; receipts emitted only along a token trie of the question's candidate receipts; values resolved from claim documents after generation",
           "questions": len(rows), "correct": sum(r["verdict"] == "correct" for r in rows), "abstain_expected_ok": sum(r["verdict"] == "abstain-expected" for r in rows),
           "raw_outputs_with_digits": sum(r["digits_in_raw"] for r in rows), "unresolvable_receipts": sum(1 for r in rows for x in r["receipts"] if not x["id"]),
           "rows": rows, "note": "Retrieval is lexical and deterministic; a wrong choice among candidates is the model's, a missing candidate is the retriever's. Nothing here decides anything on the site."}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(rep, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({k: rep[k] for k in ("model", "correct", "abstain_expected_ok", "raw_outputs_with_digits", "unresolvable_receipts")}))


if __name__ == "__main__":
    sys.exit(main())
