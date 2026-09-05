data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  deploy_prefix = var.deploy_parameter_prefix != "" ? var.deploy_parameter_prefix : "/${var.name_prefix}/deploy"
}

resource "aws_iam_role" "promote" {
  name = "${var.name_prefix}-promote-model"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "promote_basic" {
  role       = aws_iam_role.promote.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "promote" {
  name = "${var.name_prefix}-promote-model"
  role = aws_iam_role.promote.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Effect = "Allow"
          Action = [
            "sagemaker:DescribeModelPackage",
            "sagemaker:CreateModelPackage",
            "sagemaker:ListModelPackages",
          ]
          Resource = "*"
        },
        {
          Effect   = "Allow"
          Action   = ["ssm:PutParameter"]
          Resource = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/${var.name_prefix}/deploy/*"
        },
        {
          Effect   = "Allow"
          Action   = ["events:PutEvents"]
          Resource = "arn:aws:events:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:event-bus/default"
        }
      ],
      var.kms_key_arn != null ? [{
        Effect   = "Allow"
        Action   = ["kms:Decrypt", "kms:DescribeKey", "kms:GenerateDataKey"]
        Resource = [var.kms_key_arn]
      }] : []
    )
  })
}

resource "aws_cloudwatch_log_group" "promote" {
  name              = "/aws/lambda/${var.name_prefix}-promote-model"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_lambda_function" "promote" {
  function_name = "${var.name_prefix}-promote-model"
  role          = aws_iam_role.promote.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 60
  memory_size   = 256
  filename      = var.lambda_zip_path
  source_code_hash = var.lambda_source_hash

  environment {
    variables = {
      TARGET_MODEL_PACKAGE_GROUP = var.target_model_package_group
      DEPLOY_PARAMETER_PREFIX    = local.deploy_prefix
      TARGET_APPROVAL_STATUS     = var.target_approval_status
      BUSINESS_UNIT              = var.business_unit
    }
  }

  depends_on = [aws_cloudwatch_log_group.promote]
  tags       = var.tags
}

resource "aws_cloudwatch_event_rule" "model_approved" {
  count       = var.enable_event_trigger ? 1 : 0
  name        = "${var.name_prefix}-promote-on-approved"
  description = "Promote Non-Prod approved packages into Prod registry"
  event_pattern = jsonencode({
    source      = ["ml.platform.governance"]
    detail-type = ["Model Approved"]
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
