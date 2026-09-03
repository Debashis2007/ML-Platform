output "log_group_name" {
  value = aws_cloudwatch_log_group.sagemaker.name
}

output "dashboard_name" {
  value = aws_cloudwatch_dashboard.platform.dashboard_name
}
