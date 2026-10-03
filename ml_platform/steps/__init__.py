"""SageMaker Pipeline step assembly — training account pipeline (design v7).

The pipeline trains and evaluates in the configured training account and, when the
evaluation gate passes, publishes a candidate manifest. Registration is not a pipeline
step: the control-plane registration Lambda copies the candidate in and creates the
PendingManualApproval package.
"""

from __future__ import annotations

from typing import Any

from ml_platform.config import ModelConfig
from ml_platform.steps.condition import build_condition_step
from ml_platform.steps.evaluate import build_evaluate_step
from ml_platform.steps.preprocess import build_preprocess_step
from ml_platform.steps.publish import build_publish_step
from ml_platform.steps.train import build_train_step

PIPELINE_PARAMETERS = ("ImageUri", "DataUri", "OutputPrefix", "SourceCommit", "SubmittedBy", "LineageSourcePackageArn")


def build_steps(cfg: ModelConfig, role_arn: str | None = None) -> Any:
    """Return a SageMaker Pipeline: Preprocess? → Train → Evaluate → CheckMetric → PublishCandidate."""
    from sagemaker.workflow.parameters import ParameterString
    from sagemaker.workflow.pipeline import Pipeline

    effective_role = role_arn or cfg.pipeline_role_arn

    image_uri = ParameterString(name="ImageUri", default_value="")
    data_uri = ParameterString(name="DataUri", default_value=cfg.train_uri or "")
    output_prefix = ParameterString(name="OutputPrefix", default_value="")
    source_commit = ParameterString(name="SourceCommit", default_value="")
    submitted_by = ParameterString(name="SubmittedBy", default_value="")
    lineage_source = ParameterString(name="LineageSourcePackageArn", default_value="")

    steps: list[Any] = []
    preprocess_step = None
    if cfg.prepare_enabled:
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
        output_prefix=output_prefix,
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
    publish_step = build_publish_step(
        cfg,
        role_arn=effective_role,
        train_step=train_step,
        evaluate_step=evaluate_step,
        image_uri=image_uri,
        output_prefix=output_prefix,
        source_commit=source_commit,
        lineage_source_package_arn=lineage_source,
        instance_type=cfg.evaluate_instance,
    )
    condition_step = build_condition_step(
        cfg,
        evaluate_step=evaluate_step,
        evaluation_report=evaluation_report,
        publish_step=publish_step,
    )
    steps.extend([train_step, evaluate_step, condition_step])

    return Pipeline(
        name=cfg.pipeline_name,
        parameters=[image_uri, data_uri, output_prefix, source_commit, submitted_by, lineage_source],
        steps=steps,
    )
