"""
ONNX intent model — MuRIL fine-tuned, int8 quantised.
Loaded once at startup from the models volume.
Returns softmax probabilities over 6 intent labels.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import numpy as np
import structlog

from app.schemas import IntentLabel

log = structlog.get_logger()

LABELS: list[IntentLabel] = [
    "confirm", "decline", "reschedule",
    "call_later", "stop_calling", "unclear",
]


class OnnxIntentModel:
    """
    Wraps an ONNX runtime session for MuRIL-based intent classification.
    Gracefully unavailable when the model file is absent.
    """

    def __init__(self, model_dir: str | Path) -> None:
        self._session = None
        self._tokenizer = None
        self._temperature: float = 1.0
        self._load(Path(model_dir))

    def _load(self, model_dir: Path) -> None:
        onnx_path = model_dir / "intent" / "model.onnx"
        tok_path = model_dir / "intent"

        if not onnx_path.exists():
            log.warning("intent_model_not_found", path=str(onnx_path))
            return

        try:
            import onnxruntime as ort  # type: ignore[import]
            from transformers import AutoTokenizer  # type: ignore[import]

            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 4
            opts.inter_op_num_threads = 1
            self._session = ort.InferenceSession(
                str(onnx_path),
                sess_options=opts,
                providers=["CPUExecutionProvider"],
            )

            # Never download tokenizer files at runtime in the AI service.
            self._tokenizer = AutoTokenizer.from_pretrained(
                str(tok_path), local_files_only=True
            )

            # Load temperature calibration
            import yaml
            # models.yaml is packaged with the AI application, while weights
            # are mounted separately at /models.
            models_yaml = Path(__file__).resolve().parents[2] / "models.yaml"
            if models_yaml.exists():
                cfg = yaml.safe_load(models_yaml.read_text())
                self._temperature = cfg.get("intent_temperature", 1.0)

            log.info("intent_model_loaded", model_dir=str(model_dir))
        except Exception as exc:
            log.error("intent_model_load_failed", error=str(exc))
            self._session = None

    @property
    def available(self) -> bool:
        return self._session is not None

    @property
    def tokenizer_loaded_locally(self) -> bool:
        """True only after the tokenizer has loaded from the mounted folder."""
        return self._tokenizer is not None

    def predict(
        self,
        text: str,
        allowed_intents: list[IntentLabel] | None = None,
    ) -> tuple[IntentLabel, float]:
        """
        Run ONNX inference.
        Returns (intent_label, confidence).
        Raises RuntimeError if model not loaded.
        """
        if not self.available:
            raise RuntimeError("Intent model not loaded")

        enc = self._tokenizer(
            text,
            return_tensors="np",
            truncation=True,
            max_length=64,
            padding="max_length",
        )

        inputs = {
            "input_ids": enc["input_ids"].astype(np.int64),
            "attention_mask": enc["attention_mask"].astype(np.int64),
        }
        if "token_type_ids" in enc:
            inputs["token_type_ids"] = enc["token_type_ids"].astype(np.int64)

        logits = self._session.run(None, inputs)[0][0]  # shape (num_labels,)

        # Temperature scaling
        logits = logits / self._temperature

        # Softmax
        e = np.exp(logits - logits.max())
        probs = e / e.sum()

        # Mask disallowed labels
        if allowed_intents:
            mask = np.array([
                1.0 if LABELS[i] in allowed_intents else 0.0
                for i in range(len(LABELS))
            ])
            probs = probs * mask
            if probs.sum() == 0:
                return "unclear", 0.0
            probs = probs / probs.sum()

        idx = int(np.argmax(probs))
        return LABELS[idx], float(round(probs[idx], 4))
