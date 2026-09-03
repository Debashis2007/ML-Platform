"""Load and validate pipeline.yaml for a model project."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PipelineConfig:
    raw: dict[str, Any]
    model_name: str
    owner_bu: str
    threshold_metric: str
    threshold_min: float
    deployment_target: str
    train_instance: str
    features_enabled: bool

    @classmethod
    def load(cls, path: Path | str) -> PipelineConfig:
        data = yaml.safe_load(Path(path).read_text())
        if not data or "model" not in data:
            raise ValueError("pipeline.yaml must define 'model'")
        steps = data.get("steps", {})
        train = steps.get("train", {})
        cond = steps.get("conditional_register", {})
        deploy = data.get("deployment", {})
        threshold = cond.get("threshold", cond.get("metric", {}))
        if isinstance(threshold, dict):
            metric = threshold.get("metric", cond.get("metric", "auc"))
            min_val = float(threshold.get("min", cond.get("threshold", 0.75)))
        else:
            metric = cond.get("metric", "auc")
            min_val = float(threshold if threshold is not None else 0.75)
        if not (0.0 <= min_val <= 1.0):
            raise ValueError("threshold must be between 0 and 1")
        return cls(
            raw=data,
            model_name=str(data["model"]),
            owner_bu=str(data.get("owner_bu", "platform")),
            threshold_metric=str(metric),
            threshold_min=min_val,
            deployment_target=str(deploy.get("target", "central")),
            train_instance=str(train.get("instance", "ml.m5.xlarge")),
            features_enabled=bool(steps.get("features", {}).get("enabled", False)),
        )
