"""SageMaker Pipeline step assembly — evaluation pipeline modules."""

from __future__ import annotations

from typing import Any

from ml_platform.config import PipelineConfig
from ml_platform.steps.condition import build_condition_step
from ml_platform.steps.evaluate import build_evaluate_step
from ml_platform.steps.preprocess import build_preprocess_step
from ml_platform.steps.register import build_register_step
from ml_platform.steps.train import build_train_step


def build_steps(cfg: PipelineConfig, role_arn: str | None = None) -> Any:
    """Return a SageMaker Pipeline: Preprocess? → Train → Evaluate → CheckMetric → Register."""
    from sagemaker.workflow.parameters import ParameterString
    from sagemaker.workflow.pipeline import Pipeline

    # Definition-only builds (CI validate) need a placeholder role; upsert requires a real ARN.
    effective_role = role_arn or "arn:aws:iam::000000000000:role/ml-platform-pipeline-placeholder"

    image_uri = ParameterString(name="ImageUri", default_value="")
    data_uri = ParameterString(name="DataUri", default_value=cfg.train_uri or "")
    output_prefix = ParameterString(name="OutputPrefix", default_value="")

    steps: list[Any] = []
    preprocess_step = None
    if cfg.features_enabled:
        preprocess_step = build_preprocess_step(
            cfg,
            role_arn=effective_role,
            image_uri=image_uri,
            data_uri=data_uri,
            output_prefix=output_prefix,
            instance_type=cfg.train_instance,
        )
        steps.append(preprocess_step)

    train_step = build_train_step(
        cfg,
        role_arn=effective_role,
        data_uri=data_uri,
        instance_type=cfg.train_instance,
        preprocess_step=preprocess_step,
    )
    evaluate_step, evaluation_report = build_evaluate_step(
        cfg,
        role_arn=effective_role,
        train_step=train_step,
        image_uri=image_uri,
        data_uri=data_uri,
        output_prefix=output_prefix,
        instance_type=cfg.evaluate_instance,
        preprocess_step=preprocess_step,
    )
    steps.extend([train_step, evaluate_step])

    if cfg.register_enabled:
        register_step = build_register_step(
            cfg,
            role_arn=effective_role,
            train_step=train_step,
            image_uri=image_uri,
            instance_type=cfg.evaluate_instance,
        )
        condition_step = build_condition_step(
            cfg,
            evaluate_step=evaluate_step,
            evaluation_report=evaluation_report,
            register_step=register_step,
        )
        steps.append(condition_step)

    return Pipeline(
        name=cfg.model_name,
        parameters=[image_uri, data_uri, output_prefix],
        steps=steps,
    )
