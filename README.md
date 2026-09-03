# ML-Platform

Multi-account **Machine Learning Platform** on AWS — SageMaker pipeline factory, GitHub Actions CI/CD, hub/spoke accounts, and SageMaker Model Registry as system of record.

## Repository layout

| Path | Purpose |
|------|---------|
| `infra/terraform/` | **Terraform modules** — DEV/PROD factory, evaluation-pipeline, endpoint deploy |
| `docs/` | Architecture mapping (`ARCHITECTURE_MAP.md`) |
| `deployment/` | CloudFormation templates — hub/spoke, KMS, governance |
| `ml_platform/` | Pipeline builder + evaluation step modules |
| `examples/credit-risk/` | Lighthouse model |
| `templates/model-project/` | GitHub template for new model repos |
| `lambdas/` | Governance capture + endpoint invoke |
| `.github/workflows/` | Workflow A (CI), B (deploy), C (platform-infra) |
| `source/` | Reference notebooks for validation |

## Infrastructure

**Terraform** (`infra/terraform/`) — modular factory:

| Module | Purpose |
|--------|---------|
| `network` | SageMaker security group in existing VPC |
| `storage` | S3 data/artifacts buckets, ECR |
| `iam` | Pipeline, training, inference, GHA OIDC roles |
| `registry` | Model Package Group + RAM share |
| `governance` | EventBridge → Lambda → DynamoDB |
| `evaluation-pipeline` | SSM + S3 paths for Train→Evaluate→Register |
| `endpoint` | Deploy approved package (Workflow B) |
| `monitoring` | CloudWatch alarms + SNS |
| `step_functions` | Pipeline / deploy trigger (LLD flow 7) |
| `api_gateway` | HTTP API for `/invocations` (LLD flow 14) |
| `sns` | Alert topic for prod monitoring |
| `secrets` | Secrets Manager placeholders |
| `cloudwatch` | Pipeline + endpoint dashboards |

```bash
# DEV zone (Pass 1a)
cd infra/terraform/envs/hub-nonprod
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply

# PROD zone (Pass 1b)
cd infra/terraform/envs/hub-prod
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply
```

**CloudFormation** (`deployment/`) — hub/spoke SageMaker domains, model sharing, governance, and KMS cross-account policies.

See `infra/terraform/README.md` for Pass 1 (factory) vs Pass 2 (endpoint) apply order.

## Quick start — pipeline factory

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -c "from ml_platform.config import PipelineConfig; print(PipelineConfig.load('examples/credit-risk/pipeline.yaml'))"
python ml_platform/build_pipeline.py --config examples/credit-risk/pipeline.yaml
```

## Model lifecycle

```
GitHub push → Workflow A → ECR → SageMaker Pipeline
  → Preprocess → Train → Evaluate → Condition → Register (Pending)
  → Senior DS Approve → EventBridge → Lambda → DynamoDB
  → Workflow B → terraform apply (endpoint module) → Model Monitor
```

## Serving contract

```json
POST /invocations
Request:  { "features": [ ... ] }
Response: { "prediction": <value>, "score": <0..1>, "model_version": "credit-risk:3" }
```

## License

MIT-0
