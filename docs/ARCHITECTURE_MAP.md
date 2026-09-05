# Architecture map

How platform infrastructure and ML pipelines connect across **Central Plane** accounts.

See also: [`CONTROL_PLANE.md`](./CONTROL_PLANE.md) (PPT alignment).

## Two layers

| Layer | Location | When it runs | Responsibility |
|-------|----------|--------------|----------------|
| **Infrastructure** | `infra/terraform/` | Once per Central Plane (`admin-run.yml` / `platform-infra.yml`) | Shared AWS: network, S3, ECR, IAM, registry, Stage Governance, Athena analytics, BU endpoints |
| **ML pipeline** | `ml_platform/`, `pipeline.yaml` | Every model code change (`model-ci.yml`) | SageMaker Pipeline DAG: Preprocess → Train → Evaluate → Condition → Register |

## Central Plane zones (from PPT)

| Zone | AWS components | Repository paths |
|------|----------------|------------------|
| **GitHub Admin-Run** | Orchestrates both planes | `.github/workflows/admin-run.yml`, `model-promote.yml`, `model-ci.yml`, `model-deploy.yml` |
| **Non-Prod Central Plane** | Registry, S3, ECR, Stage Governance (EB→Λ→DDB→Athena), DEV BU endpoints (no API GW) | `envs/hub-nonprod/`, `modules/stage_analytics/`, `modules/bu_endpoints/` |
| **Prod Central Plane** | PROD registry, Stage Governance, promote Lambda, BU endpoints + API GW + WAF | `envs/hub-prod/`, `modules/promote/`, `modules/api_gateway/`, `modules/waf/` |
| **BU serving** | BU1 / BU2 / BU3 / BU4 SageMaker endpoints | `modules/bu_endpoints/`, `envs/deploy-endpoint/` |
| **Governance audit** | DynamoDB + Athena + QuickSight/Power BI | `modules/governance/`, `modules/stage_analytics/` |

## End-to-end flows (PPT legend)

| PPT # | What happens | Code |
|-------|--------------|------|
| 1/9 | Registry ↔ S3 model artifacts | `modules/registry/`, `modules/storage/` |
| 2/10 | Artifacts ↔ ECR images | `modules/storage/` ECR, `model-ci.yml` |
| 3–4 / 11–12 | EventBridge → Lambda → DynamoDB Stage Governance | `modules/governance/`, `lambdas/capture_approval_event/` |
| 5–6 / 13–14 | DynamoDB → Athena → QuickSight / Power BI | `modules/stage_analytics/` |
| 7/15 | Registry approval event | EventBridge rule in governance |
| 8 | ECR → DEV BU SageMaker endpoints (no API GW) | `bu_endpoints` `enable_api_gateway=false` |
| 16 | ECR → Prod API Gateway → BU endpoints | `bu_endpoints` / `deploy-endpoint` with API GW |

## Promotion

```text
Non-Prod Approved → model-promote.yml → promote Lambda → Prod registry
  → admin-run deploy-bu (plane=prod, business_unit=BU1|…)
```

## Apply order

```text
Pass 1a  hub-nonprod
Pass 1b  hub-prod
Promote  Non-Prod → Prod registry
Pass 2   deploy-endpoint / deploy-bu per BU
```
