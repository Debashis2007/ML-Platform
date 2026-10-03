# ML Platform — accounts and roles

Maps **deployment accounts** and **roles** to this repository (`ML-Platform/`).

**Wave-1 decision:** ML Platform deploys into the **Control Plane** (`Control-{env}`) — the same Launchpad control accounts — instead of separate `ML-*` accounts. Terraform roots (`hub-nonprod`, `hub-prod`) are unchanged; only the **target AWS account** changes.

Extended role catalog is maintained outside this repository.

---

## 1. Account inventory

| Account name | Env | AWS account ID | ML-Platform deploys? | Purpose |
|--------------|-----|----------------|----------------------|---------|
| **Control-NonProd** (Launchpad Non-Prod) | nonprod | `848973819860` | **Yes — Wave-1 primary** | ML hub in Control: train, registry, governance, Non-Prod endpoints |
| **Control-Prod** (Launchpad Prod) | prod | `762794225431` | **Yes — before Prod milestone** | ML hub in Control: Prod registry, promote, API GW, endpoints |
| **BU1-{env}** | nonprod / prod | `_TBD_` | No (Wave-1 invoke only) | BU applications consume ML |
| **BU2-{env}** | nonprod / prod | `_TBD_` | No (Wave-1 invoke only) | BU applications consume ML |
| **BU3-{env}** | nonprod / prod | `_TBD_` | No (Wave-1 invoke only) | BU applications consume ML |
| **BU4-{env}** | nonprod / prod | `_TBD_` | No (Wave-1 invoke only) | BU applications consume ML |
| **External data source** | varies | `_TBD_` | No (cross-account read) | Training data for `MLP_TRAIN_DATA_URI` |
| **Shared-network** | — | `_TBD_` | No | TGW, PrivateLink, DNS for Control VPC |
| **Lab** | — | `_TBD_` | No | DS experimentation (optional) |

> **Note:** Long-term target may split ML into dedicated `ML-{env}` accounts. Wave-1 uses Control Plane to avoid vending new accounts; Security must allow SageMaker + endpoints in Control.

### Wave-1 minimum (4-week Non-Prod plan)

| Required now | Can wait |
|--------------|----------|
| **Control-NonProd** VPC/subnets + `mlp-*` IAM roles | Control-Prod |
| GitHub OIDC trust to Control Non-Prod | BU spoke accounts |
| Terraform state bucket in Control Non-Prod | RAM `spoke_account_ids` (optional) |

### Terraform env → account

| Terraform root | Target account | GitHub environment |
|----------------|----------------|-------------------|
| `infra/terraform/envs/hub-nonprod/` | **Control-NonProd** | `nonprod` |
| `infra/terraform/envs/hub-prod/` | **Control-Prod** | `production` |
| `infra/terraform/envs/deploy-endpoint/` | Same Control account as target plane | `nonprod` or `production` |

Wave-1: BU-named endpoints (BU1, BU2, BU3, BU4) are deployed **inside** the Control Plane account.

---

## 2. Human roles (ML Platform)

Okta → IAM Identity Center permission sets.

| ID | Role | Home account(s) | ML Platform activity | Must not |
|----|------|-----------------|----------------------|----------|
| **H-02** | ML Platform / DevOps | **Control-{env}** | Apply `hub-*` / `deploy-endpoint` Terraform; wire GitHub vars; endpoint apply **after** H-10 | Own model quality; ad-hoc IAM in console |
| **H-09** | ML Engineer / Data Scientist | Lab + **Control-NonProd** | `train.py`, `pipeline.yaml`, Git merge, trigger train pipeline | `CreateEndpoint` Prod; `iam:CreateRole` |
| **H-10** | Senior DS (approver) | **Control** registry | Approve/reject model packages in Model Registry | Apply Terraform; widen IAM |
| **H-12** | BU App Engineer | **BU-{name}-{env}** | App that calls ML endpoint / API GW | SageMaker admin |
| **H-01** | Platform / DevOps (Control) | Control | Launchpad + shared Control infra; coordinate ML resource quotas with H-02 | Unscoped SageMaker in Prod without gates |
| **H-03** | Network | Shared-network | VPC, TGW, PrivateLink for Control VPC | — |
| **H-04** | Security / IAM | Audit (all) | Create/review S-* IAM roles, SCPs, boundaries for ML in Control | Day-to-day ML deploy |
| **H-06** | Data Engineer | External data account | Training data paths, S3 policies for `MLP_TRAIN_DATA_URI` | SageMaker admin |

---

## 3. Service (machine) roles — ML Platform

Client creates all IAM roles **in the Control Plane account**; Terraform consumes ARNs. See [`CLIENT_MANAGED_IAM_ROLES.md`](./CLIENT_MANAGED_IAM_ROLES.md).

| Role ID | Example IAM name | Account | Terraform var / secret |
|---------|------------------|---------|------------------------|
| **S-19** | `mlp-sagemaker-pipeline` | Control-{env} | `pipeline_role_arn` |
| **S-18** | `mlp-sagemaker-training` | Control-{env} | `training_role_arn` |
| **S-20** | `mlp-sagemaker-inference` | Control-{env} | `inference_role_arn` |
| **S-21** | `mlp-gha-pipeline` | Control-NonProd | `MLP_GHA_PIPELINE_ROLE_ARN` |
| **S-21** | `mlp-gha-deploy` | Control-{env} | `MLP_GHA_DEPLOY_ROLE_ARN` |
| **S-22** | `mlp-model-monitor` | Control-{env} | `monitoring_role_arn` (optional) |
| — | `mlp-governance-lambda` | Control-{env} | `governance_lambda_role_arn` |
| — | `mlp-governance-export` | Control-{env} | `stage_export_lambda_role_arn` |
| — | `mlp-promote-model` | Control-Prod | `promote_lambda_role_arn` |
| — | `mlp-invoke-endpoint` | Control-Prod | `invoke_lambda_role_arn` |
| — | `mlp-pipeline-trigger` | Control-{env} | `step_functions_role_arn` |
| — | `mlp-apigw-cloudwatch` | Control-Prod | `apigateway_cloudwatch_role_arn` |
| **S-17** | `bu-app-runtime` | BU-{name}-{env} | BU team — cross-account invoke |

---

## 4. Cross-account wiring

| From | To | Mechanism |
|------|-----|-----------|
| Control-NonProd | Control-Prod | Promote Lambda + `ml-lifecycle.yml` promote job |
| Control-{env} | BU-{name}-{env} | RAM share (optional); app invoke endpoint / API GW |
| External data | Control-NonProd | S3 read for training data |
| BU-{name}-{env} | Control-{env} | `bu-app-runtime` → InvokeEndpoint or API GW |

---

## 5. Provisioning checklist

### Account / platform team

- [ ] Confirm **Control-NonProd** (`848973819860`) for ML Wave-1 deploy
- [ ] Provide VPC ID, private subnet IDs in Control Non-Prod
- [ ] Security approves SageMaker pipelines, endpoints, ECR in Control account
- [ ] Record account IDs in `terraform.tfvars` (Prod: `762794225431` before Prod milestone)

### Security / IAM (H-04)

- [ ] Create all `mlp-*` roles in **Control** accounts (see [`CLIENT_MANAGED_IAM_ROLES.md`](./CLIENT_MANAGED_IAM_ROLES.md))
- [ ] GitHub OIDC provider + `mlp-gha-pipeline` / `mlp-gha-deploy` in Control
- [ ] BU `bu-app-runtime` per consuming BU (cross-account invoke)

### ML Platform DevOps (H-02)

- [ ] Bootstrap Terraform state in Control-NonProd
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
