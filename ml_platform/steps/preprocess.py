"""Optional preprocess ProcessingStep."""

from __future__ import annotations

from sagemaker.processing import ProcessingInput, ProcessingOutput, ScriptProcessor
from sagemaker.workflow.parameters import ParameterString
from sagemaker.workflow.steps import ProcessingStep

from ml_platform.config import PipelineConfig
from ml_platform.steps.common import script_path


def build_preprocess_step(
    cfg: PipelineConfig,
    *,
    role_arn: str | None,
    image_uri: ParameterString,
    data_uri: ParameterString,
    output_prefix: ParameterString,
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
        name="Preprocess",
        processor=processor,
        inputs=[ProcessingInput(source=data_uri, destination="/opt/ml/processing/input")],
        outputs=[
            ProcessingOutput(
                output_name="processed",
                source="/opt/ml/processing/output",
                destination=f"{output_prefix}/processed",
            )
        ],
        code=script_path(cfg.model_name, "preprocess.py"),
    )
