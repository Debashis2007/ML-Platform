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

locals {
  model_monitor_enabled = (
    var.enable_model_monitor
    && var.monitoring_role_arn != ""
    && var.baseline_constraints_s3_uri != ""
    && var.baseline_statistics_s3_uri != ""
    && var.data_capture_s3_uri != ""
    && var.monitoring_output_s3_uri != ""
    && var.monitoring_image_uri != ""
  )
}

resource "aws_sagemaker_data_quality_job_definition" "this" {
  count = local.model_monitor_enabled ? 1 : 0
  name  = "${var.name_prefix}-${var.endpoint_name}-data-quality"

  data_quality_app_specification {
    image_uri = var.monitoring_image_uri
  }

  data_quality_job_input {
    endpoint_input {
      endpoint_name = var.endpoint_name
      local_path    = "/opt/ml/processing/input/endpoint"
    }
  }

  data_quality_job_output_config {
    monitoring_outputs {
      s3_output {
        s3_uri        = var.monitoring_output_s3_uri
        local_path    = "/opt/ml/processing/output"
        s3_upload_mode = "EndOfJob"
      }
    }
  }

  data_quality_baseline_config {
    constraints_resource {
      s3_uri = var.baseline_constraints_s3_uri
    }
    statistics_resource {
      s3_uri = var.baseline_statistics_s3_uri
    }
  }

  job_resources {
    cluster_config {
      instance_count    = 1
      instance_type     = var.monitoring_instance_type
      volume_size_in_gb = 30
    }
  }

  role_arn = var.monitoring_role_arn
  tags     = var.tags
}

resource "aws_sagemaker_monitoring_schedule" "data_quality" {
  count = local.model_monitor_enabled ? 1 : 0
  name  = "${var.name_prefix}-${var.endpoint_name}-dq-schedule"

  monitoring_schedule_config {
    monitoring_job_definition_name = aws_sagemaker_data_quality_job_definition.this[0].name
    schedule_config {
      schedule_expression = var.schedule_expression
    }
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "model_monitor_failures" {
  count               = local.model_monitor_enabled ? 1 : 0
  alarm_name          = "${var.name_prefix}-${var.endpoint_name}-monitor-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "MonitoringScheduleFailed"
  namespace           = "AWS/SageMaker"
  period              = 3600
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Model Monitor schedule failures"
  alarm_actions       = var.alarm_actions
  treat_missing_data  = "notBreaching"

  dimensions = {
    MonitoringScheduleName = aws_sagemaker_monitoring_schedule.data_quality[0].name
  }

  tags = var.tags
}
