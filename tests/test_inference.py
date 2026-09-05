"""Inference helper unit tests."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier


def _load_inference():
    path = Path("examples/credit-risk/inference.py").resolve()
    spec = importlib.util.spec_from_file_location("inference", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_inference_contract(tmp_path: Path):
    inference = _load_inference()
    X = np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6], [0.7, 0.8]])
    y = np.array([0, 1, 0, 1])
    model = RandomForestClassifier(n_estimators=10, random_state=0)
    model.fit(X, y)
    import joblib

    joblib.dump(model, tmp_path / "model.joblib")
    loaded = inference.model_fn(str(tmp_path))
    features = inference.input_fn(json.dumps({"features": [[0.1, 0.2]]}))
    pred = inference.predict_fn(features, loaded)
    out = json.loads(inference.output_fn(pred))
    assert "prediction" in out
    assert "score" in out
    assert "model_version" in out
