output "governance_table_name" {
  value = aws_dynamodb_table.governance.name
}

output "governance_table_arn" {
  value = aws_dynamodb_table.governance.arn
}

output "approval_event_rule_arn" {
  value = aws_cloudwatch_event_rule.model_package_state_change.arn
}

output "capture_lambda_arn" {
  value = aws_lambda_function.capture_approval.arn
}

output "github_dispatch_lambda_arn" {
  value = try(aws_lambda_function.github_dispatch[0].arn, null)
}
