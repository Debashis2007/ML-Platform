"""SageMaker Pipeline step assembly."""

from __future__ import annotations

from ml_platform.config import PipelineConfig


def build_steps(cfg: PipelineConfig, role_arn: str | None = None):
    """Return a SageMaker Pipeline object (lazy import sagemaker)."""
    from sagemaker.processing import ProcessingInput, ProcessingOutput, ScriptProcessor
    from sagemaker.sklearn import SKLearn
    from sagemaker.workflow.condition_step import ConditionStep
    from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
    from sagemaker.workflow.functions import JsonGet
    from sagemaker.workflow.parameters import ParameterString
    from sagemaker.workflow.pipeline import Pipeline
    from sagemaker.workflow.properties import PropertyFile
    from sagemaker.workflow.steps import ProcessingStep, TrainingStep

    image_uri = ParameterString(name="ImageUri", default_value="")
    data_uri = ParameterString(name="DataUri", default_value="")
    output_prefix = ParameterString(name="OutputPrefix", default_value="")

    sklearn_version = "1.2-1"
    instance_type = cfg.train_instance

    preprocess_step = None
    if cfg.features_enabled:
        processor = ScriptProcessor(
            image_uri=image_uri,
            command=["python3"],
            instance_type=instance_type,
            instance_count=1,
            role=role_arn,
        )
        preprocess_step = ProcessingStep(
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
            code=str(_example_script("preprocess.py")),
        )

    estimator = SKLearn(
        entry_point="train.py",
        source_dir=str(_example_dir(cfg.model_name)),
        role=role_arn,
        instance_type=instance_type,
        framework_version=sklearn_version,
        py_version="py3",
        hyperparameters={"model-name": cfg.model_name},
    )
    train_step = TrainingStep(
        name="Train",
        estimator=estimator,
        inputs={"train": data_uri},
    )

    eval_processor = ScriptProcessor(
        image_uri=image_uri,
        command=["python3"],
        instance_type=instance_type,
        instance_count=1,
        role=role_arn,
    )
    evaluation_report = PropertyFile(name="EvaluationReport", output_name="evaluation", path="metrics.json")
    evaluate_step = ProcessingStep(
        name="Evaluate",
        processor=eval_processor,
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
        code=str(_example_script("evaluate.py")),
    )

    condition = ConditionGreaterThanOrEqualTo(
        left=JsonGet(step_name=evaluate_step.name, property_file=evaluation_report, json_path=f"$.{cfg.threshold_metric}"),
        right=cfg.threshold_min,
    )

    register_processor = ScriptProcessor(
        image_uri=image_uri,
        command=["python3"],
        instance_type=instance_type,
        instance_count=1,
        role=role_arn,
    )
    register_step = ProcessingStep(
        name="RegisterModel",
        processor=register_processor,
        inputs=[
            ProcessingInput(
                source=train_step.properties.ModelArtifacts.S3ModelArtifacts,
                destination="/opt/ml/processing/model",
            )
        ],
        code=str(_example_script("register.py")),
    )

    condition_step = ConditionStep(
        name="CheckMetric",
        conditions=[condition],
        if_steps=[register_step],
        else_steps=[],
    )

    steps = []
    if preprocess_step:
        steps.append(preprocess_step)
    steps.extend([train_step, evaluate_step, condition_step])

    return Pipeline(name=cfg.model_name, parameters=[image_uri, data_uri, output_prefix], steps=steps)


def _example_dir(model_name: str) -> Path:
    candidate = Path(__file__).resolve().parents[2] / "examples" / model_name.replace("_", "-")
    if candidate.exists():
        return candidate
    return Path(__file__).resolve().parents[2] / "examples" / "credit-risk"


def _example_script(name: str) -> Path:
    return _example_dir("credit-risk") / name
