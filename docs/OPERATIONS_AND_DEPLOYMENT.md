# Operations & deployment guide

How ML-Platform moves models from Non-Prod to Prod, how GitHub Actions runners drive AWS, which pipelines exist, what to run first, and how to maintain the codebase.

Related: [`ARCHITECTURE_MAP.md`](./ARCHITECTURE_MAP.md) · [`CONTROL_PLANE.md`](./CONTROL_PLANE.md) · [`PRODUCTION_VERIFICATION.md`](./PRODUCTION_VERIFICATION.md) · [`CLIENT_MANAGED_IAM_ROLES.md`](./CLIENT_MANAGED_IAM_ROLES.md)

---

## 1. Big picture

**IAM note:** The client creates all AWS IAM roles. Terraform only accepts role ARNs (see [`CLIENT_MANAGED_IAM_ROLES.md`](./CLIENT_MANAGED_IAM_ROLES.md)).

Two layers, one promotion path:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│  GitHub (this repo)                                                     │
│  Actions runners (ubuntu-latest) → OIDC → AWS IAM roles                 │
│                                                                         │
│  Workflows: ml-lifecycle · platform-infra                               │
└───────────────┬───────────────────────────────┬─────────────────────────┘
                │                               │
                ▼                               ▼
┌───────────────────────────┐     ┌───────────────────────────────────────┐
│  NONPROD Control Plane  │     │  PROD Control Plane                   │
│  hub-nonprod Terraform    │     │  hub-prod Terraform                   │
│  · S3 / ECR / IAM         │     │  · S3 / ECR / IAM                     │
│  · Model Registry (DEV)   │────►│  · Model Registry (PROD) via promote  │
│  · Stage Governance       │     │  · Stage Governance                   │
│  · BU endpoints (no APIGW)│     │  · BU endpoints + API GW + WAF        │
└───────────────────────────┘     └───────────────────────────────────────┘
                │                               │
                ▼                               ▼
        SageMaker Pipeline              Serving: BU1 / BU2 / BU3 / BU4
        (train → register)              API Gateway → Lambda → endpoint
```

| Layer | What it is | Who runs it |
|-------|------------|-------------|
| **Platform infra** | Shared AWS (buckets, registry, governance, endpoints) | Terraform via GitHub Actions |
| **ML pipeline** | Train/eval/register DAG per model | SageMaker Pipeline started by `ml-lifecycle.yml` |
| **Serving** | Real-time inference | Endpoint (+ API GW in Prod) from approved package |

Terraform does **not** define training steps. Python (`ml_platform/`) builds the SageMaker Pipeline that uses resources Terraform created.

---

## 2. Environments and promotion path

### Environments

| Environment | AWS account / plane | Terraform root | GitHub Environment |
|-------------|---------------------|----------------|--------------------|
| **Non-Prod** | Control-NonProd (`848973819860`) | `infra/terraform/envs/hub-nonprod/` | `nonprod` |
| **Prod** | Control-Prod (`762794225431`) | `infra/terraform/envs/hub-prod/` | `production` |
| **Per-BU serve** | Same plane as target | `infra/terraform/envs/deploy-endpoint/` | `nonprod` or `production` |

### Serving difference (by design)

| Plane | How apps call the model |
|-------|-------------------------|
| Non-Prod | Direct `sagemaker:InvokeEndpoint` (no API Gateway) |
| Prod | `API Gateway` (+ WAF, IAM auth) → Lambda → endpoint |

Business units: **BU1**, **BU2**, **BU3**, **BU4**.

### Env → env flow (happy path)

```text
1. Bootstrap Non-Prod hub          (Terraform hub-nonprod)
2. Bootstrap Prod hub              (Terraform hub-prod)
3. Train & register in Non-Prod    (ml-lifecycle train → SageMaker Pipeline)
4. Human approval in Model Registry (PendingManualApproval → Approved)
5. Promote package Non-Prod → Prod (ml-lifecycle promote job)
6. Deploy BU endpoint in Prod      (ml-lifecycle deploy job or platform-infra deploy-bu)
7. Invoke via API Gateway          (POST /invocations)
```

Lifecycle stages on packages (Model Registry staging construct):

| Stage | When |
|-------|------|
| `Development` / `PendingApproval` | After Non-Prod register |
| `Production` / `Approved` | After promote into Prod registry |

---

## 3. GitHub Actions and runners

### How a run works

```text
Event (push / PR / workflow_dispatch / repository_dispatch)
  → GitHub queues a job
  → Job lands on a runner: runs-on: ubuntu-latest
       (GitHub-hosted VM; fresh each job)
  → Steps: checkout → (optional) Python/Terraform setup
  → aws-actions/configure-aws-credentials (OIDC)
       GitHub token → AssumeRoleWithWebIdentity
       → MLP_GHA_PIPELINE_ROLE_ARN  (train / ECR / pipeline)
       → MLP_GHA_DEPLOY_ROLE_ARN    (Terraform / promote / deploy)
  → Job talks to AWS APIs (SageMaker, ECR, Terraform providers, Lambda)
  → Job ends; runner is discarded (no sticky state on the VM)
```

There is **no custom self-hosted runner** in Wave-1. Everything uses **GitHub-hosted** `ubuntu-latest`. AWS access is **keyless OIDC** (no long-lived access keys in secrets for assume-role).

### Required GitHub setup

| Type | Examples |
|------|----------|
| **Environments** | `nonprod`, `production` (protection rules / reviewers for Prod) |
| **Secrets** | `MLP_GHA_PIPELINE_ROLE_ARN`, `MLP_GHA_DEPLOY_ROLE_ARN` |
| **Variables** | `AWS_REGION`, `MLP_TF_STATE_BUCKET`, `MLP_TF_STATE_LOCK_TABLE`, `MLP_ECR_REPOSITORY`, `MLP_VPC_ID`, `MLP_SUBNET_IDS`, `MLP_INFERENCE_ROLE_ARN`, `MLP_PROMOTE_LAMBDA_NAME`, `MLP_DEPLOY_SSM_PARAM`, … |

Remote Terraform state is **required in CI** (`scripts/terraform_remote_backend.sh` writes `backend.tf` from `MLP_TF_STATE_BUCKET`).

### Concurrency

Infra and deploy workflows use concurrency groups so two applies do not fight the same state (e.g. `platform-infra-${environment}`).

---

## 4. Workflows (GitHub Actions) — how many and what each does

There are **2 platform workflows** in `.github/workflows/` (plus a copy under `templates/model-project/` for future model repos).

| # | Workflow file | Trigger | Runner | Plane | Purpose |
|---|---------------|---------|--------|-------|---------|
| 1 | `ml-lifecycle.yml` | Push/PR to `main` (model paths); `workflow_dispatch` (release/promote-only/deploy-only); `repository_dispatch` (`model-approved`) | `ubuntu-latest` | Non-Prod (train) / Prod (promote · deploy) | **Consolidated ML lifecycle:** test → train → promote → deploy |
| 2 | `platform-infra.yml` | Manual (`workflow_dispatch`) | `ubuntu-latest` | Non-Prod or Prod | **CI:** build platform Lambda images → ECR · **CD:** Terraform plan/apply for `hub-nonprod`, `hub-prod`, or `deploy-endpoint`; **deploy-bu** for BU endpoints |

**SageMaker Pipelines** (training DAGs) are separate from GitHub workflows:

| SageMaker Pipeline | Defined by | First / lighthouse |
|--------------------|------------|--------------------|
| One per model family | `pipeline.yaml` + `ml_platform/build_pipeline.py` | **credit-risk** (`examples/credit-risk/`) |

Wave-1 ships **one** lighthouse training pipeline: **credit-risk**. Later models copy `templates/model-project/` and add their own `pipeline.yaml` (each becomes another SageMaker Pipeline; CI may be extended or split per model repo).

### Job detail — `ml-lifecycle.yml` (train phase)

```text
PR / push
  └─ job test (push or PR only)
       pytest + validate pipeline.yaml + build definition (no AWS train)
  └─ job train (push to main only, environment: nonprod)
       OIDC → ECR login → docker build/push
       → build_pipeline.py --upsert
       → run_pipeline.py
            SageMaker: Preprocess → Train → Evaluate → Condition → Register
            → Model Package = PendingManualApproval
```

### Job detail — approval → Prod (promote · deploy jobs)

```text
Human: Approve package in Non-Prod Model Registry
  → EventBridge → capture_approval_event Lambda
       → DynamoDB Stage Governance
       → SSM deploy parameter
       → optional GitHub repository_dispatch (model-approved)
  → ml-lifecycle.yml promote job
       → promote_model_package Lambda (Prod)
       → Prod registry package + ModelLifeCycle Production/Approved
  → ml-lifecycle.yml deploy job (or platform-infra deploy-bu)
       → CI: build platform Lambda images → ECR (invoke-endpoint image)
       → CD: Terraform apply deploy-endpoint
       → Endpoint (+ API GW/WAF in Prod)
```

### Job detail — `platform-infra.yml` (CI → ECR → CD)

```text
workflow_dispatch (plan | apply | deploy-bu)
  └─ job build_platform_images (skip with skip_image_build for zip fallback)
       OIDC → verify mlp-platform-lambdas ECR repo exists
       → docker build/push 5 platform Lambda images (:capture-approval-{sha}, …)
  └─ job terraform (plan/apply) or deploy_bu
       TF_VAR_platform_ecr_registry + TF_VAR_platform_lambda_image_tag from CI
       → Terraform uses package_type=Image (empty vars → zip fallback for local dev)
```

**Bootstrap:** First `hub-nonprod` apply creates the `mlp-platform-lambdas` ECR repository (via `module.storage`). Run apply once with `skip_image_build=true` (zip Lambdas) or apply storage only, then use normal CI→ECR→CD.

---

## 5. What to run first (bootstrap order)

### First model options

| Goal | What to run |
|------|-------------|
| **Fast first endpoint (recommended now)** | OOTB JumpStart XGBoost — `examples/ootb_jumpstart/` + workflow `ootb-register.yml` → approve → deploy |
| **Full Train→Evaluate→Register** | Lighthouse **credit-risk** — `examples/credit-risk/` + `ml-lifecycle.yml` |

**OOTB path (no custom training):**

1. Actions → **OOTB JumpStart — register** (default model id `xgboost-classification-model`, group `ModelOotbDemo`).
2. Approve package if status is `PendingManualApproval`.
3. **platform-infra → deploy-bu** or **ml-lifecycle deploy** with the printed `model_package_arn` and endpoint name e.g. `ootb-xgboost`.

**credit-risk path (full MLOps):** keep using `ml-lifecycle.yml` after OOTB proves serving/governance plumbing.

### Step-by-step first cutover (infra + OOTB serve)

1. **Prereqs in AWS**  
   VPC + private subnets, S3 state bucket (+ DynamoDB lock table), OIDC provider for GitHub, **all IAM roles created by the client** (see [`CLIENT_MANAGED_IAM_ROLES.md`](./CLIENT_MANAGED_IAM_ROLES.md)).

2. **GitHub**  
   Create environments `nonprod` / `production`; set secrets/vars listed above (after first Terraform outputs exist, fill remaining).

3. **Pass 1a — Non-Prod hub**  
   Actions → `Platform infra` → target `hub-nonprod` → `plan` then `apply`.  
   Confirm: buckets, ECR, registry, governance, (optional) DEV BU endpoints.

4. **Pass 1b — Prod hub**  
   Same for `hub-prod` (promote Lambda, Prod registry, API GW account role, BU endpoints with WAF as configured).

5. **Wire CI**  
   Copy Terraform outputs into GitHub vars (pipeline role, data URI, ECR name, promote Lambda name, SSM paths).

6. **First model (pick one)**  
   - **OOTB (recommended first):** run `ootb-register.yml` → approve → `ml-lifecycle` deploy or `platform-infra` deploy-bu.
   - **credit-risk:** merge a change under `examples/credit-risk/` → `ml-lifecycle.yml` → wait for pipeline → approve.

7. **Approve**  
   SageMaker console (or API): set package to **Approved**.

8. **Promote + deploy**
   `ml-lifecycle` workflow_dispatch `release` (or `repository_dispatch` from governance Lambda) with the Non-Prod package ARN (BU e.g. `BU1`).

9. **Deploy Prod BU (alternate)**
   `platform-infra` → `deploy-bu` → `plane=prod` → business unit `BU1`.

10. **Smoke test**  
    `POST /invocations` with SigV4 against the API invoke URL (Prod).

---

## 6. Day-2: how code is managed and maintained

### Ownership split

| Area | Owners (typical) | Cadence |
|------|------------------|---------|
| `infra/terraform/` | Platform / MLOps | Change via PR; apply only through Actions with remote state |
| `ml_platform/` | ML platform engineers | Version carefully; all model pipelines depend on it |
| `examples/credit-risk/` | Model team + DS | Feature/model changes; CI trains on merge to main |
| `lambdas/` | Platform | Built as container images in CI → ECR; Terraform deploys `package_type=Image` (zip fallback when image vars empty) |
| `.github/workflows/` | Platform | Pin actions to SHAs; require PR review |
| `docs/` | Platform | Keep in sync when flows change |

### Branch and release practice

- **`main` is the deployment branch** for Non-Prod train (`ml-lifecycle` train job).
- Use **PRs** for all changes; PR runs `ml-lifecycle` **test** job only (no train).
- **Prod never trains from a random branch** — only Approved → promote → deploy.
- Prefer **small PRs**: infra vs model code separated when possible.
- Tag releases optionally (`vYYYY.MM.DD`) after a successful Prod deploy for audit.

### Adding a second model later

1. Copy `templates/model-project/` → `examples/<new-model>/` (or a dedicated model repo).
2. Author `pipeline.yaml` + train/eval/register/inference scripts.
3. Extend CI (matrix or separate workflow) to build that image and upsert that pipeline.
4. Create / reuse Model Package Group; register with `Development` lifecycle.
5. Reuse the same promote + `deploy-endpoint` path; new endpoint name / BU as needed.

No need to re-apply full hub Terraform for every model—only Pass 2 style endpoint deploy (and registry group if new).

### Maintenance checklist

| Item | Practice |
|------|----------|
| **Dependencies** | Pin Python deps; rebuild images on base CVE fixes |
| **Action pins** | Keep `uses: org/action@<sha>` (already pinned) |
| **Terraform** | `required_version >= 1.5`; provider `aws >= 5`; always remote state + lock |
| **IAM** | Keep SageMaker resources account-scoped; avoid new `Resource = "*"` for SM APIs |
| **Model Monitor** | Leave off for new AWS accounts; keep data capture; custom/Evidently later |
| **Secrets** | GitHub secrets + AWS Secrets Manager/KMS; never commit credentials |
| **Tests** | `pytest` in CI before AWS train; add tests when changing lambdas/pipelines |
| **Observability** | CloudWatch alarms + SNS; Stage Governance → Athena for approval audit |
| **Runbooks** | Failed pipeline → SageMaker console execution; failed apply → `terraform plan` in same env; failed promote → Lambda logs |

### What not to do

- Do not apply Terraform from a laptop against Prod without the same backend and approvals as Actions.
- Do not deploy Prod from an unapproved Non-Prod package.
- Do not enable API Gateway on Non-Prod DEV BU endpoints (breaks the control plane / BU split).
- Do not commit Cursor/`cursoragent` co-author trailers (see personal skill / local `commit-msg` hook).

---

## 7. Quick reference — “where do I click?”

| Goal | Action |
|------|--------|
| Register OOTB JumpStart model | Actions → `OOTB JumpStart — register` |
| Create / update shared Non-Prod AWS | `platform-infra` → `hub-nonprod` → apply |
| Create / update shared Prod AWS | same → `hub-prod` → apply |
| Retrain credit-risk | Push to `main` touching model paths → `ml-lifecycle` |
| Approve model | SageMaker Model Registry → Approved |
| Non-Prod → Prod registry + deploy | `ml-lifecycle` release / `model-approved` dispatch |
| Serve in Prod for a BU | `ml-lifecycle` deploy or `platform-infra` → deploy-bu → plane=prod |
| Inspect approvals | DynamoDB / Athena `stage_governance` (Stage Governance) |

---

## 8. Glossary

| Term | Meaning |
|------|---------|
| **Central Plane** | Control-{env} — Launchpad account hosting ML registry, governance, BU endpoints (Wave-1) |
| **GitHub runner** | Machine that executes workflow steps (`ubuntu-latest` hosted by GitHub) |
| **OIDC role** | IAM role assumed by the runner without static AWS keys |
| **SageMaker Pipeline** | Managed training DAG in AWS (not a GitHub Actions workflow) |
| **Model Package** | Versioned registry artifact; gate between train and serve |
| **Promote** | Re-register / copy package into Prod registry with Production lifecycle |
| **BU** | Business unit endpoint slice: BU1, BU2, BU3, BU4 |
