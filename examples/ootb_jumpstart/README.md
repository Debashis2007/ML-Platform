# Out-of-the-box (OOTB) JumpStart model — first deploy / smoke test

Use this when you want a **working SageMaker endpoint** without training `credit-risk`.

| Item | Value |
|------|--------|
| Default JumpStart model | `xgboost-classification-model` |
| Default package group | `ModelOotbDemo` |
| Full MLOps example (later) | `examples/credit-risk/` |

## Prerequisites

- Client-managed `pipeline` (or SageMaker execution) role ARN
- Model Registry usable in the Non-Prod (or target) account
- Hub Terraform already applied (or at least VPC + deploy-endpoint inputs ready)

## Register

```bash
export AWS_REGION=us-east-1
export SAGEMAKER_PIPELINE_ROLE_ARN=arn:aws:iam::ACCOUNT:role/mlp-sagemaker-pipeline

python examples/ootb_jumpstart/register_ootb.py \
  --model-package-group ModelOotbDemo \
  --role-arn "$SAGEMAKER_PIPELINE_ROLE_ARN"
```

Or via GitHub Actions: workflow **OOTB JumpStart — register** (`ootb-register.yml`).

## Deploy

1. Approve the package in Model Registry (skip if you passed `--approval-status Approved` for Non-Prod smoke).
2. Run **ml-lifecycle → release** with:
   - `model_package_arn` = ARN printed by the register step
   - `endpoint_name` = e.g. `ootb-xgboost` (or BU name as usual)
3. Invoke the endpoint (CSV for default XGBoost JumpStart), or Prod API `POST /invocations` if your invoke Lambda is adapted for that payload.

## Switch back to credit-risk

Keep using `ml-lifecycle.yml` + `examples/credit-risk/` for Train → Evaluate → Register. OOTB is only for platform plumbing validation.
