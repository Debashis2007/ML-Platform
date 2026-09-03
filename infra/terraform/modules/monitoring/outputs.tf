output "latency_alarm_arn" {
  value = aws_cloudwatch_metric_alarm.endpoint_latency.arn
}

output "error_alarm_arn" {
  value = aws_cloudwatch_metric_alarm.endpoint_errors.arn
}
