"""Train ProcessingStep (SKLearn estimator)."""

from __future__ import annotations

from sagemaker.inputs import TrainingInput
from sagemaker.sklearn import SKLearn
from sagemaker.workflow.parameters import ParameterString
from sagemaker.workflow.steps import ProcessingStep, TrainingStep

from ml_platform.config import PipelineConfig
from ml_platform.steps.common import model_source_dir


def build_train_step(
    cfg: PipelineConfig,
    *,
    role_arn: str | None,
    data_uri: ParameterString | str,
    instance_type: str,
    preprocess_step: ProcessingStep | None = None,
) -> TrainingStep:
    estimator = SKLearn(
        entry_point="train.py",
        source_dir=str(model_source_dir(cfg.model_name)),
        role=role_arn,
        instance_type=instance_type,
        framework_version=cfg.framework_version,
        py_version="py3",
        hyperparameters={
            "model-name": cfg.model_name,
            "target-column": cfg.target_column,
        },
        environment={"TARGET_COLUMN": cfg.target_column, "MODEL_NAME": cfg.model_name},
    )

    if preprocess_step is not None:
        train_input = TrainingInput(
            s3_data=preprocess_step.properties.ProcessingOutputConfig.Outputs["train"].S3Output.S3Uri,
            content_type="text/csv",
        )
    else:
        train_input = TrainingInput(s3_data=data_uri, content_type="text/csv")

    return TrainingStep(name="Train", estimator=estimator, inputs={"train": train_input})
