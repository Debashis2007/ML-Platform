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
│  Workflows: platform-infra · admin-run · model-ci ·                │
│             model-promote · model-deploy                                │
└───────────────┬───────────────────────────────┬─────────────────────────┘
                │                               │
                ▼                               ▼
┌───────────────────────────┐     ┌───────────────────────────────────────┐
│  NONPROD Central Plane    │     │  PROD Central Plane                   │
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
| **ML pipeline** | Train/eval/register DAG per model | SageMaker Pipeline started by `model-ci.yml` |
| **Serving** | Real-time inference | Endpoint (+ API GW in Prod) from approved package |

Terraform does **not** define training steps. Python (`ml_platform/`) builds the SageMaker Pipeline that uses resources Terraform created.

---

## 2. Environments and promotion path

### Environments

| Environment | AWS account / plane | Terraform root | GitHub Environment |
|-------------|---------------------|----------------|--------------------|
| **Non-Prod** | Non-Prod Central Plane | `infra/terraform/envs/hub-nonprod/` | `nonprod` |
| **Prod** | Prod Central Plane | `infra/terraform/envs/hub-prod/` | `production` |
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
3. Train & register in Non-Prod    (model-ci → SageMaker Pipeline)
4. Human approval in Model Registry (PendingManualApproval → Approved)
5. Promote package Non-Prod → Prod (model-promote / admin-run promote)
6. Deploy BU endpoint in Prod      (admin-run deploy-bu / model-deploy)
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

There are **5 platform workflows** in `.github/workflows/` (plus a copy under `templates/model-project/` for future model repos).

| # | Workflow file | Trigger | Runner | Plane | Purpose |
|---|---------------|---------|--------|-------|---------|
| 1 | `platform-infra.yml` | Manual (`workflow_dispatch`) | `ubuntu-latest` | Non-Prod or Prod | Terraform plan/apply for `hub-nonprod`, `hub-prod`, or `deploy-endpoint` |
| 2 | `admin-run.yml` | Manual | `ubuntu-latest` | Selected plane | orchestrator: plan/apply hub, **promote**, **deploy-bu** |
| 3 | `model-ci.yml` | Push/PR to `main` (model paths) | `ubuntu-latest` | Non-Prod (train job) | Tests → build image → upsert & run SageMaker Pipeline → register |
| 4 | `model-promote.yml` | Manual or `repository_dispatch` | `ubuntu-latest` | Prod | Copy Approved Non-Prod package into Prod registry; can trigger deploy |
| 5 | `model-deploy.yml` | Manual or `repository_dispatch` | `ubuntu-latest` | Prod | Terraform `deploy-endpoint` + optional smoke test |

**SageMaker Pipelines** (training DAGs) are separate from GitHub workflows:

| SageMaker Pipeline | Defined by | First / lighthouse |
|--------------------|------------|--------------------|
| One per model family | `pipeline.yaml` + `ml_platform/build_pipeline.py` | **credit-risk** (`examples/credit-risk/`) |

Wave-1 ships **one** lighthouse training pipeline: **credit-risk**. Later models copy `templates/model-project/` and add their own `pipeline.yaml` (each becomes another SageMaker Pipeline; CI may be extended or split per model repo).

### Job detail — `model-ci.yml` (Workflow A)

```text
PR / push
  └─ job test (always)
       pytest + validate pipeline.yaml + build definition (no AWS train)
  └─ job train (push to main only, environment: nonprod)
       OIDC → ECR login → docker build/push
       → build_pipeline.py --upsert
       → run_pipeline.py
            SageMaker: Preprocess → Train → Evaluate → Condition → Register
            → Model Package = PendingManualApproval
```

### Job detail — approval → Prod (Workflow B + promote)

```text
Human: Approve package in Non-Prod Model Registry
  → EventBridge → capture_approval_event Lambda
       → DynamoDB Stage Governance
       → SSM deploy parameter
       → optional GitHub repository_dispatch
  → model-promote.yml (or admin-run action=promote)
       → promote_model_package Lambda (Prod)
       → Prod registry package + ModelLifeCycle Production/Approved
  → admin-run deploy-bu (plane=prod, BU=BU1|…)
       or model-deploy.yml
       → Endpoint (+ API GW/WAF in Prod)
```

---

## 5. What to run first (bootstrap order)

### First model

**Run credit-risk first.** It is the reference implementation:

- Config: `examples/credit-risk/pipeline.yaml`
- Scripts: `preprocess.py`, `train.py`, `evaluate.py`, `register.py`, `inference.py`
- CI already points at it (`MODEL_NAME: credit-risk`)

Do not onboard BU1/BU2/BU3/BU4 serving until credit-risk has trained, registered, been approved, promoted, and deployed once end-to-end.

### Step-by-step first cutover

1. **Prereqs in AWS**  
   VPC + private subnets, S3 state bucket (+ DynamoDB lock table), OIDC provider for GitHub, **all IAM roles created by the client** (see [`CLIENT_MANAGED_IAM_ROLES.md`](./CLIENT_MANAGED_IAM_ROLES.md)).

2. **GitHub**  
   Create environments `nonprod` / `production`; set secrets/vars listed above (after first Terraform outputs exist, fill remaining).

3. **Pass 1a — Non-Prod hub**  
   Actions → `Admin Run` or `Platform infra` → environment `hub-nonprod` → `plan` then `apply`.  
   Confirm: buckets, ECR, registry, governance, (optional) DEV BU endpoints.

4. **Pass 1b — Prod hub**  
   Same for `hub-prod` (promote Lambda, Prod registry, API GW account role, BU endpoints with WAF as configured).

5. **Wire CI**  
   Copy Terraform outputs into GitHub vars (pipeline role, data URI, ECR name, promote Lambda name, SSM paths).

6. **First train**  
   Merge a change under `examples/credit-risk/` or `ml_platform/` to `main` → `model-ci.yml` runs → wait for SageMaker Pipeline success → package in **PendingManualApproval**.

7. **Approve**  
   SageMaker console (or API): set package to **Approved**.

8. **Promote**  
   `Model promote` workflow with the Non-Prod package ARN (BU e.g. `BU1`).

9. **Deploy Prod BU**  
   `admin-run` → `deploy-bu` → `plane=prod` → business unit `BU1` (or `model-deploy.yml`).

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
| `lambdas/` | Platform | Deployed as zip via Terraform when hub/deploy applies |
| `.github/workflows/` | Platform | Pin actions to SHAs; require PR review |
| `docs/` | Platform | Keep in sync when flows change |

### Branch and release practice

- **`main` is the deployment branch** for Non-Prod train (`model-ci` train job).
- Use **PRs** for all changes; PR runs `model-ci` **test** job only (no train).
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
| Create / update shared Non-Prod AWS | `admin-run` or `platform-infra` → `hub-nonprod` → apply |
| Create / update shared Prod AWS | same → `hub-prod` → apply |
| Retrain credit-risk | Push to `main` touching model paths → `model-ci` |
| Approve model | SageMaker Model Registry → Approved |
| Non-Prod → Prod registry | `model-promote` or `admin-run` → promote |
| Serve in Prod for a BU | `admin-run` → deploy-bu → plane=prod |
| Inspect approvals | DynamoDB / Athena `stage_governance` (Stage Governance) |

---

## 8. Glossary

| Term | Meaning |
|------|---------|
| **Central Plane** | Shared account(s) hosting registry, governance, BU endpoints |
| **GitHub runner** | Machine that executes workflow steps (`ubuntu-latest` hosted by GitHub) |
| **OIDC role** | IAM role assumed by the runner without static AWS keys |
| **SageMaker Pipeline** | Managed training DAG in AWS (not a GitHub Actions workflow) |
| **Model Package** | Versioned registry artifact; gate between train and serve |
| **Promote** | Re-register / copy package into Prod registry with Production lifecycle |
| **BU** | Business unit endpoint slice: BU1, BU2, BU3, BU4 |
