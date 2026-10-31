#!/usr/bin/env python3
"""Train the contract-drift classifier: sentence -> gate reason codes (multi-label), from eval/drift-training-set.jsonl.

Small encoder, CPU-friendly, no generation. The model does not decide anything on the site; the deterministic gate
does. It exists to catch paraphrases the regexes miss and to be published as a reproducible artefact of the record.

    python3 scripts/train_drift_classifier.py --out models/frc-contract-drift [--base distilroberta-base] [--epochs 3] [--push REPO]
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import torch
from torch.utils.data import Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "eval", "drift-training-set.jsonl")


class Rows(Dataset):
    def __init__(self, rows, tok, labels, max_len=96):
        self.enc = tok([r["text"] for r in rows], truncation=True, max_length=max_len, padding="max_length")
        self.y = np.zeros((len(rows), len(labels)), dtype=np.float32)
        for i, r in enumerate(rows):
            for c in r["codes"]:
                if c in labels:
                    self.y[i, labels.index(c)] = 1.0

    def __len__(self):
        return len(self.y)

    def __getitem__(self, i):
        item = {k: torch.tensor(v[i]) for k, v in self.enc.items()}
        item["labels"] = torch.tensor(self.y[i])
        return item


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="distilroberta-base")
    ap.add_argument("--out", default=os.path.join(ROOT, "models", "frc-contract-drift"))
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--push", default=None, help="Hugging Face repo id to push to (needs HF_TOKEN)")
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(DATA, encoding="utf-8")]
    labels = sorted({c for r in rows for c in r["codes"]} - {"PERIOD_MISMATCH"})  # too few examples to learn
    train = [r for r in rows if r["split"] == "train"]
    test = [r for r in rows if r["split"] == "test"]
    print(f"labels={labels} train={len(train)} test={len(test)}", flush=True)
    tok = AutoTokenizer.from_pretrained(a.base)
    model = AutoModelForSequenceClassification.from_pretrained(a.base, num_labels=len(labels), problem_type="multi_label_classification",
                                                               id2label={i: l for i, l in enumerate(labels)}, label2id={l: i for i, l in enumerate(labels)})
    args = TrainingArguments(output_dir=os.path.join(a.out, "_trainer"), num_train_epochs=a.epochs, per_device_train_batch_size=32, per_device_eval_batch_size=64,
                             learning_rate=3e-5, weight_decay=0.01, logging_steps=50, save_strategy="no", report_to=[], seed=20261031, use_cpu=not torch.cuda.is_available(), dataloader_pin_memory=False)
    t0 = time.time()
    trainer = Trainer(model=model, args=args, train_dataset=Rows(train, tok, labels))
    trainer.train()
    # evaluation on held-out claim ids
    model.eval()
    ds = Rows(test, tok, labels)
    probs = []
    with torch.no_grad():
        for i in range(0, len(ds), 64):
            batch = {k: torch.stack([ds[j][k] for j in range(i, min(i + 64, len(ds)))]) for k in ("input_ids", "attention_mask")}
            probs.append(torch.sigmoid(model(**batch).logits).numpy())
    P = np.concatenate(probs); Y = ds.y; pred = (P >= 0.5).astype(np.float32)
    per = {}
    for k, l in enumerate(labels):
        tp = float(((pred[:, k] == 1) & (Y[:, k] == 1)).sum()); fp = float(((pred[:, k] == 1) & (Y[:, k] == 0)).sum()); fn = float(((pred[:, k] == 0) & (Y[:, k] == 1)).sum())
        per[l] = {"support": int(Y[:, k].sum()), "precision": round(tp / (tp + fp), 3) if tp + fp else None, "recall": round(tp / (tp + fn), 3) if tp + fn else None}
    clean = (Y.sum(1) == 0); clean_pred = (pred.sum(1) == 0)
    report = {"base": a.base, "labels": labels, "train_rows": len(train), "test_rows": len(test), "epochs": a.epochs, "train_seconds": round(time.time() - t0),
              "exact_match": round(float((pred == Y).all(1).mean()), 3), "per_label": per,
              "clean_sentences": {"n": int(clean.sum()), "flagged_false": int((clean & ~clean_pred).sum())},
              "note": "Held-out split by claim id: no claim appears on both sides. Rule-generated data; a sentence pattern the generator never wrote is not covered by this number."}
    os.makedirs(a.out, exist_ok=True)
    json.dump(report, open(os.path.join(a.out, "eval.json"), "w"), indent=1)
    print(json.dumps(report, indent=1), flush=True)
    model.save_pretrained(a.out); tok.save_pretrained(a.out)
    card = f"""---
license: cc-by-4.0
language: en
tags: [text-classification, multi-label, citation, provenance, mortgage, hmda, fha]
base_model: {a.base}
---
# frc-contract-drift

Sentence → the reason codes FinanceRateCalc's deterministic gate assigns when a published figure is restated in a way the record cannot support. Labels: {", ".join(labels)}.

Trained on {len(train)} rule-generated sentences from 386 claim contracts (canonical sentence and faithful paraphrases → no code; rule-written distortions → the code), plus the citation-decision fixture candidates with the codes the gate gave them. No model wrote any training sentence. Held out by claim id: exact-match {report['exact_match']}, per-label precision/recall in `eval.json`.

This model does not decide anything on financeratecalc.com — the gate does. It is a second reader for paraphrases the regexes miss, and a reproducible artefact of the record. It knows nothing about figures it was not shown; check the number with the receipt, not with this model.

Data: https://financeratecalc.com/eval/drift-training-set.jsonl · Spec: https://financeratecalc.com/rl-env/CITATION-DECISION-SPEC.md · Source: https://github.com/financeratecalc/financeratecalc.github.io
"""
    open(os.path.join(a.out, "README.md"), "w", encoding="utf-8").write(card)
    if a.push:
        from huggingface_hub import HfApi
        api = HfApi(token=os.environ["HF_TOKEN"])
        api.create_repo(a.push, repo_type="model", exist_ok=True)
        api.upload_folder(folder_path=a.out, repo_id=a.push, repo_type="model", ignore_patterns=["_trainer/*"], commit_message="train from rule-generated set")
        print("pushed", a.push)


if __name__ == "__main__":
    main()
