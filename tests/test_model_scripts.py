"""Local model script smoke tests (no AWS)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


def _load(name: str):
    root = Path("examples/credit-risk").resolve()
    spec = importlib.util.spec_from_file_location(name, root / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_preprocess_train_evaluate_roundtrip(tmp_path: Path, monkeypatch):
    preprocess = _load("preprocess")
    train = _load("train")
    evaluate = _load("evaluate")

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    df = pd.DataFrame(
        {
            "age": [20, 30, 40, 50, 25, 35, 45, 55],
            "income": [30, 40, 50, 60, 35, 45, 55, 65],
            "grade": ["A", "B", "A", "C", "B", "A", "C", "B"],
            "default": [0, 1, 0, 1, 0, 1, 0, 1],
        }
    )
    df.to_csv(raw_dir / "data.csv", index=False)

    processed = tmp_path / "processed"
    monkeypatch.setattr(
        sys,
        "argv",
        ["preprocess.py", "--input-dir", str(raw_dir), "--output-dir", str(processed), "--target-column", "default"],
    )
    preprocess.main()
    assert (processed / "train" / "train.csv").is_file()
    assert (processed / "validation" / "validation.csv").is_file()

    model_dir = tmp_path / "model"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "train.py",
            "--train",
            str(processed / "train"),
            "--model-dir",
            str(model_dir),
            "--model-name",
            "credit-risk",
            "--target-column",
            "default",
        ],
    )
    train.main()
    assert (model_dir / "model.joblib").is_file()

    eval_out = tmp_path / "eval"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluate.py",
            "--model-dir",
            str(model_dir),
            "--input-dir",
            str(processed / "validation"),
            "--output-dir",
            str(eval_out),
            "--target-column",
            "default",
            "--model-name",
            "credit-risk",
        ],
    )
    evaluate.main()
    metrics = json.loads((eval_out / "metrics.json").read_text(encoding="utf-8"))
    assert "auc" in metrics
    assert "accuracy" in metrics
