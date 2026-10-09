from __future__ import annotations

import sys
import types

from app.intent.model import OnnxIntentModel


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
