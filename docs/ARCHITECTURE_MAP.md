# Architecture map

How platform infrastructure and ML pipelines connect across environments.

## Two layers

| Layer | Location | When it runs | Responsibility |
|-------|----------|--------------|----------------|
| **Infrastructure** | `infra/terraform/` | Once per environment (`platform-infra.yml` or manual apply) | Shared AWS services: networking, S3, ECR, IAM, registry, governance, SSM, Step Functions, monitoring |
| **ML pipeline** | `ml_platform/`, `pipeline.yaml` | Every model code change (`model-ci.yml`) | SageMaker Pipeline DAG: Preprocess → Train → Evaluate → Condition → Register |

Infrastructure creates the landing zone. Application code defines what runs inside it.

## Environment zones

| Zone | AWS components | Repository paths |
|------|----------------|------------------|
| **GitHub** | — | `templates/model-project/`, `.github/workflows/model-ci.yml`, `model-deploy.yml`, `platform-infra.yml` |
| **DEV** | Build pipeline, Secrets Manager, ECR, dev/model artifact buckets, Step Functions trigger, optional test endpoint, CloudWatch | `ml_platform/steps/`, `envs/hub-nonprod/`, `modules/evaluation-pipeline/`, `modules/step_functions/`, `modules/secrets/` |
| **PROD** | Prod pipeline, deploy trigger, API Gateway, SageMaker endpoint, Model Monitor, SNS, CloudWatch | `envs/hub-prod/`, `envs/deploy-endpoint/`, `modules/api_gateway/`, `modules/monitoring/`, `modules/sns/` |
| **Data sources** | Data Lake, external feeds | `modules/storage/`, `pipeline.yaml` data URIs |
| **Governance** | EventBridge, Lambda, DynamoDB, SSM | `modules/governance/`, `lambdas/capture_approval_event/` |

## End-to-end flows

| Step | What happens | Code |
|------|--------------|------|
| **1–2** | Push to training repo → GitHub Actions builds image, upserts pipeline, starts execution | `model-ci.yml`, `ml_platform/build_pipeline.py`, `ml_platform/run_pipeline.py` |
| **3–4** | Approver triggers deployment workflow after model review | `model-deploy.yml` |
| **5–6** | Data Lake feeds DEV preprocess; promoted data feeds PROD preprocess | S3 buckets (`modules/storage/`), pipeline `DataUri` parameter |
| **7–10** | Register → monitoring → trigger → endpoint config/endpoint pipelines → CloudWatch | `ml_platform/steps/register.py`, `modules/step_functions/`, `modules/cloudwatch/`, optional dev test endpoint |
| **11** | Lead approves manual deployment; registry status becomes Approved | SageMaker Model Registry, `modules/governance/`, `lambdas/capture_approval_event/` |
| **12–15** | PROD pipeline → deploy trigger → endpoint materialization → application traffic | `envs/hub-prod/`, `envs/deploy-endpoint/`, `modules/endpoint/`, `modules/api_gateway/` |

## Infra ↔ pipeline contract

| Infrastructure provides | Pipeline uses |
|---------------------------|---------------|
| S3 data and artifacts buckets | Training data URI, model artifacts, evaluation output |
| ECR repository | Container image for Train/Evaluate steps |
| IAM pipeline and training roles | Pipeline upsert and step execution |
| Model Package Group | Register step destination |
| SSM parameters (thresholds, instance types, S3 prefixes) | Platform defaults per model |
| Governance EventBridge + Lambda | Writes deploy ARN to SSM; signals Workflow B |
| Endpoint + API Gateway (Pass 2) | Serves approved package without re-running training |

## Apply order

```text
Pass 1a  hub-nonprod   DEV factory (storage, IAM, registry, governance, pipeline hooks)
Pass 1b  hub-prod      PROD factory (prod data, SNS, deploy trigger, prod pipeline config)
Pass 2   deploy-endpoint   Per approved model (endpoint, API Gateway, monitoring)
```

## Registry and MLflow

Wave-1 system of record is **SageMaker Model Registry** (`modules/registry/`). MLflow experiment tracking and a parallel registry store are planned for Phase 2.
