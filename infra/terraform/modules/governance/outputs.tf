output "table_names" {
  value = { for k, t in aws_dynamodb_table.this : k => t.name }
}

output "table_arns" {
  value = { for k, t in aws_dynamodb_table.this : k => t.arn }
}

output "lifecycle_table_name" {
  value = aws_dynamodb_table.this["lifecycle"].name
}

output "decision_log_table_name" {
  value = aws_dynamodb_table.this["decision_log"].name
}

output "identity_table_name" {
  value = aws_dynamodb_table.this["identity"].name
}

output "locks_table_name" {
  value = aws_dynamodb_table.this["locks"].name
}

# Stage analytics exports the decision log.
output "governance_table_name" {
  value = aws_dynamodb_table.this["decision_log"].name
}

output "governance_table_arn" {
  value = aws_dynamodb_table.this["decision_log"].arn
}

output "hub_event_bus_arn" {
  value = aws_cloudwatch_event_bus.hub.arn
}

output "approval_event_rule_arn" {
  value = aws_cloudwatch_event_rule.model_package_state_change.arn
}

output "capture_lambda_arn" {
  value = aws_lambda_function.capture_approval.arn
}

output "register_candidate_lambda_arn" {
  value = module.register_candidate.arn
}

output "github_dispatch_lambda_arn" {
  value = try(aws_lambda_function.github_dispatch[0].arn, null)
}
