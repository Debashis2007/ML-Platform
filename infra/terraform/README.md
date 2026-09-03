# Terraform infrastructure for the ML Platform.

## Layout

```
infra/terraform/
  modules/
    network/              # VPC attachment, SageMaker security group
    storage/              # S3 data + artifacts, ECR
    iam/                  # Pipeline, training, inference, GHA OIDC roles
    registry/             # Model Package Group + RAM share to spokes
    governance/           # EventBridge, Lambda, DynamoDB audit table
    evaluation-pipeline/  # SSM + S3 paths for Train→Evaluate→Register pipeline
    endpoint/             # SageMaker endpoint from approved package (Workflow B)
    monitoring/           # CloudWatch alarms on endpoint
  envs/
    hub-nonprod/          # Pass 1 — factory (apply once per hub non-prod)
    deploy-endpoint/      # Pass 2 — per approval (Workflow B)
```

## Apply order

### Pass 1 — platform factory (`envs/hub-nonprod`)

```bash
cd infra/terraform/envs/hub-nonprod
cp terraform.tfvars.example terraform.tfvars   # edit VPC, buckets, spoke IDs
terraform init
terraform plan
terraform apply
```

Creates shared storage, IAM, registry, governance, and **evaluation-pipeline** platform hooks for `credit-risk`.

Wire GitHub secrets from outputs:

- `MLP_GHA_PIPELINE_ROLE_ARN` ← `gha_pipeline_role_arn`
- `MLP_GHA_DEPLOY_ROLE_ARN` ← `gha_deploy_role_arn`

### Pass 2 — endpoint deploy (`envs/deploy-endpoint`)

Triggered after Senior DS approves a model package (Workflow B):

```bash
cd infra/terraform/envs/deploy-endpoint
terraform apply \
  -var="model_package_arn=arn:aws:sagemaker:..." \
  -var="vpc_id=..." \
  -var="subnet_ids=[...]" \
  -var="inference_role_arn=..."
```

## Evaluation pipeline — two layers

| Layer | Location | Responsibility |
|-------|----------|------------------|
| **Platform (Terraform)** | `modules/evaluation-pipeline/` | SSM config, log group, S3 evaluation prefix |
| **DAG (Python SDK)** | `ml_platform/steps/` | Preprocess, Train, Evaluate, CheckMetric, Register steps |

CI upserts the pipeline after Pass 1:

```bash
python ml_platform/build_pipeline.py \
  --config examples/credit-risk/pipeline.yaml \
  --upsert --role-arn "$PIPELINE_ROLE_ARN"
```

## CloudFormation

Existing `deployment/` CFN templates remain valid for Wave-1. Terraform modules above are the target factory layout and can replace CFN incrementally.
