data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  deploy_prefix = var.deploy_parameter_prefix != "" ? var.deploy_parameter_prefix : "/${var.name_prefix}/deploy"
}

resource "aws_cloudwatch_log_group" "promote" {
  name              = "/aws/lambda/${var.name_prefix}-promote-model"
  retention_in_days = 365
  tags              = var.tags
}

locals {
  promote_use_image = var.promote_model_image_uri != ""
}

resource "aws_lambda_function" "promote" {
  function_name = "${var.name_prefix}-promote-model"
  role          = var.lambda_role_arn
  timeout       = 60
  memory_size   = 256

  package_type = local.promote_use_image ? "Image" : "Zip"
  image_uri    = local.promote_use_image ? var.promote_model_image_uri : null

  handler          = local.promote_use_image ? null : "handler.lambda_handler"
  runtime          = local.promote_use_image ? null : "python3.11"
  filename         = local.promote_use_image ? null : var.lambda_zip_path
  source_code_hash = local.promote_use_image ? null : var.lambda_source_hash

  environment {
    variables = {
      TARGET_MODEL_PACKAGE_GROUP    = var.target_model_package_group
      DEPLOY_PARAMETER_PREFIX       = local.deploy_prefix
      DECISION_LOG_TABLE            = var.decision_log_table_name
      SOURCE_REGISTRY_READ_ROLE_ARN = var.source_registry_read_role_arn
    }
  }

  depends_on = [aws_cloudwatch_log_group.promote]
  tags       = var.tags
}

# Design v7: promotion is requested by the release workflow after the image digest is
# copied into Prod ECR; it records the request and never creates an Approved package.
resource "aws_cloudwatch_event_rule" "model_approved" {
  count       = var.enable_event_trigger ? 1 : 0
  name        = "${var.name_prefix}-promote-requested"
  description = "Promotion requests (prod_image_uri + source package)"
  event_pattern = jsonencode({
    source      = ["ml.platform.release"]
    detail-type = ["Promotion Request"]
  })
  tags = var.tags
}

resource "aws_cloudwatch_event_target" "promote" {
  count     = var.enable_event_trigger ? 1 : 0
  rule      = aws_cloudwatch_event_rule.model_approved[0].name
  target_id = "PromoteModel"
  arn       = aws_lambda_function.promote.arn
}

resource "aws_lambda_permission" "events" {
  count         = var.enable_event_trigger ? 1 : 0
  statement_id  = "AllowEventBridgePromote"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.promote.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.model_approved[0].arn
}
