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
  type        = "zip"
  source_dir  = "${path.module}/../../../lambdas/capture_approval_event"
  output_path = "${path.module}/.build/capture_approval.zip"
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
  ecr_repository_name       = var.ecr_repository_name
  tags                      = var.tags
}

module "secrets" {
  source = "../../modules/secrets"

  name_prefix = var.name_prefix
  tags        = var.tags
}

module "iam" {
  source = "../../modules/iam"

  name_prefix              = var.name_prefix
  data_bucket_arn          = module.storage.data_bucket_arn
  artifacts_bucket_arn     = module.storage.artifacts_bucket_arn
  ecr_repository_arn       = module.storage.ecr_repository_arn
  github_oidc_provider_arn = var.github_oidc_provider_arn
  github_repo_subjects     = var.github_repo_subjects
  tags                     = var.tags
}

module "registry" {
  source = "../../modules/registry"

  model_package_group_name = var.model_package_group_name
  description              = "ML Platform shared model registry"
  spoke_account_ids        = var.spoke_account_ids
  tags                     = var.tags
}

module "governance" {
  source = "../../modules/governance"

  name_prefix              = var.name_prefix
  model_package_group_name = var.model_package_group_name
  lambda_source_dir        = "${path.module}/.build"
  deploy_parameter_prefix  = "/${var.name_prefix}/deploy"
  tags                     = var.tags
}

module "credit_risk_pipeline" {
  source = "../../modules/evaluation-pipeline"

  name_prefix              = var.name_prefix
  model_name               = "credit-risk"
  pipeline_role_arn        = module.iam.pipeline_role_arn
  training_role_arn        = module.iam.training_role_arn
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

module "pipeline_trigger" {
  source = "../../modules/step_functions"

  name_prefix       = var.name_prefix
  pipeline_name     = "credit-risk"
  pipeline_role_arn = module.iam.pipeline_role_arn
  tags              = var.tags
}

module "cloudwatch" {
  source = "../../modules/cloudwatch"

  name_prefix    = var.name_prefix
  pipeline_names = ["credit-risk"]
  tags           = var.tags
}

module "dev_test_endpoint" {
  source = "../../modules/endpoint"
  count  = var.create_dev_test_endpoint ? 1 : 0

  name_prefix        = var.name_prefix
  model_package_arn  = var.dev_test_model_package_arn
  endpoint_name      = "${var.name_prefix}-credit-risk-test"
  inference_role_arn = module.iam.inference_role_arn
  subnet_ids         = module.network.subnet_ids
  security_group_ids = [module.network.sagemaker_security_group_id]
  instance_type      = "ml.m5.large"
  instance_count     = 1
  tags               = var.tags
}
