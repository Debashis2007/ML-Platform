data "aws_caller_identity" "current" {}

resource "aws_dynamodb_table" "governance" {
  name         = "${var.name_prefix}-model-governance"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "model_package_arn"

  attribute {
    name = "model_package_arn"
    type = "S"
  }

  tags = var.tags
}

resource "aws_cloudwatch_event_rule" "model_approved" {
  name        = "${var.name_prefix}-model-approved"
  description = "Fires when a model package version is approved in SageMaker Registry"
  event_pattern = jsonencode({
    source      = ["aws.sagemaker"]
    detail-type = ["SageMaker Model Package State Change"]
    detail = {
      ModelPackageGroupName = [var.model_package_group_name]
      ModelApprovalStatus   = ["Approved"]
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

resource "aws_lambda_function" "capture_approval" {
  function_name = "${var.name_prefix}-capture-approval"
  role          = aws_iam_role.governance_lambda.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30

  filename         = var.lambda_source_dir != "" ? "${var.lambda_source_dir}/capture_approval.zip" : "${path.module}/build/capture_approval.zip"
  source_code_hash = var.lambda_source_dir != "" ? filebase64sha256("${var.lambda_source_dir}/capture_approval.zip") : filebase64sha256("${path.module}/build/capture_approval.zip")

  environment {
    variables = {
      GOVERNANCE_TABLE = aws_dynamodb_table.governance.name
    }
  }

  tags = var.tags
}

resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.model_approved.name
  target_id = "CaptureApproval"
  arn       = aws_lambda_function.capture_approval.arn
}

resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.capture_approval.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.model_approved.arn
}
