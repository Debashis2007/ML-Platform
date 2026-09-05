"""Optional preprocess ProcessingStep."""

from __future__ import annotations

from sagemaker.processing import ProcessingInput, ProcessingOutput, ScriptProcessor
from sagemaker.workflow.functions import Join
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
        env={"TARGET_COLUMN": cfg.target_column, "MODEL_NAME": cfg.model_name},
    )
    return ProcessingStep(
        name="Preprocess",
        processor=processor,
        inputs=[ProcessingInput(source=data_uri, destination="/opt/ml/processing/input")],
        outputs=[
            ProcessingOutput(
                output_name="train",
                source="/opt/ml/processing/output/train",
                destination=Join(on="/", values=[output_prefix, "processed", "train"]),
            ),
            ProcessingOutput(
                output_name="validation",
                source="/opt/ml/processing/output/validation",
                destination=Join(on="/", values=[output_prefix, "processed", "validation"]),
            ),
        ],
        code=script_path(cfg.model_name, "preprocess.py"),
        job_arguments=["--target-column", cfg.target_column],
    )
