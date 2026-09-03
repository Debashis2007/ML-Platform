locals {
  evaluation_output_prefix = "s3://${var.artifacts_bucket_name}/pipelines/${var.model_name}/evaluation"
  processed_output_prefix  = "s3://${var.artifacts_bucket_name}/pipelines/${var.model_name}/processed"
  pipeline_output_prefix   = "s3://${var.artifacts_bucket_name}/pipelines/${var.model_name}"
}

resource "aws_cloudwatch_log_group" "pipeline" {
  name              = "/aws/sagemaker/pipelines/${var.model_name}"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_ssm_parameter" "metric_name" {
  name  = "/${var.name_prefix}/pipelines/${var.model_name}/metric_name"
  type  = "String"
  value = var.metric_name
  tags  = var.tags
}

resource "aws_ssm_parameter" "metric_threshold" {
  name  = "/${var.name_prefix}/pipelines/${var.model_name}/metric_threshold"
  type  = "String"
  value = tostring(var.metric_threshold)
  tags  = var.tags
}

resource "aws_ssm_parameter" "train_instance_type" {
  name  = "/${var.name_prefix}/pipelines/${var.model_name}/train_instance_type"
  type  = "String"
  value = var.train_instance_type
  tags  = var.tags
}

resource "aws_ssm_parameter" "evaluate_instance_type" {
  name  = "/${var.name_prefix}/pipelines/${var.model_name}/evaluate_instance_type"
  type  = "String"
  value = var.evaluate_instance_type
  tags  = var.tags
}

resource "aws_ssm_parameter" "features_enabled" {
  name  = "/${var.name_prefix}/pipelines/${var.model_name}/features_enabled"
  type  = "String"
  value = tostring(var.features_enabled)
  tags  = var.tags
}

resource "aws_ssm_parameter" "evaluation_output_prefix" {
  name  = "/${var.name_prefix}/pipelines/${var.model_name}/evaluation_output_prefix"
  type  = "String"
  value = local.evaluation_output_prefix
  tags  = var.tags
}

resource "aws_ssm_parameter" "pipeline_role_arn" {
  name  = "/${var.name_prefix}/pipelines/${var.model_name}/pipeline_role_arn"
  type  = "String"
  value = var.pipeline_role_arn
  tags  = var.tags
}

resource "aws_ssm_parameter" "training_role_arn" {
  name  = "/${var.name_prefix}/pipelines/${var.model_name}/training_role_arn"
  type  = "String"
  value = var.training_role_arn
  tags  = var.tags
}

resource "aws_ssm_parameter" "model_package_group" {
  name  = "/${var.name_prefix}/pipelines/${var.model_name}/model_package_group"
  type  = "String"
  value = var.model_package_group_name
  tags  = var.tags
}

resource "aws_s3_object" "evaluation_output_marker" {
  bucket  = var.artifacts_bucket_name
  key     = "pipelines/${var.model_name}/evaluation/.keep"
  content = ""
}

resource "aws_s3_object" "processed_output_marker" {
  count   = var.features_enabled ? 1 : 0
  bucket  = var.artifacts_bucket_name
  key     = "pipelines/${var.model_name}/processed/.keep"
  content = ""
}
