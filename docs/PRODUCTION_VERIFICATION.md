# AWS / production-grade verification notes (Central Plane)
#
# Checked against AWS docs (2026-03):
# - https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vs-rest.html
# - https://docs.aws.amazon.com/waf/latest/APIReference/API_AssociateWebACL.html
# - https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor-availability-change.html
# - https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry-staging-construct-set-up.html
# - Security Hub control APIGateway.4 (WAF on REST stages)

## Critical / high fixes applied

| Issue | AWS fact | Fix |
|-------|----------|-----|
| WAF on HTTP API (v2) | WAFv2 does not support HTTP APIs | `api_gateway` = **REST API** + correct stage ARN |
| REST access logs | Account CloudWatch role required | `modules/api_gateway_account` |
| Model Monitor for new accounts | Closed to new customers | Default **false**; data capture kept |
| SageMaker IAM `Resource = "*"` | Prefer account-scoped ARNs | `modules/iam` + promote + step_functions scoped |
| No VPC endpoints | Private ML traffic guidance | S3 gateway + SM/ECR/Logs/STS/CW interfaces |
| Local TF state in CI | Remote state / locking | `scripts/terraform_remote_backend.sh` in workflows |
| No ModelLifeCycle | Staging construct | Register = Development; Promote = Production |

## Verified aligned

| Control | Evidence |
|---------|----------|
| Central registry + PendingManualApproval | register scripts |
| EventBridge → Lambda → DDB | governance |
| Promote Non-Prod → Prod + RAM share option | promote + registry RAM |
| IAM auth + WAF on invoke | REST + waf module |
| Data capture | endpoint module |
| KMS | kms module |
| Unit tests | `tests/` |

## Operator prerequisites

- GitHub Variables: `MLP_TF_STATE_BUCKET` (required), `MLP_TF_STATE_LOCK_TABLE` (recommended)
- Set `spoke_account_ids` so promote IAM can describe Non-Prod packages by account
- Existing Model Monitor customers may set `enable_model_monitor=true`
