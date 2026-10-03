# Private management API (design v7): the only approval path.
# PRIVATE REST API reachable through the execute-api VPC endpoint, Okta TOKEN authorizer
# (Cognito is not used), approval routes backed by the approval Lambda. WAF attaches
# through waf_web_acl_arn so the protection product can be swapped without code changes.

data "aws_region" "current" {}

module "authorizer" {
  source = "../platform_function"

  function_name      = "${var.name_prefix}-okta-authorizer"
  description        = "Okta JWT TOKEN authorizer for the management API"
  role_arn           = var.authorizer_lambda_role_arn
  image_uri          = var.okta_authorizer_image_uri
  source_dir         = "${path.module}/../../../../lambdas/okta_authorizer"
  require_image      = true
  timeout            = 10
  subnet_ids         = var.lambda_subnet_ids
  security_group_ids = var.lambda_security_group_ids
  alarm_actions      = var.alarm_actions
  environment = {
    OKTA_ISSUER    = var.okta_issuer
    OKTA_AUDIENCE  = var.okta_audience
    REQUIRED_SCOPE = var.okta_required_scope
  }
  tags = var.tags
}

module "approval" {
  source = "../platform_function"

  function_name      = "${var.name_prefix}-approval-api"
  description        = "Approve/reject model packages: identity, separation of duties, lock, hash binding"
  role_arn           = var.approval_lambda_role_arn
  image_uri          = var.approval_api_image_uri
  source_dir         = "${path.module}/../../../../lambdas/approval_api"
  timeout            = 30
  subnet_ids         = var.lambda_subnet_ids
  security_group_ids = var.lambda_security_group_ids
  alarm_actions      = var.alarm_actions
  environment = {
    LIFECYCLE_TABLE    = var.lifecycle_table_name
    DECISION_LOG_TABLE = var.decision_log_table_name
    IDENTITY_TABLE     = var.identity_table_name
    LOCKS_TABLE        = var.locks_table_name
    LOCK_TTL_SECONDS   = tostring(var.lock_ttl_seconds)
  }
  tags = var.tags
}

data "aws_iam_policy_document" "private_api" {
  statement {
    sid       = "AllowFromManagementVpce"
    actions   = ["execute-api:Invoke"]
    resources = ["execute-api:/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
  }

  statement {
    sid       = "DenyOutsideManagementVpce"
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

resource "aws_api_gateway_rest_api" "this" {
  name        = "${var.name_prefix}-management-api"
  description = "ML management API (private)"
  policy      = data.aws_iam_policy_document.private_api.json

  endpoint_configuration {
    types            = ["PRIVATE"]
    vpc_endpoint_ids = var.vpc_endpoint_ids
  }

  lifecycle {
    precondition {
      condition     = length(var.vpc_endpoint_ids) > 0
      error_message = "The private management API needs at least one execute-api VPC endpoint."
    }
  }

  tags = var.tags
}

resource "aws_api_gateway_authorizer" "okta" {
  name                             = "okta"
  rest_api_id                      = aws_api_gateway_rest_api.this.id
  type                             = "TOKEN"
  authorizer_uri                   = module.authorizer.invoke_arn
  identity_source                  = "method.request.header.Authorization"
  identity_validation_expression   = "^Bearer [-0-9a-zA-Z._~+/]+=*$"
  authorizer_result_ttl_in_seconds = 0
}

resource "aws_api_gateway_resource" "approvals" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  parent_id   = aws_api_gateway_rest_api.this.root_resource_id
  path_part   = "approvals"
}

resource "aws_api_gateway_method" "approvals" {
  for_each = toset(["GET", "POST"])

  rest_api_id   = aws_api_gateway_rest_api.this.id
  resource_id   = aws_api_gateway_resource.approvals.id
  http_method   = each.value
  authorization = "CUSTOM"
  authorizer_id = aws_api_gateway_authorizer.okta.id
}

resource "aws_api_gateway_integration" "approvals" {
  for_each = aws_api_gateway_method.approvals

  rest_api_id             = aws_api_gateway_rest_api.this.id
  resource_id             = aws_api_gateway_resource.approvals.id
  http_method             = each.value.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.approval.invoke_arn
}

resource "aws_api_gateway_deployment" "this" {
  rest_api_id = aws_api_gateway_rest_api.this.id

  triggers = {
    redeploy = sha1(jsonencode([
      aws_api_gateway_rest_api.this.policy,
      aws_api_gateway_authorizer.okta.id,
      [for m in aws_api_gateway_method.approvals : m.id],
      [for i in aws_api_gateway_integration.approvals : i.id],
    ]))
  }

  lifecycle { create_before_destroy = true }
}

resource "aws_cloudwatch_log_group" "access" {
  name              = "/aws/apigateway/${var.name_prefix}-management-api"
  retention_in_days = 365
  tags              = var.tags
}

resource "aws_api_gateway_stage" "v1" {
  deployment_id        = aws_api_gateway_deployment.this.id
  rest_api_id          = aws_api_gateway_rest_api.this.id
  stage_name           = "v1"
  xray_tracing_enabled = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.access.arn
    format = jsonencode({
      requestId    = "$context.requestId"
      sourceVpce   = "$context.identity.vpceId"
      principal    = "$context.authorizer.principalId"
      email        = "$context.authorizer.email"
      httpMethod   = "$context.httpMethod"
      resourcePath = "$context.resourcePath"
      status       = "$context.status"
      requestTime  = "$context.requestTime"
      errorMessage = "$context.error.message"
    })
  }

  tags = var.tags
}

resource "aws_api_gateway_method_settings" "all" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  stage_name  = aws_api_gateway_stage.v1.stage_name
  method_path = "*/*"

  settings {
    metrics_enabled        = true
    logging_level          = "INFO"
    data_trace_enabled     = false
    throttling_burst_limit = 20
    throttling_rate_limit  = 10
  }
}

resource "aws_lambda_permission" "authorizer" {
  statement_id  = "AllowAPIGatewayAuthorizer"
  action        = "lambda:InvokeFunction"
  function_name = module.authorizer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.this.execution_arn}/authorizers/${aws_api_gateway_authorizer.okta.id}"
}

resource "aws_lambda_permission" "approval" {
  statement_id  = "AllowAPIGatewayApprovals"
  action        = "lambda:InvokeFunction"
  function_name = module.approval.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.this.execution_arn}/*/*/approvals"
}

# Replaceable protection hook (e.g. the enterprise WAF product). Empty = not attached.
resource "aws_wafv2_web_acl_association" "this" {
  count        = var.waf_web_acl_arn != "" ? 1 : 0
  resource_arn = aws_api_gateway_stage.v1.arn
  web_acl_arn  = var.waf_web_acl_arn
}
