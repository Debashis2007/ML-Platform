terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
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
  tags                      = var.tags
}

module "sns" {
  source = "../../modules/sns"

  name_prefix = var.name_prefix
  tags        = var.tags
}

module "credit_risk_pipeline_prod" {
  source = "../../modules/evaluation-pipeline"

  name_prefix              = var.name_prefix
  model_name               = "credit-risk-prod"
  pipeline_role_arn        = var.pipeline_role_arn
  training_role_arn        = var.training_role_arn
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
  pipeline_role_arn = var.pipeline_role_arn
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
