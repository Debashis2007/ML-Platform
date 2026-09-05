# Central Plane — architecture map

Maps the **ML Platform Central Plane** PPT (`ML_Platform_Central_Plane.pptx`) onto this repository.

## Accounts (PPT slide 1)

| Plane | Terraform root | Role |
|-------|----------------|------|
| **NONPROD Central Plane** | `infra/terraform/envs/hub-nonprod/` | Registry (DEV/TEST), S3 artifacts, ECR, Stage Governance, Athena/QS exports, DEV BU endpoints **without** API Gateway |
| **PROD Central Plane** | `infra/terraform/envs/hub-prod/` | PROD registry, Stage Governance, promote Lambda, BU endpoints **with** API Gateway |
| **Per-BU deploy workspace** | `infra/terraform/envs/deploy-endpoint/` | Single BU endpoint; `enable_api_gateway=false` in Non-Prod, `true` in Prod |

Orchestration: `.github/workflows/admin-run.yml` (Admin-Run).

## Stage Governance (flows 3–6 / 11–14)

```text
EventBridge (Model Package State Change)
  → Lambda capture_approval_event → DynamoDB Stage Governance
  → scheduled export Lambda → S3 (Athena spill bucket)
  → Athena workgroup + Glue table stage_governance
  → QuickSight (optional) or Power BI via Athena JDBC
```

Module: `infra/terraform/modules/stage_analytics/`

## Serving asymmetry (flows 8 / 16)

| Environment | Front door | Module flag |
|-------------|------------|-------------|
| Non-Prod DEV | Direct SageMaker invoke (BU1/BU2/BU3/BU4) | `bu_endpoints.enable_api_gateway = false` |
| Prod | API Gateway (+ WAF) → Lambda → endpoint | `enable_api_gateway = true` |

Business units default map: BU1, BU2, BU3, BU4.

## Promotion path (PPT)

```text
Non-Prod registry Approved
  → governance event / model-promote.yml
  → promote_model_package Lambda (Prod account)
  → Prod Model Package Group (Approved)
  → admin-run deploy-bu (plane=prod)
```

## Feature Store

Phase 2 (ASM-ML-02). Wave-1 uses optional `steps.features` in `pipeline.yaml` only.

## Apply order

```text
Pass 1a  hub-nonprod   (+ stage_analytics, optional bu_endpoints)
Pass 1b  hub-prod      (+ stage_analytics, promote, optional bu_endpoints)
Pass 2   deploy-endpoint / admin-run deploy-bu
Promote  model-promote.yml after Non-Prod approval
```
