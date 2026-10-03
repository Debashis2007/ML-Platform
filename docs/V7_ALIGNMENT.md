# ML Platform — design v7 alignment

This repository implements the v7 ML design with one POC deviation: **training runs in the
control plane NonProd account** (`aws.training_target: control_plane`). The v7 target
state trains in the BU account; switching is a `model.yaml` change (see below), not a code change.

## Lifecycle

```
model repo push
  → image built, pushed to ml-models/<model_id> (immutable), pinned by digest
  → pipeline upserted and started in aws.account_id (POC: Control-NonProd)
       Train → Evaluate → CheckMetric ──pass──▶ PublishCandidate (candidate.json + sha256)
  → EventBridge "Pipeline Execution Status Change" (Succeeded)
  → register_candidate Lambda (control plane, no approval rights)
       verify manifest ↔ pipeline parameters, copy artefact with SHA-256 verification into the
       Object Lock artefact store, write evidence, create PendingManualApproval package,
       lifecycle record + decision log
  → senior data scientist approves via the private management API (POST /approvals)
       Okta TOKEN authorizer → identity + tenant scope → separation of duties → lock (TTL,
       fencing) → hash binding → UpdateModelPackage(Approved)
  → capture_approval_event: API-bound approval → deploy signal; console approval → violation
  → release (QA): blue/green ALL_AT_ONCE in the BU NonProd account
  → promote: copy image by digest to Prod ECR → promote Lambda records PROMOTION_REQUESTED
       → Prod retrain with LineageSourcePackageArn → Prod PendingManualApproval
       → Prod senior data scientist approves
  → release (LIVE): blue/green CANARY 10%, 15-minute bake, rollback alarms, ≥ 2 instances
```

## What changed in the code

| Area | v7 behaviour | Where |
|------|--------------|-------|
| Model configuration | `model.yaml`: tenant, BU, type, platform version, training target, evaluation thresholds, serving, deployment targets, approvers, Prod retrain target (`aws.prod`) | `ml_platform/config.py`, `examples/credit-risk/model.yaml`, `templates/model-project/model.yaml` |
| Pipeline | No in-pipeline registration. All thresholds gate `PublishCandidate`; image must be a digest; `SourceCommit`, `SubmittedBy`, `LineageSourcePackageArn` parameters; `max_run`; bu/project/version tags | `ml_platform/steps/`, `ml_platform/scripts/publish_candidate.py` |
| Caller check | `build_pipeline --upsert` and `run_pipeline` refuse to run outside `aws.account_id` | `ml_platform/build_pipeline.py`, `ml_platform/run_pipeline.py` |
| Copy-in registration | Checksum-verified copy, evidence, PendingManualApproval, idempotent on artefact hash | `lambdas/register_candidate/` |
| Approval | Private management API; Okta (no Cognito); identity, separation of duties, lock, hash binding | `lambdas/approval_api/`, `lambdas/okta_authorizer/`, `modules/management_api/` |
| Approval capture | Console approvals without an API approval are `APPROVAL_VIOLATION` and never deploy | `lambdas/capture_approval_event/` |
| Governance data | `ml_lifecycle`, `ml_decision_log`, `ml_identity`, `ml_locks` — PITR, deletion protection, streams | `modules/governance/` |
| Storage | Snapshot, artefact and evidence buckets with Object Lock GOVERNANCE 730 days; deny delete/bypass except break-glass; TLS only; 7-day staging on `pipelines/`; per-model immutable ECR with count-based retention | `modules/storage/` |
| Promotion | Copy by digest, record request, Prod retrain with lineage; never creates an Approved package | `lambdas/promote_model_package/`, `.github/workflows/ml-lifecycle.yml` |
| Release | Release-unique model/config, blue/green (QA all-at-once, LIVE canary 10% / 900 s), rollback alarms required, LIVE ≥ 2, Application Auto Scaling | `modules/endpoint/`, `envs/deploy-endpoint/` |
| Network | Control-plane and BU endpoint sets, DynamoDB gateway, security-group egress limited to HTTPS inside the VPC and gateway prefix lists | `modules/network/` |
| Tags | Provider `default_tags`: `bu`, `project`, `version` | all envs |
| Removed | Step Functions trigger, control-plane BU endpoints, Prod package auto-approval | `modules/step_functions`, `modules/bu_endpoints` deleted |

## POC deviation: training on the control plane

| | POC (this repo default) | v7 target state |
|--|--|--|
| `aws.training_target` | `control_plane` | `bu` |
| `aws.account_id` / `pipeline_role_arn` | Control-NonProd | BU NonProd account and member role |
| Pipeline status event | Default bus in the control plane | Forwarded by a BU rule to the hub bus `<prefix>-ml-hub` |
| Registration Lambda reads candidate | Same account | Assumes `source_read_role_name` in the BU account |
| Terraform | — | Set `training_account_ids` and `source_read_role_name` in `hub-nonprod` |

Switching to BU training needs the BU-side event forwarding rule, the BU pipeline role, the
read role, and a bucket policy on the BU run bucket granting the registration role
`s3:GetObject`. These belong to the BU account baseline, not this repository.

## Release environments

GitHub environments `ml-nonprod`, `ml-promote`, `ml-qa`, `ml-live` with required reviewers on
`ml-promote` and `ml-live`. Secrets: `MLP_GHA_PIPELINE_ROLE_ARN`, `MLP_GHA_NONPROD_READ_ROLE_ARN`,
`MLP_GHA_PROD_PIPELINE_ROLE_ARN`, `MLP_GHA_REGISTRY_READ_ROLE_ARN`, `MLP_GHA_RELEASE_ROLE_ARN`
(per environment). Variables: `MLP_ARTIFACTS_BUCKET`, `MLP_PROD_ARTIFACTS_BUCKET`,
`MLP_PROMOTE_LAMBDA_NAME`, `MLP_ENDPOINT_NAME`, `MLP_BU`, `MLP_VPC_ID`, `MLP_SUBNET_IDS`,
`MLP_INFERENCE_ROLE_ARN`, `MLP_KMS_KEY_ARN`, optional `MLP_SMOKE_PAYLOAD`.

## Approving a package

```bash
# From inside the control-plane VPC (private API), with an Okta access token:
curl -s "$MGMT_API/approvals?model_package_arn=$ARN" -H "Authorization: Bearer $TOKEN"
# Review evidence_uri and canonical_hash, then:
curl -s -X POST "$MGMT_API/approvals" -H "Authorization: Bearer $TOKEN" \
  -d "{\"model_package_arn\":\"$ARN\",\"decision\":\"approve\",\"canonical_hash\":\"$HASH\",\"comment\":\"reviewed\"}"
```

Approvers are rows in `ml_identity`: `pk` = lower-case email, `roles` contains
`senior_data_scientist`, `tenants` lists tenant IDs (or `*`), `status` = `active`, optional
`github_login` for the separation-of-duties check.

## DR notes

Restore order: `ml_identity`, then `ml_decision_log`, then `ml_lifecycle`; reconcile
lifecycle against the registry before writes resume. `ml_locks` is never restored. Object
Lock buckets replicate with retention preserved.
