output "governance_table_name" {
  value = aws_dynamodb_table.governance.name
}

output "approval_event_rule_arn" {
  value = aws_cloudwatch_event_rule.model_approved.arn
}

output "capture_lambda_arn" {
  value = aws_lambda_function.capture_approval.arn
}
