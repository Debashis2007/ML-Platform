# Central Plane — architecture map

Maps the **ML Platform** deployment onto **Control Plane** accounts (control plane architecture deck).

## Accounts (Wave-1)

**ML Platform deploys into `Control-{env}`** (Launchpad Control Plane) — not separate ML-only accounts for Wave-1.

Account inventory, human roles, service roles, and checklist: [`ACCOUNTS_AND_ROLES.md`](./ACCOUNTS_AND_ROLES.md).

| AWS account | Terraform root | Role |
|----------------|----------------|------|
| **Control-NonProd** (`848973819860`) | `infra/terraform/envs/hub-nonprod/` | Registry (DEV/TEST), S3, ECR, Stage Governance, DEV BU endpoints **without** API Gateway |
| **Control-Prod** (`762794225431`) | `infra/terraform/envs/hub-prod/` | PROD registry, promote Lambda, BU endpoints **with** API Gateway + WAF |
| **Same Control account** (per target plane) | `infra/terraform/envs/deploy-endpoint/` | Single BU endpoint deploy |
| **BU-{name}-{env}** (Wave-1: invoke only) | — | Apps consume ML; RAM via `spoke_account_ids` when BU accounts exist |

Orchestration: `.github/workflows/ml-lifecycle.yml` (train · promote · deploy) and `.github/workflows/platform-infra.yml` (CI→ECR→CD · deploy-bu).

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
  → governance event / ml-lifecycle.yml (promote job)
  → promote_model_package Lambda (Control Prod account)
  → Prod Model Package Group (Approved)
  → ml-lifecycle.yml (deploy job) or platform-infra deploy-bu
```

## Feature Store

Phase 2 (ASM-ML-02). Wave-1 uses optional `steps.features` in `pipeline.yaml` only.

## Apply order

```text
Pass 1a  hub-nonprod   (+ stage_analytics, optional bu_endpoints)  → Control-NonProd
Pass 1b  hub-prod      (+ stage_analytics, promote, optional bu_endpoints)  → Control-Prod
Pass 2   deploy-endpoint / platform-infra deploy-bu
Promote  ml-lifecycle.yml (promote job) after Non-Prod approval
```
