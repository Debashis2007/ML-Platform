output "latency_alarm_arn" {
  value = aws_cloudwatch_metric_alarm.endpoint_latency.arn
}

output "error_alarm_arn" {
  value = aws_cloudwatch_metric_alarm.endpoint_errors.arn
}

output "monitoring_schedule_name" {
  value = try(aws_sagemaker_monitoring_schedule.data_quality[0].name, null)
}

output "data_quality_job_definition_name" {
  value = try(aws_sagemaker_data_quality_job_definition.this[0].name, null)
}
