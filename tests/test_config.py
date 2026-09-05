"""Tests for PipelineConfig validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ml_platform.config import PipelineConfig


def _write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "pipeline.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_load_credit_risk_example():
    cfg = PipelineConfig.load("examples/credit-risk/pipeline.yaml")
    assert cfg.model_name == "credit-risk"
    assert cfg.model_package_group == "ModelCreditRisk"
    assert cfg.threshold_metric == "auc"
    assert cfg.threshold_min == 0.75
    assert cfg.features_enabled is False
    assert cfg.register_enabled is True
    assert cfg.train_uri.startswith("s3://")


def test_rejects_missing_model(tmp_path: Path):
    path = _write_config(tmp_path, {"steps": {}})
    with pytest.raises(ValueError, match="model"):
        PipelineConfig.load(path)


def test_rejects_bad_threshold(tmp_path: Path):
    path = _write_config(
        tmp_path,
        {
            "model": "demo",
            "steps": {"conditional_register": {"metric": "auc", "threshold": 1.5}},
        },
    )
    with pytest.raises(ValueError, match="threshold"):
        PipelineConfig.load(path)


def test_rejects_invalid_s3_uri(tmp_path: Path):
    path = _write_config(
        tmp_path,
        {"model": "demo", "data": {"train_uri": "http://not-s3/data"}},
    )
    with pytest.raises(ValueError, match="s3://"):
        PipelineConfig.load(path)


def test_register_requires_evaluate(tmp_path: Path):
    path = _write_config(
        tmp_path,
        {
            "model": "demo",
            "steps": {
                "evaluate": {"enabled": False},
                "conditional_register": {"enabled": True, "threshold": 0.7},
            },
        },
    )
    with pytest.raises(ValueError, match="evaluate"):
        PipelineConfig.load(path)


def test_package_group_default(tmp_path: Path):
    path = _write_config(tmp_path, {"model": "fraud-detection"})
    cfg = PipelineConfig.load(path)
    assert cfg.model_package_group == "ModelFraudDetection"
