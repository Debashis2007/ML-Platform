# Platform LLD — code mapping

Reference diagram: [`PLATFORM_LLD.drawio`](PLATFORM_LLD.drawio)

## Zones → repository paths

| LLD zone | Components | Code |
|----------|------------|------|
| **GITHUB** | Repo Templates, Training/Deployment repos, GHA pipelines | `templates/model-project/`, `.github/workflows/model-ci.yml`, `model-deploy.yml`, `platform-infra.yml` |
| **DEV** | Build pipeline (Preprocess→Train→Eval→◆→Register), Secrets, ECR, artifact buckets, Step Functions trigger, test endpoint, CloudWatch | `ml_platform/steps/`, `envs/hub-nonprod/`, `modules/evaluation-pipeline/`, `modules/step_functions/`, `modules/secrets/` |
| **PROD** | Prod pipeline, EventBridge approval, deploy trigger, API Gateway, endpoint, Model Monitor, SNS | `envs/hub-prod/`, `envs/deploy-endpoint/`, `modules/api_gateway/`, `modules/monitoring/`, `modules/sns/` |
| **Data Sources** | Data Lake → DEV/PROD preprocess | `modules/storage/` (`data_bucket`), `pipeline.yaml` `data.train_uri` |
| **Governance** | Approve → EventBridge → Lambda → DynamoDB → deploy | `modules/governance/`, `lambdas/capture_approval_event/` |

## Numbered flows (diagram legend)

| Flow | Diagram | Implementation |
|------|---------|----------------|
| 1–2 | Training repo → GHA Training Pipeline | `model-ci.yml` |
| 3–4 | Approver → GHA Deployment Pipeline | Manual/registry approval → `model-deploy.yml` |
| 5–6 | Data Lake → DEV/PROD preprocess | S3 `data_bucket` + pipeline `DataUri` parameter |
| 7–10 | DEV build + trigger + endpoint config + CloudWatch | SageMaker Pipeline SDK + `modules/step_functions/` + `modules/cloudwatch/` |
| 11 | Lead approve manual deployment | Registry `Approved` → governance EventBridge |
| 12–15 | PROD build → deploy → Application | `hub-prod` factory + `deploy-endpoint` (endpoint + API GW) |

## MLflow (diagram block)

Shown in LLD for reference layout. Wave-1 system of record is **SageMaker Model Registry** (`modules/registry/`). MLflow integration is Phase 2.
