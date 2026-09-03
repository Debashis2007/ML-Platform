resource "aws_cloudwatch_metric_alarm" "endpoint_latency" {
  alarm_name          = "${var.name_prefix}-${var.endpoint_name}-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "ModelLatency"
  namespace           = "AWS/SageMaker"
  period              = 300
  statistic           = "Average"
  threshold           = var.latency_threshold_ms
  alarm_description   = "SageMaker endpoint model latency"
  alarm_actions       = var.alarm_actions

  dimensions = {
    EndpointName = var.endpoint_name
    VariantName  = "AllTraffic"
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "endpoint_errors" {
  alarm_name          = "${var.name_prefix}-${var.endpoint_name}-5xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Invocation5XXErrors"
  namespace           = "AWS/SageMaker"
  period              = 300
  statistic           = "Sum"
  threshold           = var.error_rate_threshold
  alarm_description   = "SageMaker endpoint 5xx errors"
  alarm_actions       = var.alarm_actions

  dimensions = {
    EndpointName = var.endpoint_name
    VariantName  = "AllTraffic"
  }

  tags = var.tags
}
