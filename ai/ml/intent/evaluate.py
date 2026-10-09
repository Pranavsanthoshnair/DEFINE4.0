"""
Evaluate the best checkpoint on the test set.

Reports: accuracy, macro F1, per-class precision/recall/F1, confusion matrix.
Runs on both synthetic test set and (if present) hand-written test set.

Usage:
  python ml/intent/evaluate.py
  python ml/intent/evaluate.py --handwritten ml/intent/data/handwritten_test.jsonl
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
CHECKPOINT_DIR = Path(__file__).parent / "checkpoints" / "best"
LABELS = ["confirm", "decline", "reschedule", "call_later", "stop_calling", "unclear"]
LABEL2ID = {label: i for i, label in enumerate(LABELS)}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def evaluate_dataset(rows: list[dict], tokenizer, model, label: str) -> None:
    import torch
    import numpy as np
    from sklearn.metrics import (  # type: ignore
        accuracy_score,
        f1_score,
        classification_report,
        confusion_matrix,
    )

    texts = [r["text"] for r in rows]
    true_labels = [LABEL2ID.get(r["label"], -1) for r in rows]

    all_preds: list[int] = []
    batch_size = 64

    model.eval()
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            enc = tokenizer(
                batch, return_tensors="pt", truncation=True,
                max_length=64, padding=True
            )
            logits = model(**enc).logits
            preds = logits.argmax(dim=-1).tolist()
            all_preds.extend(preds)

    # Filter invalid labels
    valid = [(t, p) for t, p in zip(true_labels, all_preds) if t >= 0]
    true_labels_f = [t for t, _ in valid]
    preds_f = [p for _, p in valid]

    print(f"\n=== {label} (n={len(valid)}) ===")
    print(f"Accuracy:  {accuracy_score(true_labels_f, preds_f):.4f}")
    print(f"Macro F1:  {f1_score(true_labels_f, preds_f, average='macro', zero_division=0):.4f}")
    print()
    print(classification_report(
        true_labels_f, preds_f,
        target_names=LABELS,
        zero_division=0,
    ))
    print("Confusion matrix (rows=true, cols=pred):")
    cm = confusion_matrix(true_labels_f, preds_f, labels=list(range(len(LABELS))))
    header = "         " + "  ".join(f"{l[:6]:>6}" for l in LABELS)
    print(header)
    for i, row in enumerate(cm):
        print(f"{LABELS[i][:8]:>8} " + "  ".join(f"{v:>6}" for v in row))


def main(args: argparse.Namespace) -> None:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification  # type: ignore

    if not CHECKPOINT_DIR.exists():
        raise SystemExit(f"Checkpoint not found at {CHECKPOINT_DIR}. Run train.py first.")

    print(f"Loading model from {CHECKPOINT_DIR} ...")
    tokenizer = AutoTokenizer.from_pretrained(str(CHECKPOINT_DIR))
    model = AutoModelForSequenceClassification.from_pretrained(str(CHECKPOINT_DIR))

    # Synthetic test set
    test_path = DATA_DIR / "test.jsonl"
    if test_path.exists():
        test_rows = load_jsonl(test_path)
        evaluate_dataset(test_rows, tokenizer, model, "Synthetic test set")

    # Hand-written test set
    if args.handwritten and Path(args.handwritten).exists():
        hw_rows = load_jsonl(Path(args.handwritten))
        evaluate_dataset(hw_rows, tokenizer, model, "Hand-written test set")
    else:
        print("\nNo hand-written test set found (use --handwritten path to provide one).")

    print("\nDone. Copy results into docs/MODEL_REPORT.md.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--handwritten", default=None,
                        help="Path to hand-written test JSONL")
    main(parser.parse_args())
