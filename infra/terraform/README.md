# Terraform infrastructure for the ML Platform.

Reference: [`docs/ARCHITECTURE_MAP.md`](../../docs/ARCHITECTURE_MAP.md).

## Layout

```
infra/terraform/
  modules/
    network/              # VPC attachment, SageMaker security group
    storage/              # S3 data, dev/prod artifacts, prod data, ECR
    iam/                  # README only — roles are client-managed (see docs/CLIENT_MANAGED_IAM_ROLES.md)
    registry/             # Model Package Group + RAM share to spokes
    governance/           # EventBridge, Lambda, DynamoDB (Lambda role ARN input)
    secrets/              # Secrets Manager placeholders (DEV zone)
    evaluation-pipeline/  # SSM + S3 paths for Train→Evaluate→Register pipeline
    step_functions/       # Pipeline and deploy trigger state machines (SFN role ARN input)
    sns/                  # Alert topic for Model Monitor alarms
    api_gateway/          # REST API → Lambda → SageMaker endpoint (+ WAF)
    cloudwatch/           # Pipeline + endpoint dashboards
    endpoint/             # SageMaker endpoint from approved package (Workflow B)
    monitoring/           # CloudWatch alarms on endpoint
  envs/
    hub-nonprod/          # DEV zone factory (Pass 1)
    hub-prod/             # PROD zone factory (pipelines, SNS, deploy trigger)
    deploy-endpoint/      # Pass 2 — endpoint + API GW + monitoring (Workflow B)
```

## IAM (client-managed)

Terraform **does not create IAM roles**. The client creates roles manually and passes ARNs via `terraform.tfvars` / `TF_VAR_*`. Full inventory: [`docs/CLIENT_MANAGED_IAM_ROLES.md`](../../docs/CLIENT_MANAGED_IAM_ROLES.md).

## Apply order

### Pass 1a — DEV factory (`envs/hub-nonprod`)

```bash
cd infra/terraform/envs/hub-nonprod
cp terraform.tfvars.example terraform.tfvars   # edit VPC, buckets, spoke IDs, role ARNs
terraform init
terraform plan
terraform apply
```

Creates shared storage, registry, governance, evaluation pipeline hooks, Step Functions trigger, and optional DEV BU endpoints. **Requires client role ARNs in tfvars.**

Wire GitHub secrets/vars (roles created by client, not Terraform outputs):

- `MLP_GHA_PIPELINE_ROLE_ARN` / `MLP_GHA_DEPLOY_ROLE_ARN` — client OIDC roles
- `MLP_INFERENCE_ROLE_ARN`, `MLP_INVOKE_LAMBDA_ROLE_ARN`, `MLP_APIGW_CLOUDWATCH_ROLE_ARN`
- `MLP_PIPELINE_ROLE_ARN`, `MLP_TRAIN_DATA_URI`, `MLP_PIPELINE_OUTPUT_PREFIX`

### Pass 1b — PROD factory (`envs/hub-prod`)

```bash
cd infra/terraform/envs/hub-prod
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply
```

Creates prod data bucket, prod evaluation pipeline config, SNS alerts, deploy trigger Step Function, and CloudWatch dashboards.

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

Or via GitHub Actions `model-deploy.yml` (reads SSM `/mlp-hub-nonprod/deploy/model_package_arn` written by governance Lambda on approval).

## Evaluation pipeline — two layers

| Layer | Location | Responsibility |
|-------|----------|------------------|
| **Platform (Terraform)** | `modules/evaluation-pipeline/` | SSM config, log group, S3 evaluation prefix |
| **DAG (Python SDK)** | `ml_platform/steps/` | Preprocess, Train, Evaluate, CheckMetric, Register steps |

CI upserts and starts the pipeline (Workflow A):

```bash
python ml_platform/build_pipeline.py \
  --config examples/credit-risk/pipeline.yaml \
  --upsert --role-arn "$PIPELINE_ROLE_ARN"

python ml_platform/run_pipeline.py \
  --pipeline-name credit-risk \
  --role-arn "$PIPELINE_ROLE_ARN" \
  --image-uri "$ECR_IMAGE" \
  --data-uri "$DATA_URI" \
  --output-prefix "$OUTPUT_PREFIX"
```

## CloudFormation

The `deployment/` CloudFormation templates can be used alongside or instead of Terraform for hub/spoke and KMS setup.
