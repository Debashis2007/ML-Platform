"""Register ProcessingStep — creates Pending Approval model package."""

from __future__ import annotations

from sagemaker.processing import ProcessingInput, ScriptProcessor
from sagemaker.workflow.parameters import ParameterString
from sagemaker.workflow.steps import ProcessingStep, TrainingStep

from ml_platform.config import PipelineConfig
from ml_platform.steps.common import script_path


def build_register_step(
    cfg: PipelineConfig,
    *,
    role_arn: str | None,
    train_step: TrainingStep,
    image_uri: ParameterString,
    instance_type: str,
) -> ProcessingStep:
    processor = ScriptProcessor(
        image_uri=image_uri,
        command=["python3"],
        instance_type=instance_type,
        instance_count=1,
        role=role_arn,
    )
    return ProcessingStep(
        name="RegisterModel",
        processor=processor,
        inputs=[
            ProcessingInput(
                source=train_step.properties.ModelArtifacts.S3ModelArtifacts,
                destination="/opt/ml/processing/model",
            )
        ],
        code=script_path(cfg.model_name, "register.py"),
    )
