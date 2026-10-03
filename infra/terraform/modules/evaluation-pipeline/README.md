# Evaluation pipeline platform module

Provisions **platform resources** for the Train → Evaluate → Condition → Register SageMaker pipeline. The pipeline DAG itself is built by `ml_platform/build_pipeline.py` (SDK upsert from CI).

## Resources

| Resource | Purpose |
|----------|---------|
| CloudWatch log group | Pipeline execution logs |
| SSM parameters | Metric gate, instance types, role ARNs, S3 prefixes |
| S3 prefix markers | Evaluation (and optional preprocess) output paths |

## Step mapping

| Pipeline step (SDK) | This module |
|---------------------|-------------|
| Preprocess | `features_enabled` + `processed/` S3 prefix |
| Train | `train_instance_type`, `training_role_arn` SSM |
| Evaluate | `evaluate_instance_type`, `evaluation_output_prefix` |
| CheckMetric | `metric_name`, `metric_threshold` SSM |
| RegisterModel | `model_package_group_name` SSM |

## Usage

```hcl
module "credit_risk_pipeline" {
  source = "../modules/evaluation-pipeline"

  name_prefix              = "mlp-hub-nonprod"
  model_name               = "credit-risk"
  pipeline_role_arn        = module.iam.pipeline_role_arn
  training_role_arn        = module.iam.training_role_arn
  artifacts_bucket_name    = module.storage.artifacts_bucket_name
  data_bucket_name         = module.storage.data_bucket_name
  model_package_group_name = module.registry.model_package_group_name
  metric_name              = "auc"
  metric_threshold         = 0.75
}
```

After apply, run Workflow A:

```bash
python ml_platform/build_pipeline.py \
  --config examples/credit-risk/model.yaml \
  --upsert --role-arn $(terraform output -raw pipeline_role_arn)
```
