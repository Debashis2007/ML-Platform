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
  source_dir  = "${path.module}/../../../lambdas/invoke_endpoint"
  output_path = "${path.module}/.build/invoke_endpoint.zip"
}

module "network" {
  source = "../../modules/network"

  name_prefix = var.name_prefix
  vpc_id      = var.vpc_id
  subnet_ids  = var.subnet_ids
  tags        = var.tags
}

module "sns" {
  source = "../../modules/sns"

  name_prefix = var.name_prefix
  tags        = var.tags
}

module "endpoint" {
  source = "../../modules/endpoint"

  name_prefix        = var.name_prefix
  model_package_arn  = var.model_package_arn
  endpoint_name      = var.endpoint_name
  inference_role_arn = var.inference_role_arn
  subnet_ids         = module.network.subnet_ids
  security_group_ids = [module.network.sagemaker_security_group_id]
  instance_type      = var.instance_type
  instance_count     = var.instance_count
  enable_multi_az    = var.enable_multi_az
  tags               = var.tags
}

module "api_gateway" {
  source = "../../modules/api_gateway"

  name_prefix        = var.name_prefix
  endpoint_name      = module.endpoint.endpoint_name
  lambda_zip_path    = data.archive_file.invoke_endpoint_lambda.output_path
  lambda_source_hash = data.archive_file.invoke_endpoint_lambda.output_base64sha256
  tags               = var.tags
}

module "monitoring" {
  source = "../../modules/monitoring"

  name_prefix   = var.name_prefix
  endpoint_name = module.endpoint.endpoint_name
  alarm_actions = [module.sns.alerts_topic_arn]
  tags          = var.tags
}

module "cloudwatch" {
  source = "../../modules/cloudwatch"

  name_prefix   = var.name_prefix
  endpoint_name = module.endpoint.endpoint_name
  tags          = var.tags
}
