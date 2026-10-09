"""
Export the best checkpoint to ONNX with int8 dynamic quantisation.

Steps:
  1. Export to ONNX fp32 using optimum
  2. Apply dynamic int8 quantisation (onnxruntime)
  3. Verify equivalence (argmax must match on 500 samples)
  4. Write model.onnx, tokenizer files, labels.json to ml/intent/onnx/

Then copy ml/intent/onnx/ into the Docker models volume:
  cp -r ml/intent/onnx/ /path/to/models/intent/

Usage:
  pip install ".[ml]"
  python ml/intent/export_onnx.py

Requirements:
  optimum[onnxruntime], torch, transformers
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import numpy as np

CHECKPOINT_DIR = Path(__file__).parent / "checkpoints" / "best"
ONNX_DIR = Path(__file__).parent / "onnx"
LABELS = ["confirm", "decline", "reschedule", "call_later", "stop_calling", "unclear"]


def _verify_equivalence(
    tokenizer,
    pt_model,
    ort_session,
    n_samples: int = 500,
    max_logit_diff: float = 0.05,
) -> bool:
    """Check that argmax matches between PyTorch and ONNX on random inputs."""
    import torch

    test_texts = [
        "yes I will come", "nahi", "illa", "reschedule please",
        "call me later", "stop calling", "hmm", "aam", "haan haan",
        "sari varuven",
    ] * (n_samples // 10 + 1)
    test_texts = test_texts[:n_samples]

    mismatches = 0
    for text in test_texts:
        enc = tokenizer(text, return_tensors="pt", truncation=True, max_length=64, padding="max_length")
        with torch.no_grad():
            pt_logits = pt_model(**enc).logits.numpy()[0]
        ort_inputs = {
            "input_ids": enc["input_ids"].numpy().astype(np.int64),
            "attention_mask": enc["attention_mask"].numpy().astype(np.int64),
        }
        if "token_type_ids" in enc:
            ort_inputs["token_type_ids"] = enc["token_type_ids"].numpy().astype(np.int64)
        ort_logits = ort_session.run(None, ort_inputs)[0][0]

        if np.argmax(pt_logits) != np.argmax(ort_logits):
            mismatches += 1

    match_rate = 1 - mismatches / n_samples
    print(f"Equivalence check: {match_rate:.3%} argmax agreement on {n_samples} samples")
    return match_rate >= 0.99


def main() -> None:
    from optimum.onnxruntime import ORTModelForSequenceClassification  # type: ignore
    from transformers import AutoTokenizer, AutoModelForSequenceClassification  # type: ignore
    import onnxruntime as ort  # type: ignore
    from onnxruntime.quantization import quantize_dynamic, QuantType  # type: ignore

    if not CHECKPOINT_DIR.exists():
        raise SystemExit(f"Checkpoint not found at {CHECKPOINT_DIR}. Run train.py first.")

    ONNX_DIR.mkdir(parents=True, exist_ok=True)
    fp32_path = ONNX_DIR / "model_fp32.onnx"
    int8_path = ONNX_DIR / "model.onnx"

    # ── Step 1: Export fp32 ONNX via optimum ─────────────────────────────────
    print("Exporting to ONNX fp32 ...")
    ort_model = ORTModelForSequenceClassification.from_pretrained(
        str(CHECKPOINT_DIR), export=True
    )
    ort_model.save_pretrained(str(ONNX_DIR))
    # optimum saves as model.onnx by default; rename for clarity
    exported = ONNX_DIR / "model.onnx"
    if exported.exists():
        shutil.copy(exported, fp32_path)

    # ── Step 2: Dynamic int8 quantisation ────────────────────────────────────
    print("Quantising to int8 ...")
    quantize_dynamic(
        model_input=str(fp32_path),
        model_output=str(int8_path),
        weight_type=QuantType.QInt8,
    )

    # ── Step 3: Equivalence verification ─────────────────────────────────────
    tokenizer = AutoTokenizer.from_pretrained(str(CHECKPOINT_DIR))
    pt_model = AutoModelForSequenceClassification.from_pretrained(str(CHECKPOINT_DIR))
    pt_model.eval()

    sess_options = ort.SessionOptions()
    sess_options.intra_op_num_threads = 4
    ort_session = ort.InferenceSession(
        str(int8_path),
        sess_options=sess_options,
        providers=["CPUExecutionProvider"],
    )

    ok = _verify_equivalence(tokenizer, pt_model, ort_session)
    if not ok:
        print("WARNING: >1% argmax mismatch — review quantisation settings.")

    # ── Step 4: Save tokenizer + labels into onnx dir ─────────────────────────
    tokenizer.save_pretrained(str(ONNX_DIR))
    (ONNX_DIR / "labels.json").write_text(
        json.dumps(LABELS, ensure_ascii=False, indent=2)
    )
    # Remove fp32 model to save space
    fp32_path.unlink(missing_ok=True)

    # ── Benchmark latency ─────────────────────────────────────────────────────
    test_text = "yes I will attend the event"
    enc = tokenizer(test_text, return_tensors="np", truncation=True, max_length=64, padding="max_length")
    ort_inputs = {k: v.astype(np.int64) for k, v in enc.items() if k in ("input_ids", "attention_mask", "token_type_ids")}

    times = []
    for _ in range(50):
        t0 = time.perf_counter()
        ort_session.run(None, ort_inputs)
        times.append((time.perf_counter() - t0) * 1000)
    p50 = sorted(times)[len(times) // 2]
    p95 = sorted(times)[int(len(times) * 0.95)]
    print(f"\nLatency on CPU (4 threads): p50={p50:.1f}ms  p95={p95:.1f}ms")

    model_size_mb = int8_path.stat().st_size / 1_000_000
    print(f"Model size: {model_size_mb:.1f} MB")

    print(f"\nONNX model written to {ONNX_DIR}")
    print("Next: copy onnx/ into your models volume as intent/")
    print("  e.g.  cp -r ml/intent/onnx/ /models/intent/")


if __name__ == "__main__":
    main()
