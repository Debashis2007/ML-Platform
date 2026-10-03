# Client-managed IAM roles

The client creates **all** AWS IAM roles. Terraform and GitHub Actions only **consume ARNs**.

Account placement and role IDs (H-02, H-09, S-18–S-22): [`ACCOUNTS_AND_ROLES.md`](./ACCOUNTS_AND_ROLES.md).

## Role inventory

| Role purpose | Typical name (example) | Account | Trust principal | Used by |
|--------------|------------------------|--------------|-----------------|---------|
| SageMaker pipeline execution | `mlp-sagemaker-pipeline` | **Control-{env}** | `sagemaker.amazonaws.com` | Pipeline upsert/run, PassRole to training |
| SageMaker training/processing | `mlp-sagemaker-training` | **Control-{env}** | `sagemaker.amazonaws.com` | Training/processing jobs |
| SageMaker inference / endpoint | `mlp-sagemaker-inference` | **Control-{env}** | `sagemaker.amazonaws.com` | Endpoint model execution |
| GitHub Actions — pipeline CI | `mlp-gha-pipeline` | **Control-NonProd** | GitHub OIDC federated | `ml-lifecycle.yml` (`MLP_GHA_PIPELINE_ROLE_ARN`) |
| GitHub Actions — Terraform/deploy | `mlp-gha-deploy` | **Control-{env}** | GitHub OIDC federated | infra/promote/deploy workflows (`MLP_GHA_DEPLOY_ROLE_ARN`) |
| Governance capture Lambda | `mlp-governance-lambda` | **Control-{env}** | `lambda.amazonaws.com` | `capture_approval_event` |
| GitHub dispatch Lambda (optional) | `mlp-github-dispatch` | **Control-{env}** | `lambda.amazonaws.com` | auto-deploy `repository_dispatch` |
| Promote Lambda (Prod) | `mlp-promote-model` | **Control-Prod** | `lambda.amazonaws.com` | Non-Prod → Prod package copy |
| Stage Governance export Lambda | `mlp-governance-export` | **Control-{env}** | `lambda.amazonaws.com` | DDB → S3 export for Athena |
| Step Functions pipeline trigger | `mlp-pipeline-trigger` | **Control-{env}** | `states.amazonaws.com` | Start SageMaker pipeline execution |
| Invoke-endpoint Lambda (Prod API) | `mlp-invoke-endpoint` | **Control-Prod** | `lambda.amazonaws.com` | API GW → SageMaker InvokeEndpoint |
| API Gateway CloudWatch logs | `mlp-apigw-cloudwatch` | **Control-Prod** | `apigateway.amazonaws.com` | REST API access/execution logs |
| Model Monitor (optional, existing customers) | `mlp-model-monitor` | **Control-{env}** | `sagemaker.amazonaws.com` | Monitoring schedules only if enabled |
| BU app runtime (consumer) | `bu-app-runtime` | **BU-{name}-{env}** | app compute | Invoke ML endpoint / API GW — **not** created by this repo |

## Terraform variables (pass these ARNs)

### `hub-nonprod` / `hub-prod`

| Variable | Required when |
|----------|----------------|
| `pipeline_role_arn` | Always |
| `training_role_arn` | Always |
| `inference_role_arn` | Endpoints / BU endpoints enabled |
| `governance_lambda_role_arn` | Governance enabled |
| `github_dispatch_lambda_role_arn` | `enable_auto_deploy=true` |
| `stage_export_lambda_role_arn` | Stage analytics / governance export |
| `step_functions_role_arn` | Always (pipeline trigger SFN) |
| `promote_lambda_role_arn` | Prod + promote enabled |
| `invoke_lambda_role_arn` | Prod BU endpoints + API GW |
| `apigateway_cloudwatch_role_arn` | Prod API GW access logs |

### `deploy-endpoint`

| Variable | Required when |
|----------|----------------|
| `inference_role_arn` | Always |
| `invoke_lambda_role_arn` | `enable_api_gateway=true` |
| `apigateway_cloudwatch_role_arn` | API GW + access logs |
| `monitoring_role_arn` | Model Monitor enabled (rare) |

## Permission checklist (minimum)

**SageMaker pipeline role:** create/start/describe pipelines and jobs; PassRole to training role; S3 on data/artifacts buckets; ECR pull; CloudWatch logs/metrics; KMS on platform key.

**Training role:** S3 read/write data+artifacts; ECR pull; create/describe training & processing jobs; logs/metrics; KMS.

**Inference role:** pull model artifacts from S3/ECR; describe model package; endpoint runtime; logs; KMS; data-capture write if used.

**GHA pipeline role:** ECR push/pull; S3 data/artifacts; StartPipelineExecution / upsert via SageMaker APIs; PassRole to pipeline+training.

**GHA deploy role:** Terraform-needed service permissions (scoped by your IaC); SageMaker create/update endpoint; SSM get deploy params; PassRole to inference; invoke promote Lambda if used from Actions; **ECR push/pull** on `mlp-platform-lambdas` repository (platform Lambda CI before Terraform CD).

**Governance Lambda:** DynamoDB put/get on governance table; SSM put under `/{prefix}/deploy/*`; events:PutEvents; logs; KMS if table encrypted.

**Promote Lambda:** DescribeModelPackage (source accounts); CreateModelPackage on Prod group; SSM put; events:PutEvents; logs; KMS.

**Export Lambda:** DynamoDB scan governance table; S3 put to Athena spill bucket; logs; KMS.

**SFN role:** `sagemaker:StartPipelineExecution` / `DescribePipeline` on named pipeline ARNs.

**Invoke Lambda:** `sagemaker:InvokeEndpoint` on BU endpoint ARNs; logs.

**API GW CloudWatch role:** managed policy `AmazonAPIGatewayPushToCloudWatchLogs` (or equivalent).

## GitHub secrets (not created by Terraform)

Set after the client creates GHA roles:

- `MLP_GHA_PIPELINE_ROLE_ARN`
- `MLP_GHA_DEPLOY_ROLE_ARN`

## Legacy CloudFormation (`deployment/`)

Older `deployment/step*.yaml` templates still contain `AWS::IAM::Role` resources (hub/spoke SageMaker execution roles, StackSet admin, etc.). **Do not use those templates to create platform roles** if the client owns IAM. Prefer Terraform env roots with ARN inputs above. Treat `deployment/` as reference / migration only until retired.

## Design v7 roles

Roles added for copy-in registration, the management API and releases. Step Functions
(`step_functions_role_arn`), control-plane BU endpoints (`invoke_lambda_role_arn`,
`apigateway_cloudwatch_role_arn` in the hubs) are no longer used.

| Role purpose | Typical name | Account | Trust | Terraform variable |
|--------------|--------------|---------|-------|--------------------|
| Copy-in registration Lambda | `mlp-register-candidate` | Control-{env} | `lambda.amazonaws.com` | `registration_lambda_role_arn` |
| Approval API Lambda | `mlp-approval-api` | Control-{env} | `lambda.amazonaws.com` | `approval_lambda_role_arn` |
| Okta authorizer Lambda | `mlp-okta-authorizer` | Control-{env} | `lambda.amazonaws.com` | `authorizer_lambda_role_arn` |
| NonProd registry read (promotion) | `mlp-registry-read` | Control-NonProd | Prod promote role, GHA | `source_registry_read_role_arn` |
| BU candidate read (BU training only) | `<bu>-ml-candidate-read` | BU NonProd | Control-plane registration role | `source_read_role_name` |
| Release deploy role | `<bu>-ml-release` | BU NonProd / BU Prod | GitHub OIDC | `target_role_arn` or `MLP_GHA_RELEASE_ROLE_ARN` |

**Registration Lambda:** `sagemaker:ListPipelineParametersForExecution`, `sagemaker:CreateModelPackage`,
`sagemaker:DescribeModelPackageGroup`; `s3:GetObject` on run outputs; `s3:PutObject` and
`s3:GetObjectAttributes` on the artefact and evidence buckets; DynamoDB put/get/update on
`ml_lifecycle` and put on `ml_decision_log`; `sts:AssumeRole` on BU read roles (BU training);
KMS; VPC ENI permissions. **Explicitly deny `sagemaker:UpdateModelPackage`.**

**Approval API Lambda:** the only principal allowed `sagemaker:UpdateModelPackage`;
`sagemaker:DescribeModelPackage`; DynamoDB get on `ml_identity`, get/update on
`ml_lifecycle`, put on `ml_decision_log`, put/delete on `ml_locks`; KMS; VPC ENI permissions.
Deny `sagemaker:UpdateModelPackage` to every other role (including human console roles) through
an SCP or permission boundary so approval can only come from the API.

**Okta authorizer Lambda:** logs and VPC ENI permissions only (outbound HTTPS to the Okta JWKS
URL through the egress path).

**Capture Lambda (updated):** DynamoDB get on `ml_lifecycle`, put on `ml_decision_log`;
`sagemaker:DescribeModelPackage`; SSM put; `events:PutEvents`.

**Promote Lambda (updated):** `sts:AssumeRole` on `mlp-registry-read`; `ecr:DescribeImages` on
Prod model repositories; put on the Prod `ml_decision_log`; `events:PutEvents`. No
`CreateModelPackage`.

**Inference role (deployment target account):** `sagemaker:DescribeModelPackage` on the shared
control-plane package; `ecr:BatchGetImage`/`GetDownloadUrlForLayer` on the control-plane model
repository (granted by `ecr_pull_account_ids`); `s3:GetObject` on the artefact store (bucket
policy grant per target account).
