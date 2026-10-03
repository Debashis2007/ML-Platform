"""Integration-style tests for pipeline factory (no live AWS upsert)."""

from __future__ import annotations

import pytest
import yaml

from ml_platform.config import ModelConfig
from ml_platform.run_pipeline import pipeline_parameters
from ml_platform.steps import PIPELINE_PARAMETERS, build_steps

EXAMPLE = "examples/credit-risk/model.yaml"


@pytest.fixture(autouse=True)
def aws_region(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_REGION", "us-east-1")


def _step(pipeline, name):
    return next(s for s in pipeline.steps if s.name == name)


def test_build_credit_risk_pipeline_definition():
    cfg = ModelConfig.load(EXAMPLE)
    pipeline = build_steps(cfg)
    assert pipeline.name == "demo-credit-risk"
    assert [s.name for s in pipeline.steps] == ["Train", "Evaluate", "CheckMetric"]
    assert {p.name for p in pipeline.parameters} == set(PIPELINE_PARAMETERS)


def test_gate_publishes_candidate_and_never_registers():
    pipeline = build_steps(ModelConfig.load(EXAMPLE))
    gate = _step(pipeline, "CheckMetric")
    assert [s.name for s in gate.if_steps] == ["PublishCandidate"]
    assert gate.else_steps == []
    all_names = {s.name for s in pipeline.steps} | {s.name for s in gate.if_steps}
    assert not any("Register" in n for n in all_names)


def test_train_has_max_runtime_and_tags():
    train = _step(build_steps(ModelConfig.load(EXAMPLE)), "Train")
    assert train.estimator.max_run == 7200
    tags = {t["Key"]: t["Value"] for t in train.estimator.tags}
    assert tags["bu"] == "demo" and tags["project"] == "credit-risk" and tags["version"] == "v1.0.0"


def test_multiple_thresholds_all_gated(tmp_path):
    raw = yaml.safe_load(open(EXAMPLE, encoding="utf-8"))
    raw["evaluation"]["thresholds"]["accuracy"] = 0.6
    path = tmp_path / "model.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    gate = _step(build_steps(ModelConfig.load(path)), "CheckMetric")
    assert len(gate.conditions) == 2


def test_build_pipeline_with_prepare_enabled(tmp_path):
    raw = yaml.safe_load(open(EXAMPLE, encoding="utf-8"))
    raw["steps"]["prepare"]["enabled"] = True
    path = tmp_path / "model.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    cfg = ModelConfig.load(path)
    assert cfg.prepare_enabled is True
    names = [s.name for s in build_steps(cfg).steps]
    assert names == ["Preprocess", "Train", "Evaluate", "CheckMetric"]


def test_run_parameters_require_digest_and_commit():
    with pytest.raises(ValueError, match="digest"):
        pipeline_parameters("123.dkr.ecr.us-east-1.amazonaws.com/m:latest", "s3://b/d", "s3://b/o", "abc")
    with pytest.raises(ValueError, match="source-commit"):
        pipeline_parameters("123.dkr.ecr.us-east-1.amazonaws.com/m@sha256:" + "a" * 64, "s3://b/d", "s3://b/o", "")
    params = pipeline_parameters(
        "123.dkr.ecr.us-east-1.amazonaws.com/m@sha256:" + "a" * 64, "s3://b/d", "s3://b/o", "abc"
    )
    assert [p["Name"] for p in params] == list(PIPELINE_PARAMETERS)
