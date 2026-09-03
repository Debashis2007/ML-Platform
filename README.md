# ML-Platform

Multi-account **Machine Learning Platform** on AWS — SageMaker pipeline factory, GitHub Actions CI/CD, hub/spoke accounts, and SageMaker Model Registry as system of record.

## How infrastructure and ML pipelines work together

The platform splits responsibilities into two layers that must be applied in order:

| Layer | Code | Runs when | What it creates |
|-------|------|-----------|-----------------|
| **Platform (infra)** | `infra/terraform/` | Once per environment (manual or `platform-infra.yml`) | Shared AWS resources: S3 buckets, ECR, IAM roles, Model Registry, governance hooks, SSM parameters, Step Functions |
| **Pipeline (application)** | `ml_platform/`, `examples/*/pipeline.yaml` | On every model code push (`model-ci.yml`) | SageMaker Pipeline definition and execution: Preprocess → Train → Evaluate → Condition → Register |

Terraform does **not** define the training DAG step-by-step. It provisions the **hooks and shared services** the pipeline needs. Python (`ml_platform/build_pipeline.py`) reads `pipeline.yaml` and upserts the SageMaker Pipeline that runs on those resources.

### Bootstrap (apply once)

```text
Pass 1a — hub-nonprod (DEV)
  Terraform → buckets, ECR, IAM, registry, governance, evaluation-pipeline SSM paths

Pass 1b — hub-prod (PROD)
  Terraform → prod data bucket, prod pipeline config, SNS, deploy trigger

Pass 2 — deploy-endpoint (per approved model)
  Terraform → SageMaker endpoint, API Gateway, monitoring
```

After Pass 1a, wire GitHub **secrets/vars** from Terraform outputs (OIDC roles, pipeline role, data URIs, bucket prefixes). CI cannot run until this bootstrap completes.

### Training flow — Workflow A (`model-ci.yml`)

Triggered on push to `main` when model or pipeline code changes.

```text
GitHub push
  → validate pipeline.yaml
  → build Docker image → push to ECR          (uses infra: ECR repo from storage module)
  → build_pipeline.py --upsert                (registers SageMaker Pipeline in AWS)
  → run_pipeline.py                           (starts execution with ImageUri, DataUri, OutputPrefix)
       ↓
SageMaker Pipeline (ml_platform/steps/)
  Preprocess → Train → Evaluate → Condition → Register
       ↓
Model Package in PendingManualApproval        (uses infra: registry module + S3 artifacts bucket)
```

Pipeline parameters (`DataUri`, `OutputPrefix`, `ImageUri`) come from GitHub vars and land in S3 paths that Terraform created under `modules/evaluation-pipeline/` and `modules/storage/`.

### Approval and deploy — governance + Workflow B

When a Senior DS approves the model package in SageMaker Model Registry:

```text
Registry status → Approved
  → EventBridge (governance module)
  → Lambda (capture_approval_event)
       → DynamoDB audit record
       → SSM /deploy/model_package_arn
       → EventBridge "Model Approved" event
  → model-deploy.yml (manual or repository_dispatch)
  → terraform apply in deploy-endpoint/
       → SageMaker endpoint from approved package
       → API Gateway POST /invocations
       → CloudWatch alarms → SNS
```

Workflow B reads the approved `model_package_arn` from workflow input or the SSM parameter the governance Lambda wrote. Terraform then materializes the serving stack; the ML pipeline code is not redeployed at this stage.

### Contract between layers

| Infra provides | Pipeline consumes |
|----------------|-------------------|
| S3 data + artifacts buckets | `DataUri`, training output, evaluation reports |
| ECR repository | Training container `ImageUri` |
| IAM pipeline / training roles | Pipeline upsert and step execution |
| Model Package Group | Register step target |
| SSM parameters (metric threshold, instance types, S3 prefixes) | Platform-wide defaults per model (optional; `pipeline.yaml` is source of truth for DAG) |
| Governance EventBridge + Lambda | Triggers deploy workflow after human approval |
| Endpoint + API Gateway modules | Serve approved model package (no pipeline rerun) |

Each new model repo copies `templates/model-project/`, adds a `pipeline.yaml`, and reuses the same infra factory. Only Pass 2 (`deploy-endpoint`) is repeated per approved model version.

See `docs/ARCHITECTURE_MAP.md` for zone-to-path mapping and `infra/terraform/README.md` for module-level apply order.

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
| `step_functions` | Pipeline and deploy trigger state machines |
| `api_gateway` | HTTP API for `/invocations` |
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

See `infra/terraform/README.md` for Pass 1 vs Pass 2 apply order.

## Quick start — pipeline factory

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -c "from ml_platform.config import PipelineConfig; print(PipelineConfig.load('examples/credit-risk/pipeline.yaml'))"
python ml_platform/build_pipeline.py --config examples/credit-risk/pipeline.yaml
```

After infra bootstrap, CI runs the same upsert + start sequence automatically via `model-ci.yml`.

## Serving contract

```json
POST /invocations
Request:  { "features": [ ... ] }
Response: { "prediction": <value>, "score": <0..1>, "model_version": "credit-risk:3" }
```

## License

MIT-0
