"""Tests for model.yaml (ModelConfig) validation."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from ml_platform.config import ModelConfig, PipelineConfig

EXAMPLE = Path("examples/credit-risk/model.yaml")


def _base() -> dict:
    return yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))


def _load(tmp_path: Path, data: dict) -> ModelConfig:
    path = tmp_path / "model.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return ModelConfig.load(path)


def test_load_credit_risk_example():
    cfg = ModelConfig.load(EXAMPLE)
    assert cfg.model_id == "credit-risk"
    assert cfg.tenant_id == "demo"
    assert cfg.model_type == "bu_specific"
    assert cfg.training_target == "control_plane"
    assert cfg.account_id == "848973819860"
    assert cfg.model_package_group == "ModelCreditRisk"
    assert cfg.thresholds == {"auc": 0.75}
    assert cfg.primary_metric == "auc"
    assert cfg.prepare_enabled is False
    assert cfg.train_max_runtime_seconds == 7200
    assert cfg.train_uri.startswith("s3://")
    assert cfg.target("live").instance_count == 2
    assert cfg.pipeline_name == "demo-credit-risk"


def test_tags_carry_bu_project_version():
    tags = ModelConfig.load(EXAMPLE).tags()
    assert tags["bu"] == "demo"
    assert tags["project"] == "credit-risk"
    assert tags["version"] == "v1.0.0"


def test_pipeline_config_alias():
    assert PipelineConfig is ModelConfig


def test_template_parses_shape():
    raw = yaml.safe_load(Path("templates/model-project/model.yaml").read_text(encoding="utf-8"))
    assert raw["aws"]["training_target"] == "control_plane"
    assert {"model", "aws", "data", "steps", "evaluation", "serving", "deployment", "approvers"} <= raw.keys()


def test_rejects_missing_model(tmp_path: Path):
    data = _base()
    del data["model"]
    with pytest.raises(ValueError, match="model"):
        _load(tmp_path, data)


def test_rejects_bad_threshold(tmp_path: Path):
    data = _base()
    data["evaluation"]["thresholds"]["auc"] = 1.5
    with pytest.raises(ValueError, match="threshold"):
        _load(tmp_path, data)


def test_rejects_threshold_not_in_metrics(tmp_path: Path):
    data = _base()
    data["evaluation"]["thresholds"]["f1"] = 0.5
    with pytest.raises(ValueError, match="f1"):
        _load(tmp_path, data)


def test_rejects_invalid_s3_uri(tmp_path: Path):
    data = _base()
    data["data"]["train_uri"] = "http://not-s3/data"
    with pytest.raises(ValueError, match="s3://"):
        _load(tmp_path, data)


def test_evaluate_cannot_be_disabled(tmp_path: Path):
    data = _base()
    data["steps"]["evaluate"]["enabled"] = False
    with pytest.raises(ValueError, match="evaluate"):
        _load(tmp_path, data)


def test_account_id_must_be_twelve_digit_string(tmp_path: Path):
    data = _base()
    data["aws"]["account_id"] = 848973819
    with pytest.raises(ValueError, match="12-digit"):
        _load(tmp_path, data)


def test_role_must_belong_to_training_account(tmp_path: Path):
    data = _base()
    data["aws"]["pipeline_role_arn"] = "arn:aws:iam::111111111111:role/x"
    with pytest.raises(ValueError, match="belong"):
        _load(tmp_path, data)


def test_bu_training_target_accepted(tmp_path: Path):
    data = _base()
    data["aws"].update(
        training_target="bu",
        account_id="546386837851",
        pipeline_role_arn="arn:aws:iam::546386837851:role/demo-ml-pipeline",
    )
    assert _load(tmp_path, data).training_target == "bu"


def test_enterprise_type_reserved(tmp_path: Path):
    data = _base()
    data["model"]["type"] = "enterprise"
    with pytest.raises(ValueError, match="reserved"):
        _load(tmp_path, data)


def test_live_requires_two_instances(tmp_path: Path):
    data = _base()
    data["deployment"]["targets"][1]["instance_count"] = 1
    with pytest.raises(ValueError, match="LIVE"):
        _load(tmp_path, data)


def test_approvers_required(tmp_path: Path):
    data = _base()
    data["approvers"] = []
    with pytest.raises(ValueError, match="approvers"):
        _load(tmp_path, data)


def test_max_runtime_bounds(tmp_path: Path):
    data = copy.deepcopy(_base())
    data["steps"]["train"]["max_runtime"] = "9d"
    with pytest.raises(ValueError, match="max_runtime"):
        _load(tmp_path, data)


def test_package_group_default(tmp_path: Path):
    data = _base()
    data["model"]["id"] = "fraud-detection"
    del data["registry"]
    assert _load(tmp_path, data).model_package_group == "ModelFraudDetection"


def test_prod_stage_retargets_training_account():
    cfg = ModelConfig.load(EXAMPLE, stage="prod")
    assert cfg.account_id == "762794225431"
    assert cfg.pipeline_role_arn.startswith("arn:aws:iam::762794225431:")
    assert cfg.train_uri.startswith("s3://mlp-prod-model-data/")
    assert cfg.model_package_group == "ModelCreditRisk"


def test_prod_stage_requires_block(tmp_path: Path):
    data = _base()
    del data["aws"]["prod"]
    path = tmp_path / "model.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert ModelConfig.load(path).account_id == "848973819860"
    with pytest.raises(ValueError, match="aws.prod"):
        ModelConfig.load(path, stage="prod")
