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
    """Register via processing script.

    Image URI and model data URL are passed as pipeline parameters/properties through
    job arguments (resolved at execution time by SageMaker).
    """
    processor = ScriptProcessor(
        image_uri=image_uri,
        command=["python3"],
        instance_type=instance_type,
        instance_count=1,
        role=role_arn,
        env={
            "MODEL_PACKAGE_GROUP": cfg.model_package_group,
            "MODEL_APPROVAL_STATUS": "PendingManualApproval",
            "MODEL_NAME": cfg.model_name,
        },
    )
    model_data_url = train_step.properties.ModelArtifacts.S3ModelArtifacts
    return ProcessingStep(
        name="RegisterModel",
        processor=processor,
        inputs=[
            ProcessingInput(
                source=model_data_url,
                destination="/opt/ml/processing/model",
            )
        ],
        code=script_path(cfg.model_name, "register.py"),
        job_arguments=[
            "--model-package-group",
            cfg.model_package_group,
            "--inference-image-uri",
            image_uri,
            "--model-data-url",
            model_data_url,
            "--model-name",
            cfg.model_name,
            "--approval-status",
            "PendingManualApproval",
        ],
    )
