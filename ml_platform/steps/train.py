"""Train ProcessingStep (SKLearn estimator)."""

from __future__ import annotations

from sagemaker.sklearn import SKLearn
from sagemaker.workflow.parameters import ParameterString
from sagemaker.workflow.steps import TrainingStep

from ml_platform.config import PipelineConfig
from ml_platform.steps.common import model_source_dir


def build_train_step(
    cfg: PipelineConfig,
    *,
    role_arn: str | None,
    data_uri: ParameterString,
    instance_type: str,
) -> TrainingStep:
    estimator = SKLearn(
        entry_point="train.py",
        source_dir=str(model_source_dir(cfg.model_name)),
        role=role_arn,
        instance_type=instance_type,
        framework_version="1.2-1",
        py_version="py3",
        hyperparameters={"model-name": cfg.model_name},
    )
    return TrainingStep(name="Train", estimator=estimator, inputs={"train": data_uri})
