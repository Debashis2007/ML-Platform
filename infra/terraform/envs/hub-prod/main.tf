terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "archive_file" "capture_approval_lambda" {
  count       = var.enable_governance ? 1 : 0
  type        = "zip"
  source_dir  = "${path.module}/../../../../lambdas/capture_approval_event"
  output_path = "${path.module}/.build/capture_approval.zip"
}

data "archive_file" "github_dispatch_lambda" {
  count       = var.enable_governance && var.enable_auto_deploy ? 1 : 0
  type        = "zip"
  source_dir  = "${path.module}/../../../../lambdas/trigger_github_deploy"
  output_path = "${path.module}/.build/github_dispatch.zip"
}

module "kms" {
  source = "../../modules/kms"

  name_prefix       = var.name_prefix
  spoke_account_ids = var.spoke_account_ids
  tags              = var.tags
}

module "network" {
  source = "../../modules/network"

  name_prefix = var.name_prefix
  vpc_id      = var.vpc_id
  subnet_ids  = var.subnet_ids
  tags        = var.tags
}

module "storage" {
  source = "../../modules/storage"

  name_prefix               = var.name_prefix
  data_bucket_name          = var.data_bucket_name
  dev_artifacts_bucket_name = var.dev_artifacts_bucket_name
  artifacts_bucket_name     = var.artifacts_bucket_name
  prod_data_bucket_name     = var.prod_data_bucket_name
  ecr_repository_name       = var.ecr_repository_name
  kms_key_arn               = module.kms.key_arn
  tags                      = var.tags
}

module "secrets" {
  source = "../../modules/secrets"

  name_prefix           = var.name_prefix
  kms_key_arn           = module.kms.key_arn
  github_dispatch_token = var.github_dispatch_token
  tags                  = var.tags
}

module "iam" {
  count  = var.create_iam_roles ? 1 : 0
  source = "../../modules/iam"

  name_prefix              = var.name_prefix
  data_bucket_arn          = module.storage.data_bucket_arn
  artifacts_bucket_arn     = module.storage.artifacts_bucket_arn
  ecr_repository_arn       = module.storage.ecr_repository_arn
  github_oidc_provider_arn = var.github_oidc_provider_arn
  github_repo_subjects     = var.github_repo_subjects
  kms_key_arn              = module.kms.key_arn
  tags                     = var.tags
}

module "registry" {
  count  = var.create_registry ? 1 : 0
  source = "../../modules/registry"

  model_package_group_name = var.model_package_group_name
  description              = "ML Platform PROD model registry"
  spoke_account_ids        = var.spoke_account_ids
  tags                     = var.tags
}

module "governance" {
  count  = var.enable_governance ? 1 : 0
  source = "../../modules/governance"

  name_prefix              = var.name_prefix
  model_package_group_name = var.model_package_group_name
  lambda_source_dir        = "${path.module}/.build"
  deploy_parameter_prefix  = "/${var.name_prefix}/deploy"
  kms_key_arn              = module.kms.key_arn
  enable_auto_deploy       = var.enable_auto_deploy
  github_owner             = var.github_owner
  github_repo              = var.github_repo
  github_token_secret_arn  = coalesce(module.secrets.github_dispatch_secret_arn, "")
  tags                     = var.tags

  depends_on = [
    data.archive_file.capture_approval_lambda,
    data.archive_file.github_dispatch_lambda,
  ]
}

module "sns" {
  source = "../../modules/sns"

  name_prefix = var.name_prefix
  kms_key_arn = module.kms.key_arn
  tags        = var.tags
}

locals {
  pipeline_role_arn = var.create_iam_roles ? module.iam[0].pipeline_role_arn : var.pipeline_role_arn
  training_role_arn = var.create_iam_roles ? module.iam[0].training_role_arn : var.training_role_arn
}

module "credit_risk_pipeline_prod" {
  source = "../../modules/evaluation-pipeline"

  name_prefix              = var.name_prefix
  model_name               = "credit-risk-prod"
  pipeline_role_arn        = local.pipeline_role_arn
  training_role_arn        = local.training_role_arn
  artifacts_bucket_name    = module.storage.artifacts_bucket_name
  data_bucket_name         = module.storage.prod_data_bucket_name != null ? module.storage.prod_data_bucket_name : module.storage.data_bucket_name
  model_package_group_name = var.model_package_group_name
  metric_name              = "auc"
  metric_threshold         = 0.75
  tags                     = var.tags
}

module "deploy_trigger" {
  source = "../../modules/step_functions"

  name_prefix       = var.name_prefix
  pipeline_name     = "credit-risk-prod"
  pipeline_role_arn = local.pipeline_role_arn
  tags              = var.tags
}

module "cloudwatch" {
  source = "../../modules/cloudwatch"

  name_prefix    = var.name_prefix
  pipeline_names = ["credit-risk-prod"]
  endpoint_name  = var.endpoint_name
  tags           = var.tags
}

module "monitoring" {
  source = "../../modules/monitoring"

  name_prefix   = var.name_prefix
  endpoint_name = var.endpoint_name
  alarm_actions = [module.sns.alerts_topic_arn]
  tags          = var.tags
}

module "stage_analytics" {
  count  = var.enable_governance ? 1 : 0
  source = "../../modules/stage_analytics"

  name_prefix           = var.name_prefix
  governance_table_name = module.governance[0].governance_table_name
  governance_table_arn  = module.governance[0].governance_table_arn
  kms_key_arn           = module.kms.key_arn
  spill_bucket_name     = var.athena_spill_bucket_name
  quicksight_user_arn   = var.quicksight_user_arn
  tags                  = var.tags
}

data "archive_file" "promote_lambda" {
  count       = var.enable_promote ? 1 : 0
  type        = "zip"
  source_dir  = "${path.module}/../../../../lambdas/promote_model_package"
  output_path = "${path.module}/.build/promote_model.zip"
}

data "archive_file" "invoke_endpoint_lambda" {
  count       = var.enable_bu_endpoints ? 1 : 0
  type        = "zip"
  source_dir  = "${path.module}/../../../../lambdas/invoke_endpoint"
  output_path = "${path.module}/.build/invoke_endpoint.zip"
}

# Non-Prod Approved → Prod registry (invoked by admin-run / model-promote.yml).
module "promote" {
  count  = var.enable_promote ? 1 : 0
  source = "../../modules/promote"

  name_prefix                = var.name_prefix
  lambda_zip_path            = data.archive_file.promote_lambda[0].output_path
  lambda_source_hash         = data.archive_file.promote_lambda[0].output_base64sha256
  target_model_package_group = var.model_package_group_name
  deploy_parameter_prefix    = "/${var.name_prefix}/deploy"
  kms_key_arn                = module.kms.key_arn
  enable_event_trigger       = false
  tags                       = var.tags
}

# Central Plane Prod: BU endpoints WITH API Gateway front door.
module "bu_endpoints" {
  source = "../../modules/bu_endpoints"
  count  = var.enable_bu_endpoints ? 1 : 0

  name_prefix           = var.name_prefix
  business_units        = var.business_units
  inference_role_arn    = var.create_iam_roles ? module.iam[0].inference_role_arn : var.inference_role_arn
  subnet_ids            = module.network.subnet_ids
  security_group_ids    = [module.network.sagemaker_security_group_id]
  artifacts_bucket_name = module.storage.artifacts_bucket_name
  kms_key_arn           = module.kms.key_arn
  enable_api_gateway    = true
  enable_waf            = var.enable_waf
  lambda_zip_path       = data.archive_file.invoke_endpoint_lambda[0].output_path
  lambda_source_hash    = data.archive_file.invoke_endpoint_lambda[0].output_base64sha256
  tags                  = var.tags
}
