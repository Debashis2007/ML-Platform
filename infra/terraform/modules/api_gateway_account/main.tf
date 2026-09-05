# Account-level CloudWatch role is client-managed. This module only associates it.

resource "aws_api_gateway_account" "this" {
  cloudwatch_role_arn = var.cloudwatch_role_arn
}
