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

  default_tags {
    tags = {
      bu      = var.bu
      project = var.project
      version = var.platform_version
    }
  }
}

data "archive_file" "capture_approval_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../../../../lambdas/capture_approval_event"
  output_path = "${path.module}/.build/capture_approval.zip"
}

data "archive_file" "github_dispatch_lambda" {
  count       = var.enable_auto_deploy ? 1 : 0
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

  name_prefix          = var.name_prefix
  vpc_id               = var.vpc_id
  subnet_ids           = var.subnet_ids
  plane                = "control_plane"
  enable_vpc_endpoints = var.enable_vpc_endpoints
  tags                 = var.tags
}

module "storage" {
  source = "../../modules/storage"

  name_prefix                          = var.name_prefix
  data_bucket_name                     = var.data_bucket_name
  dev_artifacts_bucket_name            = var.dev_artifacts_bucket_name
  artifacts_bucket_name                = var.artifacts_bucket_name
  ecr_repository_name                  = var.ecr_repository_name
  platform_lambdas_ecr_repository_name = var.platform_lambdas_ecr_repository_name
  model_ids                            = var.model_ids
  ecr_pull_account_ids                 = var.deployment_account_ids
  break_glass_principal_arns           = var.break_glass_principal_arns
  kms_key_arn                          = module.kms.key_arn
  tags                                 = var.tags
}

module "secrets" {
  source = "../../modules/secrets"

  name_prefix           = var.name_prefix
  kms_key_arn           = module.kms.key_arn
  github_dispatch_token = var.github_dispatch_token
  tags                  = var.tags
}

# IAM roles are client-managed — see docs/CLIENT_MANAGED_IAM_ROLES.md

module "registry" {
  source = "../../modules/registry"

  model_package_group_name = var.model_package_group_name
  description              = "ML NonProd model registry"
  spoke_account_ids        = var.spoke_account_ids
  tags                     = var.tags
}

module "sns" {
  source = "../../modules/sns"

  name_prefix = var.name_prefix
  kms_key_arn = module.kms.key_arn
  tags        = var.tags
}

module "governance" {
  source = "../../modules/governance"

  name_prefix                     = var.name_prefix
  model_package_group_name        = ""
  lambda_source_dir               = "${path.module}/.build"
  deploy_parameter_prefix         = "/${var.name_prefix}/deploy"
  kms_key_arn                     = module.kms.key_arn
  artefact_bucket_name            = module.storage.artefact_store_bucket_name
  evidence_bucket_name            = module.storage.evidence_bucket_name
  training_account_ids            = var.training_account_ids
  spoke_account_ids               = var.training_account_ids
  source_read_role_name           = var.source_read_role_name
  lambda_subnet_ids               = module.network.subnet_ids
  lambda_security_group_ids       = [module.network.sagemaker_security_group_id]
  alarm_actions                   = [module.sns.alerts_topic_arn]
  violation_topic_arn             = module.sns.alerts_topic_arn
  enable_auto_deploy              = var.enable_auto_deploy
  github_owner                    = var.github_owner
  github_repo                     = var.github_repo
  github_token_secret_arn         = coalesce(module.secrets.github_dispatch_secret_arn, "")
  governance_lambda_role_arn      = var.governance_lambda_role_arn
  registration_lambda_role_arn    = var.registration_lambda_role_arn
  github_dispatch_lambda_role_arn = var.github_dispatch_lambda_role_arn
  capture_approval_image_uri      = module.platform_lambda_uris.capture_approval
  register_candidate_image_uri    = module.platform_lambda_uris.register_candidate
  github_dispatch_image_uri       = module.platform_lambda_uris.github_dispatch
  tags                            = var.tags

  depends_on = [
    data.archive_file.capture_approval_lambda,
    data.archive_file.github_dispatch_lambda,
  ]
}

module "management_api" {
  source = "../../modules/management_api"
  count  = var.enable_management_api ? 1 : 0

  name_prefix                = var.name_prefix
  vpc_endpoint_ids           = compact([module.network.execute_api_vpc_endpoint_id])
  okta_issuer                = var.okta_issuer
  okta_audience              = var.okta_audience
  okta_authorizer_image_uri  = module.platform_lambda_uris.okta_authorizer
  approval_api_image_uri     = module.platform_lambda_uris.approval_api
  authorizer_lambda_role_arn = var.authorizer_lambda_role_arn
  approval_lambda_role_arn   = var.approval_lambda_role_arn
  lifecycle_table_name       = module.governance.lifecycle_table_name
  decision_log_table_name    = module.governance.decision_log_table_name
  identity_table_name        = module.governance.identity_table_name
  locks_table_name           = module.governance.locks_table_name
  waf_web_acl_arn            = var.waf_web_acl_arn
  lambda_subnet_ids          = module.network.subnet_ids
  lambda_security_group_ids  = [module.network.sagemaker_security_group_id]
  alarm_actions              = [module.sns.alerts_topic_arn]
  tags                       = var.tags
}

module "credit_risk_pipeline" {
  source = "../../modules/evaluation-pipeline"

  name_prefix              = var.name_prefix
  model_name               = "credit-risk"
  pipeline_role_arn        = var.pipeline_role_arn
  training_role_arn        = var.training_role_arn
  artifacts_bucket_name    = module.storage.artifacts_bucket_name
  data_bucket_name         = module.storage.data_bucket_name
  model_package_group_name = module.registry.model_package_group_name
  metric_name              = "auc"
  metric_threshold         = 0.75
  train_instance_type      = "ml.m5.xlarge"
  evaluate_instance_type   = "ml.m5.xlarge"
  features_enabled         = false
  tags                     = var.tags
}

module "cloudwatch" {
  source = "../../modules/cloudwatch"

  name_prefix    = var.name_prefix
  pipeline_names = ["demo-credit-risk"]
  tags           = var.tags
}

module "stage_analytics" {
  source = "../../modules/stage_analytics"

  name_prefix                 = var.name_prefix
  governance_table_name       = module.governance.governance_table_name
  governance_table_arn        = module.governance.governance_table_arn
  kms_key_arn                 = module.kms.key_arn
  spill_bucket_name           = var.athena_spill_bucket_name
  export_lambda_role_arn      = var.stage_export_lambda_role_arn
  governance_export_image_uri = module.platform_lambda_uris.governance_export
  quicksight_user_arn         = var.quicksight_user_arn
  tags                        = var.tags
}
