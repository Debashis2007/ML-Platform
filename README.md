# ML-Platform

Multi-account **Machine Learning Platform** on AWS — SageMaker pipeline factory and model governance.

Adapted from [AWS Guidance: multi-account ML model governance](https://github.com/aws-solutions-library-samples/guidance-for-multi-account-machine-learning-model-governance-on-aws), extended with GitHub Actions CI/CD, hub/spoke accounts, and SageMaker Model Registry as system of record.

## Repository layout

| Path | Purpose |
|------|---------|
| `deployment/` | **Infrastructure (CloudFormation)** — hub, spoke, KMS, governance stacks |
| `ml_platform/` | Pipeline builder, step library, config |
| `examples/credit-risk/` | Lighthouse model (`preprocess.py`, `train.py`, `evaluate.py`, `register.py`) |
| `templates/model-project/` | GitHub template for new model repos |
| `lambdas/` | Governance event capture + endpoint invoke handlers |
| `.github/workflows/` | Workflow A (CI/train) and Workflow B (deploy) — stubs until infra is wired |
| `source/` | AWS sample notebooks for manual validation |

## Infrastructure — what exists today

**CloudFormation** lives under `deployment/` (from the AWS guidance sample):

| Step | File | Account |
|------|------|---------|
| 1a | `step1a-hub-sagemaker-domain-userprofile.yaml` | Hub |
| 1b | `step1b-hubaccount-model-package-share.yaml` | Hub |
| 1c | `step1c-hubaccount-model-governance-resources.yaml` | Hub |
| 2 | `step2-dev-spoke-sagemaker-domain-userprofile.yaml` | Dev spoke |
| 3 | `step3-test-spoke-sagemaker-domain-userprofile.yaml` | Test spoke |
| 4–6 | `step4`–`step6` KMS cross-account policies | Hub + spokes |
| — | `stacksets_roles/` | StackSet admin/execution roles |

Deploy hub stacks in order, then spokes, then KMS policies. See the [AWS sample README](https://github.com/aws-solutions-library-samples/guidance-for-multi-account-machine-learning-model-governance-on-aws) for parameters.

## Terraform — not in this repo yet

There is **no `infra/` or `.tf` code** in this repository. Workflow B (`.github/workflows/model-deploy.yml`) and the model lifecycle below reference Terraform endpoint deploy as the **target** pattern; that module still needs to be added (e.g. under `infra/terraform/`).

Wave-1 foundation can be stood up with the CloudFormation templates above; Terraform would cover shared factory resources (VPC endpoints, ECR, registry, endpoint modules) when implemented.

## Quick start — pipeline factory

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -c "from ml_platform.config import PipelineConfig; print(PipelineConfig.load('examples/credit-risk/pipeline.yaml'))"
python ml_platform/build_pipeline.py --config examples/credit-risk/pipeline.yaml
```

## Model lifecycle

```
GitHub push → Workflow A → ECR → SageMaker Pipeline
  → Preprocess → Train → Evaluate → Condition → Register (Pending)
  → Senior DS Approve → EventBridge → Lambda → DynamoDB
  → Workflow B → endpoint deploy (Terraform — TBD) → Model Monitor
```

## Serving contract

```json
POST /invocations
Request:  { "features": [ ... ] }
Response: { "prediction": <value>, "score": <0..1>, "model_version": "credit-risk:3" }
```

## License

MIT-0 (inherits AWS sample license).
