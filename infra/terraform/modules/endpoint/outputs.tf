output "endpoint_name" {
  value = aws_sagemaker_endpoint.this.name
}

output "endpoint_arn" {
  value = aws_sagemaker_endpoint.this.arn
}

output "endpoint_config_name" {
  value = aws_sagemaker_endpoint_configuration.this.name
}

output "model_name" {
  value = aws_sagemaker_model.this.name
}

output "rollback_alarm_names" {
  value = local.rollback_alarm_names
}

output "latency_alarm_arn" {
  value = aws_cloudwatch_metric_alarm.rollback_latency.arn
}

output "error_alarm_arn" {
  value = aws_cloudwatch_metric_alarm.rollback_5xx.arn
}
