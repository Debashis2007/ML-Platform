"""Integration-style tests for pipeline factory (no live AWS upsert)."""

from __future__ import annotations

import os

import pytest

from ml_platform.config import PipelineConfig
from ml_platform.steps import build_steps


@pytest.fixture(autouse=True)
def aws_region(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_REGION", "us-east-1")


def test_build_credit_risk_pipeline_definition():
    cfg = PipelineConfig.load("examples/credit-risk/pipeline.yaml")
    pipeline = build_steps(cfg, role_arn="arn:aws:iam::123456789012:role/test-pipeline")
    names = [s.name for s in pipeline.steps]
    assert names == ["Train", "Evaluate", "CheckMetric"]
    param_names = {p.name for p in pipeline.parameters}
    assert param_names == {"ImageUri", "DataUri", "OutputPrefix"}


def test_build_pipeline_with_features_enabled(tmp_path):
    import yaml

    raw = yaml.safe_load(open("examples/credit-risk/pipeline.yaml", encoding="utf-8"))
    raw["steps"]["features"]["enabled"] = True
    path = tmp_path / "pipeline.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    cfg = PipelineConfig.load(path)
    assert cfg.features_enabled is True
    pipeline = build_steps(cfg, role_arn="arn:aws:iam::123456789012:role/test-pipeline")
    names = [s.name for s in pipeline.steps]
    assert names[0] == "Preprocess"
    assert "Train" in names
    assert "Evaluate" in names
    assert "CheckMetric" in names
