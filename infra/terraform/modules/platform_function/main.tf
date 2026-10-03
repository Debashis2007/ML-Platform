# Platform Lambda: container image from platform-infra CI, or zip of source_dir as fallback.
# The execution role is client-managed and passed in by ARN.

terraform {
  required_providers {
    aws     = { source = "hashicorp/aws", version = ">= 5.0" }
    archive = { source = "hashicorp/archive", version = ">= 2.4" }
  }
}

locals {
  use_image = var.image_uri != ""
}

data "archive_file" "zip" {
  count       = local.use_image ? 0 : 1
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.root}/.build/${var.function_name}.zip"
  excludes    = ["Dockerfile", "__pycache__", "requirements.txt"]
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn
  tags              = var.tags
}

resource "aws_lambda_function" "this" {
  function_name = var.function_name
  description   = var.description
  role          = var.role_arn
  timeout       = var.timeout
  memory_size   = var.memory_size

  package_type = local.use_image ? "Image" : "Zip"
  image_uri    = local.use_image ? var.image_uri : null

  handler          = local.use_image ? null : "handler.lambda_handler"
  runtime          = local.use_image ? null : "python3.11"
  filename         = local.use_image ? null : data.archive_file.zip[0].output_path
  source_code_hash = local.use_image ? null : data.archive_file.zip[0].output_base64sha256

  environment {
    variables = var.environment
  }

  dynamic "vpc_config" {
    for_each = length(var.subnet_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = var.security_group_ids
    }
  }

  tracing_config {
    mode = "Active"
  }

  lifecycle {
    precondition {
      condition     = local.use_image || !var.require_image
      error_message = "${var.function_name} has third-party dependencies and must be deployed from a container image (image_uri)."
    }
  }

  depends_on = [aws_cloudwatch_log_group.this]
  tags       = var.tags
}

resource "aws_cloudwatch_metric_alarm" "errors" {
  alarm_name          = "${var.function_name}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_actions
  dimensions          = { FunctionName = aws_lambda_function.this.function_name }
  tags                = var.tags
}
