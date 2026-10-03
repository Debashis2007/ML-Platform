"""Load and validate model.yaml — the per-model configuration surface (ML design v7).

The configuration names the training target (account, region, pipeline role), the
evaluation gate, the serving contract and the deployment targets. Infrastructure and IAM
roles are never created from it; it only selects them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml

_S3_URI = re.compile(r"^s3://[a-z0-9][a-z0-9.\-]{1,61}[a-z0-9](/.*)?$", re.IGNORECASE)
_INSTANCE = re.compile(r"^ml\.[a-z0-9]+\.[a-z0-9]+$", re.IGNORECASE)
_ACCOUNT = re.compile(r"^\d{12}$")
_REGION = re.compile(r"^[a-z]{2}(-gov)?-[a-z]+-\d$")
_ROLE_ARN = re.compile(r"^arn:aws:iam::(\d{12}):role/[\w+=,.@/-]+$")
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
_DURATION = re.compile(r"^(\d+)\s*([smhd])$")

MODEL_TYPES = {"bu_specific", "enterprise"}
TRAINING_TARGETS = {"control_plane", "bu"}
STAGES = {"nonprod", "prod"}
ENVIRONMENTS = {"qa", "live"}
MAX_TRAINING_SECONDS = 5 * 24 * 3600


def _require(data: dict[str, Any], key: str, where: str) -> Any:
    value = data.get(key)
    if value is None or (isinstance(value, str) and value.strip() == ""):
        raise ValueError(f"model.yaml must define non-empty '{where}.{key}'" if where else
                         f"model.yaml must define non-empty '{key}'")
    return value


def _mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key) or {}
    if not isinstance(value, dict):
        raise ValueError(f"model.yaml '{key}' must be a mapping")
    return value


def _account(value: Any, field: str) -> str:
    text = str(value).strip()
    if not _ACCOUNT.match(text):
        raise ValueError(f"{field} must be a 12-digit account ID quoted as a string, got {value!r}")
    return text


def _instance(value: Any, field: str) -> str:
    text = str(value).strip()
    if not _INSTANCE.match(text):
        raise ValueError(f"{field} looks invalid: {text!r}")
    return text


def _seconds(value: Any, field: str) -> int:
    match = _DURATION.match(str(value).strip().lower())
    if not match:
        raise ValueError(f"{field} must look like '30m', '4h' or '1d', got {value!r}")
    amount, unit = int(match.group(1)), match.group(2)
    seconds = amount * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    if not 0 < seconds <= MAX_TRAINING_SECONDS:
        raise ValueError(f"{field} must be between 1s and 5d")
    return seconds


def _package_group_default(model_id: str) -> str:
    return "Model" + "".join(p.capitalize() for p in re.split(r"[-_]+", model_id) if p)


@dataclass(frozen=True)
class DeploymentTarget:
    account: str
    account_id: str
    environment: str
    instance_count: int


@dataclass(frozen=True)
class ModelConfig:
    raw: dict[str, Any]
    model_id: str
    tenant_id: str
    bu: str
    model_type: str
    project: str
    platform_version: str
    training_target: str
    account_id: str
    region: str
    pipeline_role_arn: str
    train_uri: str | None
    target_column: str
    dataset_contract: str | None
    prepare_enabled: bool
    train_instance: str
    train_max_runtime_seconds: int
    framework_version: str
    evaluate_instance: str
    metrics: tuple[str, ...]
    thresholds: dict[str, float]
    model_package_group: str
    serving_contract_version: str
    serving_instance: str
    serving_instance_count: int
    deployment_targets: tuple[DeploymentTarget, ...]
    approvers: tuple[str, ...]
    monitoring: str | None

    @property
    def primary_metric(self) -> str:
        return next(iter(self.thresholds))

    @property
    def primary_threshold(self) -> float:
        return self.thresholds[self.primary_metric]

    @property
    def pipeline_name(self) -> str:
        return f"{self.tenant_id}-{self.model_id}"

    def tags(self) -> dict[str, str]:
        """Tags applied to every resource created for this model."""
        return {
            "bu": self.bu,
            "project": self.project,
            "version": self.platform_version,
            "tenant_id": self.tenant_id,
            "model_id": self.model_id,
        }

    def target(self, environment: str) -> DeploymentTarget:
        for target in self.deployment_targets:
            if target.environment == environment:
                return target
        raise KeyError(f"No deployment target for environment {environment!r}")

    def for_stage(self, stage: str) -> ModelConfig:
        """NonProd as configured, or the Prod retrain target from aws.prod (promotion by digest)."""
        if stage not in STAGES:
            raise ValueError(f"stage must be one of {sorted(STAGES)}")
        if stage == "nonprod":
            return self
        prod = (self.raw.get("aws") or {}).get("prod")
        if not isinstance(prod, dict):
            raise ValueError("model.yaml must define aws.prod for the Prod retrain")
        account_id = _account(_require(prod, "account_id", "aws.prod"), "aws.prod.account_id")
        role_arn = str(_require(prod, "pipeline_role_arn", "aws.prod")).strip()
        match = _ROLE_ARN.match(role_arn)
        if not match or match.group(1) != account_id:
            raise ValueError("aws.prod.pipeline_role_arn must be an IAM role in aws.prod.account_id")
        train_uri = str(prod.get("train_uri") or "").strip() or None
        if train_uri and not _S3_URI.match(train_uri):
            raise ValueError(f"aws.prod.train_uri must be a valid s3:// URI, got: {train_uri!r}")
        return replace(
            self,
            account_id=account_id,
            region=str(prod.get("region", self.region)),
            pipeline_role_arn=role_arn,
            train_uri=train_uri or self.train_uri,
        )

    @classmethod
    def load(cls, path: Path | str, stage: str = "nonprod") -> ModelConfig:
        config_path = Path(path)
        if not config_path.is_file():
            raise FileNotFoundError(f"model.yaml not found: {config_path}")
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("model.yaml must be a mapping")
        return cls.from_dict(data).for_stage(stage)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelConfig:
        if not isinstance(data.get("model"), dict):
            raise ValueError("model.yaml must define a 'model' mapping")
        model = data["model"]
        aws = _mapping(data, "aws")
        data_block = _mapping(data, "data")
        steps = _mapping(data, "steps")
        evaluation = _mapping(data, "evaluation")
        serving = _mapping(data, "serving")
        deployment = _mapping(data, "deployment")
        registry = _mapping(data, "registry")

        model_id = str(_require(model, "id", "model")).strip()
        if not _SLUG.match(model_id):
            raise ValueError(f"model.id must be lowercase letters, digits and hyphens: {model_id!r}")
        tenant_id = str(_require(model, "tenant_id", "model")).strip()
        bu = str(model.get("bu", tenant_id)).strip()
        model_type = str(model.get("type", "bu_specific")).strip()
        if model_type not in MODEL_TYPES:
            raise ValueError(f"model.type must be one of {sorted(MODEL_TYPES)}")
        if model_type == "enterprise":
            raise ValueError("model.type 'enterprise' is reserved for the enterprise tenant account "
                             "and is not available in phase 1")
        platform_version = str(_require(model, "platform_version", "model")).strip()

        training_target = str(aws.get("training_target", "control_plane")).strip()
        if training_target not in TRAINING_TARGETS:
            raise ValueError(f"aws.training_target must be one of {sorted(TRAINING_TARGETS)}")
        account_id = _account(_require(aws, "account_id", "aws"), "aws.account_id")
        region = str(aws.get("region", "us-east-1")).strip()
        if not _REGION.match(region):
            raise ValueError(f"aws.region looks invalid: {region!r}")
        role_arn = str(_require(aws, "pipeline_role_arn", "aws")).strip()
        role_match = _ROLE_ARN.match(role_arn)
        if not role_match:
            raise ValueError(f"aws.pipeline_role_arn is not an IAM role ARN: {role_arn!r}")
        if role_match.group(1) != account_id:
            raise ValueError("aws.pipeline_role_arn must belong to aws.account_id")

        train_uri = data_block.get("train_uri")
        if train_uri is not None and str(train_uri).strip():
            train_uri = str(train_uri).strip()
            if not _S3_URI.match(train_uri):
                raise ValueError(f"data.train_uri must be a valid s3:// URI, got: {train_uri!r}")
        else:
            train_uri = None

        prepare = steps.get("prepare") or {}
        train = steps.get("train") or {}
        evaluate = steps.get("evaluate") or {}
        if not bool(train.get("enabled", True)):
            raise ValueError("steps.train.enabled cannot be false — training is required")
        if not bool(evaluate.get("enabled", True)):
            raise ValueError("steps.evaluate.enabled cannot be false — the evaluation gate is required")
        train_instance = _instance(train.get("instance", "ml.m5.xlarge"), "steps.train.instance")
        evaluate_instance = _instance(evaluate.get("instance", train_instance), "steps.evaluate.instance")

        thresholds_raw = evaluation.get("thresholds") or {}
        if not isinstance(thresholds_raw, dict) or not thresholds_raw:
            raise ValueError("evaluation.thresholds must name at least one metric and its minimum")
        thresholds: dict[str, float] = {}
        for metric, value in thresholds_raw.items():
            minimum = float(value)
            if not 0.0 <= minimum <= 1.0:
                raise ValueError(f"evaluation.thresholds.{metric} threshold must be between 0 and 1")
            thresholds[str(metric)] = minimum
        metrics = tuple(str(m) for m in (evaluation.get("metrics") or thresholds.keys()))
        missing = [m for m in thresholds if m not in metrics]
        if missing:
            raise ValueError(f"evaluation.thresholds names metrics not in evaluation.metrics: {missing}")

        serving_instance = _instance(serving.get("instance", "ml.m5.large"), "serving.instance")
        serving_count = int(serving.get("instance_count", 2))
        if serving_count < 1:
            raise ValueError("serving.instance_count must be at least 1")

        targets: list[DeploymentTarget] = []
        for i, item in enumerate(deployment.get("targets") or []):
            if not isinstance(item, dict):
                raise ValueError(f"deployment.targets[{i}] must be a mapping")
            env = str(_require(item, "environment", f"deployment.targets[{i}]")).strip()
            if env not in ENVIRONMENTS:
                raise ValueError(f"deployment.targets[{i}].environment must be one of {sorted(ENVIRONMENTS)}")
            count = int(item.get("instance_count", serving_count))
            if env == "live" and count < 2:
                raise ValueError("LIVE requires at least two instances so one instance or AZ "
                                 "failure does not take the endpoint out")
            targets.append(DeploymentTarget(
                account=str(_require(item, "account", f"deployment.targets[{i}]")).strip(),
                account_id=_account(_require(item, "account_id", f"deployment.targets[{i}]"),
                                    f"deployment.targets[{i}].account_id"),
                environment=env,
                instance_count=count,
            ))
        if len({t.environment for t in targets}) != len(targets):
            raise ValueError("deployment.targets must list each environment once")

        approvers = tuple(str(a).strip() for a in (data.get("approvers") or []) if str(a).strip())
        if not approvers:
            raise ValueError("approvers must name at least one senior data scientist")

        return cls(
            raw=data,
            model_id=model_id,
            tenant_id=tenant_id,
            bu=bu,
            model_type=model_type,
            project=str(model.get("project", model_id)).strip(),
            platform_version=platform_version,
            training_target=training_target,
            account_id=account_id,
            region=region,
            pipeline_role_arn=role_arn,
            train_uri=train_uri,
            target_column=str(data_block.get("target_column", "default")),
            dataset_contract=data_block.get("contract"),
            prepare_enabled=bool(prepare.get("enabled", False)),
            train_instance=train_instance,
            train_max_runtime_seconds=_seconds(train.get("max_runtime", "4h"), "steps.train.max_runtime"),
            framework_version=str(train.get("framework_version", "1.2-1")),
            evaluate_instance=evaluate_instance,
            metrics=metrics,
            thresholds=thresholds,
            model_package_group=str(registry.get("model_package_group") or _package_group_default(model_id)),
            serving_contract_version=str(serving.get("contract_version", "1.0")),
            serving_instance=serving_instance,
            serving_instance_count=serving_count,
            deployment_targets=tuple(targets),
            approvers=approvers,
            monitoring=data.get("monitoring"),
        )


PipelineConfig = ModelConfig
