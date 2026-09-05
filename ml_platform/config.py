"""Load and validate pipeline.yaml for a model project."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_S3_URI = re.compile(r"^s3://[a-z0-9][a-z0-9.\-]{1,61}[a-z0-9](/.*)?$", re.IGNORECASE)
_INSTANCE = re.compile(r"^ml\.[a-z0-9]+\.[a-z0-9]+$", re.IGNORECASE)


def _require_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if value is None or str(value).strip() == "":
        raise ValueError(f"pipeline.yaml must define non-empty '{key}'")
    return str(value).strip()


def _optional_s3(uri: str | None, field: str) -> str | None:
    if uri is None or str(uri).strip() == "":
        return None
    value = str(uri).strip()
    if not _S3_URI.match(value):
        raise ValueError(f"{field} must be a valid s3:// URI, got: {value!r}")
    return value


def _package_group_default(model_name: str) -> str:
    parts = re.split(r"[-_]+", model_name)
    return "Model" + "".join(p.capitalize() for p in parts if p)


@dataclass(frozen=True)
class PipelineConfig:
    raw: dict[str, Any]
    model_name: str
    owner_bu: str
    threshold_metric: str
    threshold_min: float
    deployment_target: str
    environment: str
    train_instance: str
    evaluate_instance: str
    features_enabled: bool
    train_enabled: bool
    evaluate_enabled: bool
    register_enabled: bool
    model_package_group: str
    train_uri: str | None
    target_column: str
    framework_version: str

    @classmethod
    def load(cls, path: Path | str) -> PipelineConfig:
        config_path = Path(path)
        if not config_path.is_file():
            raise FileNotFoundError(f"pipeline.yaml not found: {config_path}")

        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("pipeline.yaml must be a mapping")
        if "model" not in data:
            raise ValueError("pipeline.yaml must define 'model'")

        steps = data.get("steps") or {}
        if not isinstance(steps, dict):
            raise ValueError("pipeline.yaml 'steps' must be a mapping")

        train = steps.get("train") or {}
        evaluate = steps.get("evaluate") or {}
        cond = steps.get("conditional_register") or {}
        features = steps.get("features") or {}
        deploy = data.get("deployment") or {}
        data_block = data.get("data") or {}

        env = str(data.get("environment", deploy.get("environment", "dev")))
        threshold = cond.get("threshold", cond.get("metric", {}))
        if isinstance(threshold, dict):
            metric = threshold.get("metric", cond.get("metric", "auc"))
            min_val = float(threshold.get("min", cond.get("threshold", 0.75)))
        else:
            metric = cond.get("metric", "auc")
            min_val = float(threshold if threshold is not None else 0.75)

        if not (0.0 <= min_val <= 1.0):
            raise ValueError("threshold must be between 0 and 1")

        train_instance = str(train.get("instance", "ml.m5.xlarge"))
        evaluate_instance = str(evaluate.get("instance", train_instance))
        for label, value in (("train.instance", train_instance), ("evaluate.instance", evaluate_instance)):
            if not _INSTANCE.match(value):
                raise ValueError(f"{label} looks invalid: {value!r}")

        model_name = _require_str(data, "model")
        package_group = str(
            data.get("model_package_group")
            or deploy.get("model_package_group")
            or _package_group_default(model_name)
        )

        train_enabled = bool(train.get("enabled", True))
        evaluate_enabled = bool(evaluate.get("enabled", True))
        register_enabled = bool(cond.get("enabled", True))
        if not train_enabled:
            raise ValueError("steps.train.enabled cannot be false — training is required")
        if register_enabled and not evaluate_enabled:
            raise ValueError("conditional_register requires steps.evaluate.enabled=true")

        return cls(
            raw=data,
            model_name=model_name,
            owner_bu=str(data.get("owner_bu", "platform")),
            threshold_metric=str(metric),
            threshold_min=min_val,
            deployment_target=str(deploy.get("target", "central")),
            environment=env,
            train_instance=train_instance,
            evaluate_instance=evaluate_instance,
            features_enabled=bool(features.get("enabled", False)),
            train_enabled=train_enabled,
            evaluate_enabled=evaluate_enabled,
            register_enabled=register_enabled,
            model_package_group=package_group,
            train_uri=_optional_s3(data_block.get("train_uri"), "data.train_uri"),
            target_column=str(data.get("target_column", "default")),
            framework_version=str(train.get("framework_version", "1.2-1")),
        )
