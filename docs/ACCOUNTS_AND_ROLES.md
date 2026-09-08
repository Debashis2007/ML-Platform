# ML Central Plane — accounts and roles

Maps **ML Central Plane accounts** and **roles** to this repository (`ML-Platform/`).

**Scope:** ML Central Plane (`ML-{env}`), BU consumers, and optional cross-account data/network.  
Extended role catalog is maintained outside this repository.

---

## 1. Account inventory

Fill **AWS account ID** when CRBG / cloud team vends accounts.

| Account name | Env | AWS account ID | ML-Platform deploys? | Purpose |
|--------------|-----|----------------|----------------------|---------|
| **ML-NonProd** | nonprod | `_TBD_` | **Yes — Wave-1 primary** | ML Central Plane: train, registry, Non-Prod endpoints |
| **ML-Prod** | prod | `_TBD_` | **Yes — before Prod** | ML Central Plane: Prod registry, promote, API GW, endpoints |
| **BU1-{env}** | nonprod / prod | `_TBD_` | No (Wave-1 invoke only) | BU applications consume ML |
| **BU2-{env}** | nonprod / prod | `_TBD_` | No (Wave-1 invoke only) | BU applications consume ML |
| **BU3-{env}** | nonprod / prod | `_TBD_` | No (Wave-1 invoke only) | BU applications consume ML |
| **BU4-{env}** | nonprod / prod | `_TBD_` | No (Wave-1 invoke only) | BU applications consume ML |
| **External data source** | varies | `_TBD_` | No (cross-account read) | Training data for `MLP_TRAIN_DATA_URI` (S3 or lake) |
| **Shared-network** | — | `_TBD_` | No | TGW, PrivateLink, DNS for ML VPC |
| **Lab** | — | `_TBD_` | No | DS experimentation (optional) |

### Wave-1 minimum (4-week Non-Prod plan)

| Required now | Can wait |
|--------------|----------|
| **ML-NonProd** account ID + VPC/subnets | ML-Prod |
| Client IAM roles in ML Non-Prod | BU spoke accounts |
| GitHub OIDC trust to ML Non-Prod | RAM `spoke_account_ids` (optional) |

### Terraform env → account

| Terraform root | Target account | GitHub environment |
|----------------|----------------|-------------------|
| `infra/terraform/envs/hub-nonprod/` | **ML-NonProd** | `nonprod` |
| `infra/terraform/envs/hub-prod/` | **ML-Prod** | `production` |
| `infra/terraform/envs/deploy-endpoint/` | Same ML hub as target plane | `nonprod` or `production` |

Wave-1: BU-named endpoints (BU1, BU2, BU3, BU4) are deployed **inside** the ML Central Plane account.

---

## 2. Human roles (ML Platform)

Okta → IAM Identity Center permission sets.

| ID | Role | Home account(s) | ML Platform activity | Must not |
|----|------|-----------------|----------------------|----------|
| **H-02** | ML Platform / DevOps | **ML-{env}** | Apply `hub-*` / `deploy-endpoint` Terraform; wire GitHub vars; endpoint apply **after** H-10 | Own model quality; ad-hoc IAM in console |
| **H-09** | ML Engineer / Data Scientist | Lab + **ML-NonProd** | `train.py`, `pipeline.yaml`, Git merge, trigger train pipeline | `CreateEndpoint` Prod; `iam:CreateRole` |
| **H-10** | Senior DS (approver) | **ML** registry | Approve/reject model packages in Model Registry | Apply Terraform; widen IAM |
| **H-12** | BU App Engineer | **BU-{name}-{env}** | App that calls ML endpoint / API GW | SageMaker admin |
| **H-03** | Network | Shared-network | VPC, TGW, PrivateLink for ML hub | — |
| **H-04** | Security / IAM | Audit (all) | Create/review S-* IAM roles, SCPs, boundaries | Day-to-day ML deploy |
| **H-06** | Data Engineer | External data account | Training data paths, S3 policies for `MLP_TRAIN_DATA_URI` | SageMaker admin |

---

## 3. Service (machine) roles — ML Platform

Client creates all IAM roles; Terraform consumes ARNs. See [`CLIENT_MANAGED_IAM_ROLES.md`](./CLIENT_MANAGED_IAM_ROLES.md).

| Role ID | Example IAM name | Account | Terraform var / secret |
|---------|------------------|---------|------------------------|
| **S-19** | `mlp-sagemaker-pipeline` | ML-{env} | `pipeline_role_arn` |
| **S-18** | `mlp-sagemaker-training` | ML-{env} | `training_role_arn` |
| **S-20** | `mlp-sagemaker-inference` | ML-{env} | `inference_role_arn` |
| **S-21** | `mlp-gha-pipeline` | ML-NonProd | `MLP_GHA_PIPELINE_ROLE_ARN` |
| **S-21** | `mlp-gha-deploy` | ML-{env} | `MLP_GHA_DEPLOY_ROLE_ARN` |
| **S-22** | `mlp-model-monitor` | ML-{env} | `monitoring_role_arn` (optional) |
| — | `mlp-governance-lambda` | ML-{env} | `governance_lambda_role_arn` |
| — | `mlp-governance-export` | ML-{env} | `stage_export_lambda_role_arn` |
| — | `mlp-promote-model` | ML-Prod | `promote_lambda_role_arn` |
| — | `mlp-invoke-endpoint` | ML-Prod | `invoke_lambda_role_arn` |
| — | `mlp-pipeline-trigger` | ML-{env} | `step_functions_role_arn` |
| — | `mlp-apigw-cloudwatch` | ML-Prod | `apigateway_cloudwatch_role_arn` |
| **S-17** | `bu-app-runtime` | BU-{name}-{env} | BU team — cross-account invoke |

---

## 4. Cross-account wiring

| From | To | Mechanism |
|------|-----|-----------|
| ML-NonProd | ML-Prod | Promote Lambda + `ml-lifecycle.yml` promote job |
| ML-{env} | BU-{name}-{env} | RAM share (optional); app invoke endpoint / API GW |
| External data | ML-NonProd | S3 read for training data |
| BU-{name}-{env} | ML-{env} | `bu-app-runtime` → InvokeEndpoint or API GW |

---

## 5. Provisioning checklist

### Account team

- [ ] Vend **ML-NonProd** AWS account
- [ ] Vend **ML-Prod** (before Prod milestone)
- [ ] Provide VPC ID, private subnet IDs
- [ ] Record account IDs in `terraform.tfvars` and Excel service map

### Security / IAM (H-04)

- [ ] Create all `mlp-*` roles in correct ML accounts (see [`CLIENT_MANAGED_IAM_ROLES.md`](./CLIENT_MANAGED_IAM_ROLES.md))
- [ ] GitHub OIDC provider + `mlp-gha-pipeline` / `mlp-gha-deploy`
- [ ] BU `bu-app-runtime` per consuming BU (cross-account invoke)

### ML Platform DevOps (H-02)

- [ ] Bootstrap Terraform state in ML-NonProd
- [ ] `hub-nonprod` apply
- [ ] Wire GitHub secrets/vars
- [ ] E2E: train → approve → deploy → invoke

---

## 6. Related docs

| Doc | Content |
|-----|---------|
| [`CONTROL_PLANE.md`](./CONTROL_PLANE.md) | PPT ↔ Terraform |
| [`CLIENT_MANAGED_IAM_ROLES.md`](./CLIENT_MANAGED_IAM_ROLES.md) | IAM permissions |
| [`ARCHITECTURE_MAP.md`](./ARCHITECTURE_MAP.md) | Component flows |
| `ML_Platform_Central_Plane_BU_Service_Map.xlsx` | Services + roles spreadsheet |
