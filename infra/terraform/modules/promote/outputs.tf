output "promote_lambda_arn" {
  value = aws_lambda_function.promote.arn
}

output "promote_lambda_name" {
  value = aws_lambda_function.promote.function_name
}

output "deploy_parameter_prefix" {
  value = local.deploy_prefix
}
