resource "aws_iam_role" "lambda" {
  name = "${var.name_prefix}-invoke-endpoint"
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

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_invoke" {
  name = "${var.name_prefix}-invoke-endpoint"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sagemaker:InvokeEndpoint"]
      Resource = var.endpoint_arn != "" ? [var.endpoint_arn] : ["*"]
    }]
  })
}

resource "aws_cloudwatch_log_group" "invoke" {
  name              = "/aws/lambda/${var.name_prefix}-invoke-endpoint"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_lambda_function" "invoke" {
  function_name = "${var.name_prefix}-invoke-endpoint"
  role          = aws_iam_role.lambda.arn
  handler       = "handler.handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 256
  filename      = var.lambda_zip_path
  source_code_hash = var.lambda_source_hash

  environment {
    variables = {
      ENDPOINT_NAME = var.endpoint_name
      MODEL_VERSION = var.model_version
    }
  }

  depends_on = [aws_cloudwatch_log_group.invoke]
  tags       = var.tags
}

resource "aws_apigatewayv2_api" "http" {
  name          = "${var.name_prefix}-${var.endpoint_name}-api"
  protocol_type = "HTTP"
  tags          = var.tags
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.invoke.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "invocations" {
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "POST /invocations"
  target             = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorization_type = var.enable_iam_auth ? "AWS_IAM" : "NONE"
}

resource "aws_cloudwatch_log_group" "api" {
  count             = var.enable_access_logs ? 1 : 0
  name              = "/aws/apigateway/${var.name_prefix}-${var.endpoint_name}"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true
  tags        = var.tags

  dynamic "access_log_settings" {
    for_each = var.enable_access_logs ? [1] : []
    content {
      destination_arn = aws_cloudwatch_log_group.api[0].arn
      format = jsonencode({
        requestId      = "$context.requestId"
        ip             = "$context.identity.sourceIp"
        requestTime    = "$context.requestTime"
        httpMethod     = "$context.httpMethod"
        routeKey       = "$context.routeKey"
        status         = "$context.status"
        protocol       = "$context.protocol"
        responseLength = "$context.responseLength"
        errorMessage   = "$context.error.message"
      })
    }
  }
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.invoke.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
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
