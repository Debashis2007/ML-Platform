"""PublishCandidate ProcessingStep — writes candidate.json for copy-in registration."""

from __future__ import annotations

import json
from pathlib import Path

from sagemaker.processing import ProcessingInput, ProcessingOutput, ScriptProcessor
from sagemaker.workflow.functions import Join
from sagemaker.workflow.parameters import ParameterString
from sagemaker.workflow.steps import ProcessingStep, TrainingStep

from ml_platform.config import ModelConfig
from ml_platform.steps.common import resource_tags

PUBLISH_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish_candidate.py"


def build_publish_step(
    cfg: ModelConfig,
    *,
    role_arn: str | None,
    train_step: TrainingStep,
    evaluate_step: ProcessingStep,
    image_uri: ParameterString,
    output_prefix: ParameterString,
    source_commit: ParameterString,
    lineage_source_package_arn: ParameterString,
    instance_type: str,
) -> ProcessingStep:
    processor = ScriptProcessor(
        image_uri=image_uri,
        command=["python3"],
        instance_type=instance_type,
        instance_count=1,
        role=role_arn,
        tags=resource_tags(cfg.tags()),
    )
    model_data = train_step.properties.ModelArtifacts.S3ModelArtifacts
    return ProcessingStep(
        name="PublishCandidate",
        processor=processor,
        inputs=[
            ProcessingInput(source=model_data, destination="/opt/ml/processing/model"),
            ProcessingInput(
                source=evaluate_step.properties.ProcessingOutputConfig.Outputs["evaluation"].S3Output.S3Uri,
                destination="/opt/ml/processing/evaluation",
            ),
        ],
        outputs=[
            ProcessingOutput(
                output_name="candidate",
                source="/opt/ml/processing/output",
                destination=Join(on="/", values=[output_prefix, "candidate"]),
            )
        ],
        code=str(PUBLISH_SCRIPT),
        job_arguments=[
            "--model-data-url", model_data,
            "--image-uri", image_uri,
            "--source-commit", source_commit,
            "--tenant-id", cfg.tenant_id,
            "--model-id", cfg.model_id,
            "--model-package-group", cfg.model_package_group,
            "--platform-version", cfg.platform_version,
            "--source-account-id", cfg.account_id,
            "--thresholds", json.dumps(cfg.thresholds, sort_keys=True),
            "--lineage-source-package-arn", lineage_source_package_arn,
        ],
    )
