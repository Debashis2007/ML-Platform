"""SageMaker Pipeline step assembly — evaluation pipeline modules."""

from __future__ import annotations

from ml_platform.config import PipelineConfig
from ml_platform.steps.condition import build_condition_step
from ml_platform.steps.evaluate import build_evaluate_step
from ml_platform.steps.preprocess import build_preprocess_step
from ml_platform.steps.register import build_register_step
from ml_platform.steps.train import build_train_step


def build_steps(cfg: PipelineConfig, role_arn: str | None = None):
    """Return a SageMaker Pipeline: Preprocess? → Train → Evaluate → CheckMetric → Register."""
    from sagemaker.workflow.parameters import ParameterString
    from sagemaker.workflow.pipeline import Pipeline

    image_uri = ParameterString(name="ImageUri", default_value="")
    data_uri = ParameterString(name="DataUri", default_value="")
    output_prefix = ParameterString(name="OutputPrefix", default_value="")
    instance_type = cfg.train_instance

    steps = []
    if cfg.features_enabled:
        steps.append(
            build_preprocess_step(
                cfg,
                role_arn=role_arn,
                image_uri=image_uri,
                data_uri=data_uri,
                output_prefix=output_prefix,
                instance_type=instance_type,
            )
        )

    train_step = build_train_step(cfg, role_arn=role_arn, data_uri=data_uri, instance_type=instance_type)
    evaluate_step, evaluation_report = build_evaluate_step(
        cfg,
        role_arn=role_arn,
        train_step=train_step,
        image_uri=image_uri,
        data_uri=data_uri,
        output_prefix=output_prefix,
        instance_type=instance_type,
    )
    register_step = build_register_step(
        cfg,
        role_arn=role_arn,
        train_step=train_step,
        image_uri=image_uri,
        instance_type=instance_type,
    )
    condition_step = build_condition_step(
        cfg,
        evaluate_step=evaluate_step,
        evaluation_report=evaluation_report,
        register_step=register_step,
    )

    steps.extend([train_step, evaluate_step, condition_step])
    return Pipeline(
        name=cfg.model_name,
        parameters=[image_uri, data_uri, output_prefix],
        steps=steps,
    )
