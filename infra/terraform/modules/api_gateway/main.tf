resource "aws_cloudwatch_log_group" "invoke" {
  name              = "/aws/lambda/${var.name_prefix}-invoke-endpoint"
  retention_in_days = 30
  tags              = var.tags
}

locals {
  invoke_use_image = var.invoke_endpoint_image_uri != ""
}

resource "aws_lambda_function" "invoke" {
  function_name = "${var.name_prefix}-invoke-endpoint"
  role          = var.lambda_role_arn
  timeout       = 30
  memory_size   = 256

  package_type = local.invoke_use_image ? "Image" : "Zip"
  image_uri    = local.invoke_use_image ? var.invoke_endpoint_image_uri : null

  handler          = local.invoke_use_image ? null : "handler.handler"
  runtime          = local.invoke_use_image ? null : "python3.11"
  filename         = local.invoke_use_image ? null : var.lambda_zip_path
  source_code_hash = local.invoke_use_image ? null : var.lambda_source_hash

  environment {
    variables = {
      ENDPOINT_NAME = var.endpoint_name
      MODEL_VERSION = var.model_version
    }
  }

  depends_on = [aws_cloudwatch_log_group.invoke]
  tags       = var.tags
}

# REST API (WAFv2-compatible). IAM role for Lambda is client-managed (lambda_role_arn).
locals {
  is_private = var.endpoint_type == "PRIVATE"
}

data "aws_iam_policy_document" "private" {
  count = local.is_private ? 1 : 0

  statement {
    actions   = ["execute-api:Invoke"]
    resources = ["execute-api:/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
  }

  statement {
    effect    = "Deny"
    actions   = ["execute-api:Invoke"]
    resources = ["execute-api:/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "StringNotEquals"
      variable = "aws:SourceVpce"
      values   = var.vpc_endpoint_ids
    }
  }
}

resource "aws_api_gateway_rest_api" "rest" {
  name        = "${var.name_prefix}-${var.endpoint_name}-api"
  description = "Invoke API for ${var.endpoint_name}"
  policy      = local.is_private ? data.aws_iam_policy_document.private[0].json : null

  endpoint_configuration {
    types            = [var.endpoint_type]
    vpc_endpoint_ids = local.is_private ? var.vpc_endpoint_ids : null
  }

  lifecycle {
    precondition {
      condition     = !local.is_private || length(var.vpc_endpoint_ids) > 0
      error_message = "PRIVATE APIs need at least one execute-api VPC endpoint."
    }
  }

  tags = var.tags
}

resource "aws_api_gateway_resource" "invocations" {
  rest_api_id = aws_api_gateway_rest_api.rest.id
  parent_id   = aws_api_gateway_rest_api.rest.root_resource_id
  path_part   = "invocations"
}

resource "aws_api_gateway_method" "invocations_post" {
  rest_api_id   = aws_api_gateway_rest_api.rest.id
  resource_id   = aws_api_gateway_resource.invocations.id
  http_method   = "POST"
  authorization = var.enable_iam_auth ? "AWS_IAM" : "NONE"
}

resource "aws_api_gateway_integration" "lambda" {
  rest_api_id             = aws_api_gateway_rest_api.rest.id
  resource_id             = aws_api_gateway_resource.invocations.id
  http_method             = aws_api_gateway_method.invocations_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.invoke.invoke_arn
}

resource "aws_cloudwatch_log_group" "api" {
  count             = var.enable_access_logs ? 1 : 0
  name              = "/aws/apigateway/${var.name_prefix}-${var.endpoint_name}"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_api_gateway_deployment" "this" {
  rest_api_id = aws_api_gateway_rest_api.rest.id

  triggers = {
    redeploy = sha1(jsonencode([
      aws_api_gateway_resource.invocations.id,
      aws_api_gateway_method.invocations_post.id,
      aws_api_gateway_integration.lambda.id,
      var.enable_iam_auth,
      aws_api_gateway_rest_api.rest.policy,
    ]))
  }

  lifecycle { create_before_destroy = true }

  depends_on = [aws_api_gateway_integration.lambda]
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.this.id
  rest_api_id   = aws_api_gateway_rest_api.rest.id
  stage_name    = "prod"
  tags          = var.tags

  dynamic "access_log_settings" {
    for_each = var.enable_access_logs ? [1] : []
    content {
      destination_arn = aws_cloudwatch_log_group.api[0].arn
      format = jsonencode({
        requestId      = "$context.requestId"
        ip             = "$context.identity.sourceIp"
        requestTime    = "$context.requestTime"
        httpMethod     = "$context.httpMethod"
        resourcePath   = "$context.resourcePath"
        status         = "$context.status"
        protocol       = "$context.protocol"
        responseLength = "$context.responseLength"
        errorMessage   = "$context.error.message"
      })
    }
  }

  xray_tracing_enabled = true
}

resource "aws_api_gateway_method_settings" "all" {
  rest_api_id = aws_api_gateway_rest_api.rest.id
  stage_name  = aws_api_gateway_stage.prod.stage_name
  method_path = "*/*"

  settings {
    metrics_enabled        = true
    logging_level          = var.enable_access_logs ? "INFO" : "OFF"
    data_trace_enabled     = false
    throttling_burst_limit = var.throttling_burst_limit
    throttling_rate_limit  = var.throttling_rate_limit
  }
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.invoke.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.rest.execution_arn}/*/POST/invocations"
}

resource "aws_cloudwatch_metric_alarm" "invoke_errors" {
  alarm_name          = "${var.name_prefix}-invoke-endpoint-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  dimensions = {
    FunctionName = aws_lambda_function.invoke.function_name
  }
  tags = var.tags
}
