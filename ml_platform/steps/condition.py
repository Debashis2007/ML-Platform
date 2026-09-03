"""Metric condition gate (CheckMetric ConditionStep)."""

from __future__ import annotations

from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.functions import JsonGet
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.steps import ProcessingStep

from ml_platform.config import PipelineConfig


def build_condition_step(
    cfg: PipelineConfig,
    *,
    evaluate_step: ProcessingStep,
    evaluation_report: PropertyFile,
    register_step: ProcessingStep,
) -> ConditionStep:
    condition = ConditionGreaterThanOrEqualTo(
        left=JsonGet(
            step_name=evaluate_step.name,
            property_file=evaluation_report,
            json_path=f"$.{cfg.threshold_metric}",
        ),
        right=cfg.threshold_min,
    )
    return ConditionStep(
        name="CheckMetric",
        conditions=[condition],
        if_steps=[register_step],
        else_steps=[],
    )
