"""
Fine-tune google/muril-base-cased on the intent dataset.

Requirements (install the [ml] extras):
  pip install ".[ml]"   # from ai/ directory
  OR
  pip install torch transformers datasets scikit-learn optimum[onnxruntime]

Runs on your local GPU (RTX 2050 4GB), Colab T4, or CPU.
Auto-detects VRAM and adjusts batch size + fp16 accordingly.

Usage:
  python ml/intent/train.py                      # full run
  python ml/intent/train.py --epochs 1 --debug   # smoke test (100 rows)
  python ml/intent/train.py --no-fp16            # force fp32 (CPU only)

Output: ml/intent/checkpoints/best/
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"
MODEL_NAME = "google/muril-base-cased"
LABELS = ["confirm", "decline", "reschedule", "call_later", "stop_calling", "unclear"]
LABEL2ID = {label: i for i, label in enumerate(LABELS)}
ID2LABEL = {i: label for i, label in enumerate(LABELS)}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def rows_to_hf_dataset(rows: list[dict]):
    """Convert JSONL rows to a HuggingFace Dataset."""
    from datasets import Dataset  # type: ignore

    data = {"text": [], "label": []}
    for row in rows:
        label_id = LABEL2ID.get(row["label"])
        if label_id is None:
            continue
        data["text"].append(row["text"])
        data["label"].append(label_id)
    return Dataset.from_dict(data)


def compute_metrics(eval_pred):
    from sklearn.metrics import f1_score  # type: ignore
    import numpy as np

    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    macro_f1 = f1_score(labels, preds, average="macro", zero_division=0)
    accuracy = (preds == labels).mean()
    return {"macro_f1": macro_f1, "accuracy": float(accuracy)}


def _get_gpu_config() -> dict:
    """Auto-detect GPU VRAM and return safe training parameters."""
    import torch
    if not torch.cuda.is_available():
        print("No GPU detected — training on CPU (slow but works).")
        return {"batch_size": 16, "grad_accum": 2, "fp16": False}

    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
    name = torch.cuda.get_device_name(0)
    print(f"GPU: {name}  |  VRAM: {vram_gb:.1f} GB")

    if vram_gb < 5:          # RTX 2050 (4GB), GTX 1650, etc.
        return {"batch_size": 8, "grad_accum": 4, "fp16": True}
    elif vram_gb < 10:       # RTX 3060 6GB, etc.
        return {"batch_size": 16, "grad_accum": 2, "fp16": True}
    else:                    # Colab T4 (16GB), RTX 3080+
        return {"batch_size": 32, "grad_accum": 1, "fp16": True}


def main(args: argparse.Namespace) -> None:
    from transformers import (  # type: ignore
        AutoTokenizer,
        AutoModelForSequenceClassification,
        TrainingArguments,
        Trainer,
        DataCollatorWithPadding,
    )
    import torch
    from sklearn.utils.class_weight import compute_class_weight  # type: ignore
    import numpy as np

    # ── Load data ────────────────────────────────────────────────────────────
    train_rows = load_jsonl(DATA_DIR / "train.jsonl")
    val_rows = load_jsonl(DATA_DIR / "val.jsonl")

    if args.debug:
        random.shuffle(train_rows)
        train_rows = train_rows[:100]
        val_rows = val_rows[:50]
        print("DEBUG mode: using 100 train, 50 val rows")

    print(f"Train: {len(train_rows)} | Val: {len(val_rows)}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=64)

    train_ds = rows_to_hf_dataset(train_rows).map(tokenize, batched=True)
    val_ds = rows_to_hf_dataset(val_rows).map(tokenize, batched=True)

    # ── Class weights (handles imbalance) ────────────────────────────────────
    train_labels = [LABEL2ID[r["label"]] for r in train_rows if r["label"] in LABEL2ID]
    class_weights = compute_class_weight(
        "balanced", classes=np.arange(len(LABELS)), y=train_labels
    )
    weight_tensor = torch.tensor(class_weights, dtype=torch.float)

    # ── Model ─────────────────────────────────────────────────────────────────
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=len(LABELS),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    # ── Custom Trainer with weighted loss ─────────────────────────────────────
    class WeightedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            labels = inputs.get("labels")
            outputs = model(**inputs)
            logits = outputs.logits
            loss_fct = torch.nn.CrossEntropyLoss(
                weight=weight_tensor.to(logits.device)
            )
            loss = loss_fct(logits, labels)
            return (loss, outputs) if return_outputs else loss

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    gpu_cfg = _get_gpu_config()
    use_fp16 = gpu_cfg["fp16"] and not args.no_fp16
    effective_batch = gpu_cfg["batch_size"]
    grad_accum = gpu_cfg["grad_accum"]
    # effective total batch = batch_size * grad_accum (simulates batch_size=32)
    print(f"Config: batch={effective_batch}  grad_accum={grad_accum}  fp16={use_fp16}")

    training_args = TrainingArguments(
        output_dir=str(CHECKPOINT_DIR / "run"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=effective_batch,
        per_device_eval_batch_size=effective_batch * 2,
        gradient_accumulation_steps=grad_accum,
        learning_rate=3e-5,
        weight_decay=0.01,
        warmup_ratio=0.1,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        seed=42,
        logging_steps=20,
        fp16=use_fp16,
        dataloader_num_workers=0,   # Windows: keep at 0
        report_to="none",
    )

    trainer = WeightedTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        tokenizer=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer),
        compute_metrics=compute_metrics,
    )

    print(f"Training on {len(train_ds)} samples for {args.epochs} epochs ...")
    trainer.train()

    # ── Save best checkpoint ──────────────────────────────────────────────────
    best_dir = CHECKPOINT_DIR / "best"
    trainer.save_model(str(best_dir))
    tokenizer.save_pretrained(str(best_dir))

    # Save labels.json for the inference layer
    (best_dir / "labels.json").write_text(
        json.dumps(LABELS, ensure_ascii=False, indent=2)
    )

    print(f"\nBest model saved to {best_dir}")
    print("Next step: run evaluate.py, then export_onnx.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=4,
                        help="Number of training epochs (default 4)")
    parser.add_argument("--debug", action="store_true",
                        help="Smoke test: 100 rows, 1 epoch")
    parser.add_argument("--no-fp16", action="store_true",
                        help="Disable fp16 (use on CPU or for debugging)")
    main(parser.parse_args())
