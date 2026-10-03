output "api_id" {
  value = aws_api_gateway_rest_api.this.id
}

output "invoke_url" {
  description = "Private URL; resolves only through the execute-api VPC endpoint."
  value       = "https://${aws_api_gateway_rest_api.this.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${aws_api_gateway_stage.v1.stage_name}"
}

output "stage_arn" {
  value = aws_api_gateway_stage.v1.arn
}

output "approval_lambda_arn" {
  value = module.approval.arn
}

output "authorizer_lambda_arn" {
  value = module.authorizer.arn
}
