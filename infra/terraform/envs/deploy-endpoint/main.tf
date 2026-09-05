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

data "archive_file" "invoke_endpoint_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../../../../lambdas/invoke_endpoint"
  output_path = "${path.module}/.build/invoke_endpoint.zip"
}

locals {
  data_capture_uri = var.data_capture_s3_uri != "" ? var.data_capture_s3_uri : (
    var.artifacts_bucket_name != "" ? "s3://${var.artifacts_bucket_name}/data-capture/${var.endpoint_name}" : ""
  )
}

module "network" {
  source = "../../modules/network"

  name_prefix          = var.name_prefix
  vpc_id               = var.vpc_id
  subnet_ids           = var.subnet_ids
  enable_vpc_endpoints = var.enable_vpc_endpoints
  tags                 = var.tags
}

module "sns" {
  source = "../../modules/sns"

  name_prefix = var.name_prefix
  kms_key_arn = var.kms_key_arn
  tags        = var.tags
}

module "endpoint" {
  source = "../../modules/endpoint"

  name_prefix           = var.name_prefix
  model_package_arn     = var.model_package_arn
  endpoint_name         = var.endpoint_name
  inference_role_arn    = var.inference_role_arn
  subnet_ids            = module.network.subnet_ids
  security_group_ids    = [module.network.sagemaker_security_group_id]
  instance_type         = var.instance_type
  instance_count        = var.instance_count
  enable_multi_az       = var.enable_multi_az
  enable_data_capture   = var.enable_data_capture && local.data_capture_uri != ""
  data_capture_s3_uri   = local.data_capture_uri
  data_capture_percentage = var.data_capture_percentage
  kms_key_id            = var.kms_key_arn
  tags                  = var.tags
}

module "api_gateway_account" {
  source = "../../modules/api_gateway_account"
  count  = var.enable_api_gateway ? 1 : 0

  cloudwatch_role_arn = var.apigateway_cloudwatch_role_arn
}

module "api_gateway" {
  source = "../../modules/api_gateway"
  count  = var.enable_api_gateway ? 1 : 0

  name_prefix        = var.name_prefix
  endpoint_name      = module.endpoint.endpoint_name
  endpoint_arn       = module.endpoint.endpoint_arn
  lambda_zip_path    = data.archive_file.invoke_endpoint_lambda.output_path
  lambda_source_hash = data.archive_file.invoke_endpoint_lambda.output_base64sha256
  lambda_role_arn    = var.invoke_lambda_role_arn
  enable_iam_auth    = var.enable_api_iam_auth
  tags               = var.tags

  depends_on = [module.api_gateway_account]
}

module "waf" {
  source = "../../modules/waf"
  count  = var.enable_api_gateway && var.enable_waf ? 1 : 0

  name_prefix   = var.name_prefix
  rate_limit    = var.waf_rate_limit
  resource_arns = [module.api_gateway[0].stage_arn]
  tags          = var.tags
}

module "monitoring" {
  source = "../../modules/monitoring"

  name_prefix                  = var.name_prefix
  endpoint_name                = module.endpoint.endpoint_name
  alarm_actions                = [module.sns.alerts_topic_arn]
  enable_model_monitor         = var.enable_model_monitor
  monitoring_role_arn          = var.monitoring_role_arn != "" ? var.monitoring_role_arn : var.inference_role_arn
  baseline_constraints_s3_uri  = var.baseline_constraints_s3_uri
  baseline_statistics_s3_uri   = var.baseline_statistics_s3_uri
  data_capture_s3_uri          = local.data_capture_uri
  monitoring_output_s3_uri     = var.monitoring_output_s3_uri
  monitoring_image_uri         = var.monitoring_image_uri
  tags                         = var.tags
}

module "cloudwatch" {
  source = "../../modules/cloudwatch"

  name_prefix   = var.name_prefix
  endpoint_name = module.endpoint.endpoint_name
  tags          = var.tags
}
