from __future__ import annotations

import sys
import types
import json
from collections import Counter
from pathlib import Path

import pytest

from app.intent.model import OnnxIntentModel

LABELS = ["confirm", "decline", "reschedule", "call_later", "stop_calling", "unclear"]
AI_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = AI_DIR / "models"
DATA_DIR = AI_DIR / "ml" / "intent" / "data"


def test_missing_intent_model_is_unavailable_without_crashing(tmp_path):
    model = OnnxIntentModel(tmp_path)

    assert model.available is False


def test_intent_tokenizer_is_loaded_from_local_files_only(tmp_path, monkeypatch):
    intent_dir = tmp_path / "intent"
    intent_dir.mkdir()
    (intent_dir / "model.onnx").write_bytes(b"placeholder")

    class FakeSessionOptions:
        intra_op_num_threads = 0
        inter_op_num_threads = 0

    class FakeSession:
        def __init__(self, *args, **kwargs):
            pass

    ort_module = types.ModuleType("onnxruntime")
    ort_module.SessionOptions = FakeSessionOptions
    ort_module.InferenceSession = FakeSession

    calls: list[dict] = []

    class FakeTokenizer:
        @staticmethod
        def from_pretrained(path, **kwargs):
            calls.append({"path": path, **kwargs})
            return object()

    transformers_module = types.ModuleType("transformers")
    transformers_module.AutoTokenizer = FakeTokenizer

    monkeypatch.setitem(sys.modules, "onnxruntime", ort_module)
    monkeypatch.setitem(sys.modules, "transformers", transformers_module)

    model = OnnxIntentModel(tmp_path)

    assert model.available is True
    assert calls == [{"path": str(intent_dir), "local_files_only": True}]


@pytest.fixture(scope="module")
def trained_intent_model():
    pytest.importorskip("onnxruntime")
    pytest.importorskip("transformers")
    model = OnnxIntentModel(MODEL_DIR)
    if not model.available:
        pytest.fail(f"Trained intent model did not load from {MODEL_DIR / 'intent'}")
    return model


def test_trained_onnx_model_returns_valid_label_and_confidence(trained_intent_model):
    label, confidence = trained_intent_model.predict("haan main aaunga", [*LABELS])

    assert label in LABELS
    assert 0.0 <= confidence <= 1.0


def test_trained_onnx_model_allowed_intents_masking(trained_intent_model):
    label, confidence = trained_intent_model.predict(
        "haan main aaunga", ["decline"]
    )

    assert label == "decline"
    assert 0.0 <= confidence <= 1.0


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_test_set_predictions_match_training_report(trained_intent_model):
    pytest.skip(
        "repository test.jsonl is not identified as the split used by "
        "training_report.json; compare only after the Colab split is supplied"
    )
    sklearn = pytest.importorskip("sklearn")
    rows = _rows(DATA_DIR / "test.jsonl")
    predictions = [
        trained_intent_model.predict(row["text"], LABELS)[0]
        for row in rows
    ]
    truth = [row["label"] for row in rows]
    accuracy = sklearn.metrics.accuracy_score(truth, predictions)
    macro_f1 = sklearn.metrics.f1_score(
        truth, predictions, labels=LABELS, average="macro", zero_division=0
    )

    report = json.loads(
        (MODEL_DIR / "intent" / "training_report.json").read_text(encoding="utf-8")
    )["report"]["synthetic_test"]["overall"]
    assert accuracy == pytest.approx(report["acc"], abs=0.01)
    assert macro_f1 == pytest.approx(report["macro_f1"], abs=0.01)


def test_handwritten_test_set_has_no_train_overlap():
    handwritten_path = DATA_DIR / "handwritten_test.jsonl"
    if not handwritten_path.exists():
        pytest.skip("handwritten_test.jsonl is not present")

    train_texts = {
        " ".join(row["text"].casefold().split())
        for row in _rows(DATA_DIR / "train.jsonl")
    }
    handwritten_texts = {
        " ".join(row["text"].casefold().split())
        for row in _rows(handwritten_path)
    }
    assert not train_texts.intersection(handwritten_texts)


@pytest.mark.asyncio
async def test_pipeline_order_rules_then_model_then_llm_then_unclear(monkeypatch):
    import app.intent.pipeline as pipeline

    class FakeModel:
        available = True

        def __init__(self):
            self.calls = 0

        def predict(self, text, allowed):
            self.calls += 1
            return "decline", 0.9

    fake_model = FakeModel()
    monkeypatch.setattr(pipeline, "_onnx_model", fake_model)
    monkeypatch.setattr(pipeline, "rules_classify", lambda *args: ("confirm", 0.95))
    label, _, source, _ = await pipeline.run_pipeline("yes", "en")
    assert (label, source) == ("confirm", "rules")
    assert fake_model.calls == 0

    monkeypatch.setattr(pipeline, "rules_classify", lambda *args: ("unclear", 0.0))
    label, _, source, _ = await pipeline.run_pipeline("maybe", "en")
    assert (label, source) == ("decline", "model")

    fake_model.available = False
    monkeypatch.setattr(pipeline.settings, "llm_fallback", "groq")
    async def fake_llm(*args):
        return "call_later", 0.8
    import app.intent.llm_fallback as llm_fallback
    monkeypatch.setattr(llm_fallback, "classify_with_llm", fake_llm)
    label, _, source, _ = await pipeline.run_pipeline("maybe", "en")
    assert (label, source) == ("call_later", "llm")

    monkeypatch.setattr(pipeline.settings, "llm_fallback", "none")
    label, confidence, source, _ = await pipeline.run_pipeline("maybe", "en")
    assert (label, confidence, source) == ("unclear", 0.0, "rules")


def test_llm_failure_metadata_does_not_include_exception_message():
    from app.intent.llm_fallback import _failure_fields

    fields = _failure_fields(RuntimeError("secret-bearing request URL"))
    assert fields == {"error_type": "RuntimeError"}
