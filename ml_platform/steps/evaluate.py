"""Evaluate ProcessingStep — writes metrics.json for the condition gate."""

from __future__ import annotations

from sagemaker.processing import ProcessingInput, ProcessingOutput, ScriptProcessor
from sagemaker.workflow.parameters import ParameterString
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.steps import ProcessingStep, TrainingStep

from ml_platform.config import PipelineConfig
from ml_platform.steps.common import script_path


def build_evaluate_step(
    cfg: PipelineConfig,
    *,
    role_arn: str | None,
    train_step: TrainingStep,
    image_uri: ParameterString,
    data_uri: ParameterString,
    output_prefix: ParameterString,
    instance_type: str,
) -> tuple[ProcessingStep, PropertyFile]:
    processor = ScriptProcessor(
        image_uri=image_uri,
        command=["python3"],
        instance_type=instance_type,
        instance_count=1,
        role=role_arn,
    )
    evaluation_report = PropertyFile(
        name="EvaluationReport",
        output_name="evaluation",
        path="metrics.json",
    )
    step = ProcessingStep(
        name="Evaluate",
        processor=processor,
        inputs=[
            ProcessingInput(
                source=train_step.properties.ModelArtifacts.S3ModelArtifacts,
                destination="/opt/ml/processing/model",
            ),
            ProcessingInput(source=data_uri, destination="/opt/ml/processing/input"),
        ],
        outputs=[
            ProcessingOutput(
                output_name="evaluation",
                source="/opt/ml/processing/output",
                destination=f"{output_prefix}/evaluation",
            )
        ],
        property_files=[evaluation_report],
        code=script_path(cfg.model_name, "evaluate.py"),
    )
    return step, evaluation_report
