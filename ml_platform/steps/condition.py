"""Metric condition gate (CheckMetric ConditionStep) — every threshold must pass."""

from __future__ import annotations

from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.functions import JsonGet
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.steps import ProcessingStep

from ml_platform.config import ModelConfig


def build_condition_step(
    cfg: ModelConfig,
    *,
    evaluate_step: ProcessingStep,
    evaluation_report: PropertyFile,
    publish_step: ProcessingStep,
) -> ConditionStep:
    conditions = [
        ConditionGreaterThanOrEqualTo(
            left=JsonGet(
                step_name=evaluate_step.name,
                property_file=evaluation_report,
                json_path=f"$.{metric}",
            ),
            right=minimum,
        )
        for metric, minimum in cfg.thresholds.items()
    ]
    return ConditionStep(
        name="CheckMetric",
        conditions=conditions,
        if_steps=[publish_step],
        else_steps=[],
    )
