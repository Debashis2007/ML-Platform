output "api_endpoint" {
  value = "https://${aws_api_gateway_rest_api.rest.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${aws_api_gateway_stage.prod.stage_name}"
}

output "invoke_url" {
  value = "https://${aws_api_gateway_rest_api.rest.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${aws_api_gateway_stage.prod.stage_name}/invocations"
}

output "lambda_arn" {
  value = aws_lambda_function.invoke.arn
}

output "stage_arn" {
  # Format required by WAFv2 AssociateWebACL for REST APIs:
  # arn:aws:apigateway:region::/restapis/api-id/stages/stage-name
  value = "arn:aws:apigateway:${data.aws_region.current.name}::/restapis/${aws_api_gateway_rest_api.rest.id}/stages/${aws_api_gateway_stage.prod.stage_name}"
}

output "api_id" {
  value = aws_api_gateway_rest_api.rest.id
}

data "aws_region" "current" {}
