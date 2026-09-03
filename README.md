# ML-Platform

Multi-account **Machine Learning Platform** on AWS — pipeline factory code and SageMaker model governance deployment templates.

Adapted from [AWS Guidance: multi-account ML model governance](https://github.com/aws-solutions-library-samples/guidance-for-multi-account-machine-learning-model-governance-on-aws), extended with GitHub Actions CI/CD, hub/spoke accounts, and SageMaker Model Registry as system of record.

## Repository layout

| Path | Purpose | AWS reference |
|------|---------|---------------|
| `deployment/` | CloudFormation — hub, spoke, KMS, governance | AWS sample (steps 1a–6) |
| `source/` | Notebooks + original lambda stub | AWS sample (manual validation) |
| `ml_platform/` | Pipeline builder, step library, config | Platform factory |
| `examples/credit-risk/` | ModelCreditRisk lighthouse (`preprocess.py`, `train.py`, `evaluate.py`) | AWS notebook logic → scripts |
| `templates/model-project/` | GitHub template for new models | Platform template |
| `lambdas/` | Governance capture + endpoint invoke | AWS step1c + invoke lambda |
| `.github/workflows/` | Workflow A (CI) / B (deploy) | GitHub Actions (replaces GitLab in reference diagram) |
| `assets/` | LLD diagrams, flowchart, reference PNG | `scripts/` builders |
| `scripts/lib/` | Self-contained PPT/diagram helpers | No external repo dependencies |

## Architecture diagram

Build the consolidated LLD (GitHub, DEV/PROD VPCs, numbered flows):

**Editable draw.io:**

```bash
python scripts/build_reference_drawio.py   # → assets/ML_Platform_LLD.drawio
```

Open in [diagrams.net](https://app.diagrams.net).

**End-to-end flowchart:**

```bash
python scripts/build_flowchart.py        # → assets/ML_Platform_Flowchart.png
```

**PowerPoint with AWS icons (optional — icons fall back to tiles if not installed):**

```bash
python scripts/build_reference_lld_ppt.py
python scripts/export_drawio_from_ppt.py     # PNG-backed draw.io (visual only)
```

| File | Purpose |
|------|---------|
| `assets/ML_Platform_LLD.drawio` | Primary editable diagram |
| `assets/ML_Platform_Flowchart.png` | End-to-end flowchart |
| `assets/ML_Platform_Consolidated_LLD.pptx` | PPT with AWS icons |
| `docs/LLD.md` | LLD summary (Markdown) |

Optional: place [AWS Architecture Icons](https://aws.amazon.com/architecture/icons/) under `assets/AWS_Architecture_Icons/Architecture-Service-Icons_04302026/` for icon rendering in PPT scripts.

## Quick start — pipeline factory

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -c "from ml_platform.config import PipelineConfig; print(PipelineConfig.load('examples/credit-risk/pipeline.yaml'))"
python ml_platform/build_pipeline.py --config examples/credit-risk/pipeline.yaml
```

## Deploy AWS governance stack

1. **Hub account** — run in order:
   - `deployment/step1a-hub-sagemaker-domain-userprofile.yaml`
   - `deployment/step1b-hubaccount-model-package-share.yaml` (default group: `ModelCreditRisk`)
   - `deployment/step1c-hubaccount-model-governance-resources.yaml`
   - KMS steps 4–6 for cross-account artifact access

2. **Spoke accounts** — `step2-dev-spoke-*`, `step3-test-spoke-*`, KMS policies 5–6

3. **Validate** — run notebooks in `source/` or factory example in `examples/credit-risk/`

See the [AWS sample README](https://github.com/aws-solutions-library-samples/guidance-for-multi-account-machine-learning-model-governance-on-aws) for parameter details.

## Platform deltas from AWS sample

| AWS sample | This platform |
|------------|---------------|
| GitLab / manual notebooks | GitHub Actions + `ml_platform/build_pipeline.py` |
| QuickSight dashboards | BI via Athena (hub governance) |
| MLflow in notebooks | SageMaker Model Registry (SoR); MLflow optional |
| 3-account dev/test/hub | Hub Non-Prod/Prod + BU spokes |
| DevOps entry | Dedicated factory account (configure in CI secrets) |

## Model lifecycle

```
GitHub push → Workflow A → ECR → SageMaker Pipeline
  → Preprocess → Train → Evaluate → Condition → Register (Pending)
  → Senior DS Approve → EventBridge → Lambda → DynamoDB
  → Workflow B → Terraform endpoint → Model Monitor → optional MCP tool
```

## Serving contract

```json
POST /invocations
Request:  { "features": [ ... ] }
Response: { "prediction": <value>, "score": <0..1>, "model_version": "credit-risk:3" }
```

## License

MIT-0 (inherits AWS sample license).
