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

# Applied in the deployment target account (BU NonProd for QA, BU Prod for LIVE).
provider "aws" {
  region = var.aws_region

  dynamic "assume_role" {
    for_each = var.target_role_arn != "" ? [1] : []
    content {
      role_arn     = var.target_role_arn
      session_name = "ml-release-${var.release_id}"
    }
  }

  default_tags {
    tags = {
      bu          = coalesce(var.bu, var.business_unit, "unassigned")
      project     = var.project
      version     = var.platform_version
      environment = var.environment
    }
  }
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
  plane                = "bu"
  enable_vpc_endpoints = var.enable_vpc_endpoints
  interface_services = var.enable_api_gateway ? [
    "ecr.api", "ecr.dkr", "sagemaker.api", "sagemaker.runtime", "sts", "logs", "events", "lambda", "execute-api",
  ] : null
  tags = var.tags
}

module "sns" {
  source = "../../modules/sns"

  name_prefix = var.name_prefix
  kms_key_arn = var.kms_key_arn
  tags        = var.tags
}

module "endpoint" {
  source = "../../modules/endpoint"

  name_prefix             = var.name_prefix
  model_package_arn       = var.model_package_arn
  endpoint_name           = var.endpoint_name
  environment             = var.environment
  release_id              = var.release_id
  inference_role_arn      = var.inference_role_arn
  subnet_ids              = module.network.subnet_ids
  security_group_ids      = [module.network.sagemaker_security_group_id]
  instance_type           = var.instance_type
  instance_count          = var.instance_count
  max_instance_count      = var.max_instance_count
  alarm_actions           = concat([module.sns.alerts_topic_arn], var.alarm_actions)
  enable_data_capture     = var.enable_data_capture && local.data_capture_uri != ""
  data_capture_s3_uri     = local.data_capture_uri
  data_capture_percentage = var.data_capture_percentage
  kms_key_id              = var.kms_key_arn
  tags                    = var.tags
}

module "api_gateway_account" {
  source = "../../modules/api_gateway_account"
  count  = var.enable_api_gateway ? 1 : 0

  cloudwatch_role_arn = var.apigateway_cloudwatch_role_arn
}

module "api_gateway" {
  source = "../../modules/api_gateway"
  count  = var.enable_api_gateway ? 1 : 0

  name_prefix               = var.name_prefix
  endpoint_name             = module.endpoint.endpoint_name
  endpoint_arn              = module.endpoint.endpoint_arn
  lambda_zip_path           = data.archive_file.invoke_endpoint_lambda.output_path
  lambda_source_hash        = data.archive_file.invoke_endpoint_lambda.output_base64sha256
  invoke_endpoint_image_uri = module.platform_lambda_uris.invoke_endpoint
  lambda_role_arn           = var.invoke_lambda_role_arn
  endpoint_type             = "PRIVATE"
  vpc_endpoint_ids          = compact([module.network.execute_api_vpc_endpoint_id])
  enable_iam_auth           = var.enable_api_iam_auth
  tags                      = var.tags

  depends_on = [module.api_gateway_account]
}

resource "aws_wafv2_web_acl_association" "invoke_api" {
  count        = var.enable_api_gateway && var.waf_web_acl_arn != "" ? 1 : 0
  resource_arn = module.api_gateway[0].stage_arn
  web_acl_arn  = var.waf_web_acl_arn
}

module "monitoring" {
  source = "../../modules/monitoring"

  name_prefix                 = var.name_prefix
  endpoint_name               = module.endpoint.endpoint_name
  alarm_actions               = [module.sns.alerts_topic_arn]
  enable_model_monitor        = var.enable_model_monitor
  monitoring_role_arn         = var.monitoring_role_arn != "" ? var.monitoring_role_arn : var.inference_role_arn
  baseline_constraints_s3_uri = var.baseline_constraints_s3_uri
  baseline_statistics_s3_uri  = var.baseline_statistics_s3_uri
  data_capture_s3_uri         = local.data_capture_uri
  monitoring_output_s3_uri    = var.monitoring_output_s3_uri
  monitoring_image_uri        = var.monitoring_image_uri
  tags                        = var.tags
}

module "cloudwatch" {
  source = "../../modules/cloudwatch"

  name_prefix   = var.name_prefix
  endpoint_name = module.endpoint.endpoint_name
  tags          = var.tags
}
