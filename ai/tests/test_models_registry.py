from pathlib import Path

from app.models_registry import load_models_yaml


def test_models_yaml_declares_intent_threshold():
    config = load_models_yaml(Path(__file__).resolve().parents[1] / "models.yaml")

    assert config["intent"]["confidence_threshold"] == 0.7
