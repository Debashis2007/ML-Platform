data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_dynamodb_table" "governance" {
  name         = "${var.name_prefix}-model-governance"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  tags = var.tags
}

resource "aws_cloudwatch_event_rule" "model_package_state_change" {
  name        = "${var.name_prefix}-model-package-state"
  description = "Fires on SageMaker Model Package approval status changes"
  event_pattern = jsonencode({
    source      = ["aws.sagemaker"]
    detail-type = ["SageMaker Model Package State Change"]
    detail = {
      ModelPackageGroupName = [var.model_package_group_name]
      ModelApprovalStatus   = ["Approved", "Rejected", "PendingManualApproval"]
    }
  })
  tags = var.tags
}

resource "aws_iam_role" "governance_lambda" {
  name = "${var.name_prefix}-governance-lambda"
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

resource "aws_iam_role_policy_attachment" "governance_lambda_basic" {
  role       = aws_iam_role.governance_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "governance_lambda_ddb" {
  name = "${var.name_prefix}-governance-ddb"
  role = aws_iam_role.governance_lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:GetItem"]
      Resource = aws_dynamodb_table.governance.arn
    }]
  })
}

resource "aws_cloudwatch_log_group" "capture_approval" {
  name              = "/aws/lambda/${var.name_prefix}-capture-approval"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_lambda_function" "capture_approval" {
  function_name = "${var.name_prefix}-capture-approval"
  role          = aws_iam_role.governance_lambda.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 256

  filename         = var.lambda_source_dir != "" ? "${var.lambda_source_dir}/capture_approval.zip" : "${path.module}/build/capture_approval.zip"
  source_code_hash = var.lambda_source_dir != "" ? filebase64sha256("${var.lambda_source_dir}/capture_approval.zip") : filebase64sha256("${path.module}/build/capture_approval.zip")

  environment {
    variables = {
      GOVERNANCE_TABLE        = aws_dynamodb_table.governance.name
      DEPLOY_PARAMETER_PREFIX = var.deploy_parameter_prefix != "" ? var.deploy_parameter_prefix : "/${var.name_prefix}/deploy"
    }
  }

  depends_on = [aws_cloudwatch_log_group.capture_approval]
  tags       = var.tags
}

resource "aws_iam_role_policy" "governance_lambda_extras" {
  name = "${var.name_prefix}-governance-extras"
  role = aws_iam_role.governance_lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
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
      var.kms_key_arn != null ? [
        {
          Effect   = "Allow"
          Action   = ["kms:Decrypt", "kms:DescribeKey", "kms:GenerateDataKey"]
          Resource = [var.kms_key_arn]
        }
      ] : []
    )
  })
}

resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.model_package_state_change.name
  target_id = "CaptureApproval"
  arn       = aws_lambda_function.capture_approval.arn
}

resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.capture_approval.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.model_package_state_change.arn
}

resource "aws_cloudwatch_metric_alarm" "governance_lambda_errors" {
  alarm_name          = "${var.name_prefix}-governance-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  dimensions = {
    FunctionName = aws_lambda_function.capture_approval.function_name
  }
  tags = var.tags
}

# --- Auto-deploy: Model Approved → GitHub repository_dispatch ---

resource "aws_cloudwatch_event_rule" "model_approved_deploy" {
  count       = var.enable_auto_deploy ? 1 : 0
  name        = "${var.name_prefix}-model-approved-deploy"
  description = "Triggers GitHub deploy workflow on Model Approved"
  event_pattern = jsonencode({
    source      = ["ml.platform.governance"]
    detail-type = ["Model Approved"]
  })
  tags = var.tags
}

resource "aws_iam_role" "github_dispatch_lambda" {
  count = var.enable_auto_deploy ? 1 : 0
  name  = "${var.name_prefix}-github-dispatch"
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

resource "aws_iam_role_policy_attachment" "github_dispatch_basic" {
  count      = var.enable_auto_deploy ? 1 : 0
  role       = aws_iam_role.github_dispatch_lambda[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "github_dispatch_secrets" {
  count = var.enable_auto_deploy ? 1 : 0
  name  = "${var.name_prefix}-github-dispatch-secrets"
  role  = aws_iam_role.github_dispatch_lambda[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Effect   = "Allow"
          Action   = ["secretsmanager:GetSecretValue"]
          Resource = [var.github_token_secret_arn]
        }
      ],
      var.kms_key_arn != null ? [
        {
          Effect   = "Allow"
          Action   = ["kms:Decrypt", "kms:DescribeKey"]
          Resource = [var.kms_key_arn]
        }
      ] : []
    )
  })
}

resource "aws_cloudwatch_log_group" "github_dispatch" {
  count             = var.enable_auto_deploy ? 1 : 0
  name              = "/aws/lambda/${var.name_prefix}-github-dispatch"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_lambda_function" "github_dispatch" {
  count         = var.enable_auto_deploy ? 1 : 0
  function_name = "${var.name_prefix}-github-dispatch"
  role          = aws_iam_role.github_dispatch_lambda[0].arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 256

  filename         = "${var.lambda_source_dir}/github_dispatch.zip"
  source_code_hash = filebase64sha256("${var.lambda_source_dir}/github_dispatch.zip")

  environment {
    variables = {
      GITHUB_OWNER            = var.github_owner
      GITHUB_REPO             = var.github_repo
      GITHUB_TOKEN_SECRET_ARN = var.github_token_secret_arn
    }
  }

  depends_on = [aws_cloudwatch_log_group.github_dispatch]
  tags       = var.tags
}

resource "aws_cloudwatch_event_target" "github_dispatch" {
  count     = var.enable_auto_deploy ? 1 : 0
  rule      = aws_cloudwatch_event_rule.model_approved_deploy[0].name
  target_id = "GitHubDispatch"
  arn       = aws_lambda_function.github_dispatch[0].arn
}

resource "aws_lambda_permission" "github_dispatch_events" {
  count         = var.enable_auto_deploy ? 1 : 0
  statement_id  = "AllowEventBridgeGitHubDispatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.github_dispatch[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.model_approved_deploy[0].arn
}
