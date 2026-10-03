"""Evaluate ProcessingStep — writes metrics.json for the condition gate."""

from __future__ import annotations

from sagemaker.processing import ProcessingInput, ProcessingOutput, ScriptProcessor
from sagemaker.workflow.functions import Join
from sagemaker.workflow.parameters import ParameterString
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.steps import ProcessingStep, TrainingStep

from ml_platform.config import ModelConfig
from ml_platform.steps.common import resource_tags, script_path


def build_evaluate_step(
    cfg: ModelConfig,
    *,
    role_arn: str | None,
    train_step: TrainingStep,
    image_uri: ParameterString,
    data_uri: ParameterString,
    output_prefix: ParameterString,
    instance_type: str,
    preprocess_step: ProcessingStep | None = None,
) -> tuple[ProcessingStep, PropertyFile]:
    processor = ScriptProcessor(
        image_uri=image_uri,
        command=["python3"],
        instance_type=instance_type,
        instance_count=1,
        role=role_arn,
        env={"TARGET_COLUMN": cfg.target_column, "MODEL_NAME": cfg.model_id},
        tags=resource_tags(cfg.tags()),
    )
    evaluation_report = PropertyFile(
        name="EvaluationReport",
        output_name="evaluation",
        path="metrics.json",
    )

    if preprocess_step is not None:
        eval_data = ProcessingInput(
            source=preprocess_step.properties.ProcessingOutputConfig.Outputs["validation"].S3Output.S3Uri,
            destination="/opt/ml/processing/input",
        )
    else:
        eval_data = ProcessingInput(source=data_uri, destination="/opt/ml/processing/input")

    step = ProcessingStep(
        name="Evaluate",
        processor=processor,
        inputs=[
            ProcessingInput(
                source=train_step.properties.ModelArtifacts.S3ModelArtifacts,
                destination="/opt/ml/processing/model",
            ),
            eval_data,
        ],
        outputs=[
            ProcessingOutput(
                output_name="evaluation",
                source="/opt/ml/processing/output",
                destination=Join(on="/", values=[output_prefix, "evaluation"]),
            )
        ],
        property_files=[evaluation_report],
        code=script_path(cfg.model_id, "evaluate.py"),
        job_arguments=["--target-column", cfg.target_column, "--model-name", cfg.model_id],
    )
    return step, evaluation_report
