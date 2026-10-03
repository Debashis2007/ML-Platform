# Endpoint release (design v7), applied in the deployment target account.
#
# Every release gets a unique model and endpoint configuration (release_id), and the
# endpoint moves to it with a blue/green deployment:
#   QA    ALL_AT_ONCE
#   LIVE  CANARY 10% of capacity, 15-minute bake, then full shift
# Rollback alarms (5xx, latency) are created here and wired into auto-rollback; a
# release without them is refused. Application Auto Scaling is the only writer of the
# running instance count.

locals {
  is_live      = var.environment == "live"
  release_name = substr("${var.endpoint_name}-${var.release_id}", 0, 63)
  variant_name = "AllTraffic"
  rollback_alarm_names = concat(
    [aws_cloudwatch_metric_alarm.rollback_5xx.alarm_name, aws_cloudwatch_metric_alarm.rollback_latency.alarm_name],
    var.extra_rollback_alarm_names,
  )
}

resource "aws_sagemaker_model" "this" {
  name               = local.release_name
  execution_role_arn = var.inference_role_arn

  primary_container {
    model_package_name = var.model_package_arn
  }

  vpc_config {
    subnets            = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  enable_network_isolation = var.enable_network_isolation

  tags = merge(var.tags, { release_id = var.release_id, environment = var.environment })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_sagemaker_endpoint_configuration" "this" {
  name = local.release_name

  production_variants {
    variant_name           = local.variant_name
    model_name             = aws_sagemaker_model.this.name
    initial_instance_count = var.instance_count
    instance_type          = var.instance_type
  }

  dynamic "data_capture_config" {
    for_each = var.enable_data_capture && var.data_capture_s3_uri != "" ? [1] : []
    content {
      enable_capture              = true
      initial_sampling_percentage = var.data_capture_percentage
      destination_s3_uri          = var.data_capture_s3_uri
      kms_key_id                  = var.kms_key_id

      capture_options {
        capture_mode = "Input"
      }
      capture_options {
        capture_mode = "Output"
      }

      capture_content_type_header {
        json_content_types = ["application/json"]
      }
    }
  }

  kms_key_arn = var.kms_key_id

  tags = merge(var.tags, { release_id = var.release_id, environment = var.environment })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_cloudwatch_metric_alarm" "rollback_5xx" {
  alarm_name          = "${var.endpoint_name}-rollback-5xx"
  alarm_description   = "Blue/green auto-rollback: endpoint 5xx errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  metric_name         = "Invocation5XXErrors"
  namespace           = "AWS/SageMaker"
  period              = 60
  statistic           = "Sum"
  threshold           = var.rollback_5xx_threshold
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_actions
  dimensions          = { EndpointName = var.endpoint_name, VariantName = local.variant_name }
  tags                = var.tags
}

resource "aws_cloudwatch_metric_alarm" "rollback_latency" {
  alarm_name          = "${var.endpoint_name}-rollback-latency"
  alarm_description   = "Blue/green auto-rollback: p99 model latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  datapoints_to_alarm = 3
  metric_name         = "ModelLatency"
  namespace           = "AWS/SageMaker"
  period              = 60
  extended_statistic  = "p99"
  threshold           = var.rollback_latency_p99_ms * 1000
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_actions
  dimensions          = { EndpointName = var.endpoint_name, VariantName = local.variant_name }
  tags                = var.tags
}

resource "aws_sagemaker_endpoint" "this" {
  name                 = var.endpoint_name
  endpoint_config_name = aws_sagemaker_endpoint_configuration.this.name

  deployment_config {
    blue_green_update_policy {
      traffic_routing_configuration {
        type                     = local.is_live ? "CANARY" : "ALL_AT_ONCE"
        wait_interval_in_seconds = local.is_live ? var.live_canary_wait_seconds : var.qa_wait_seconds

        dynamic "canary_size" {
          for_each = local.is_live ? [1] : []
          content {
            type  = "CAPACITY_PERCENT"
            value = var.live_canary_percent
          }
        }
      }
      termination_wait_in_seconds          = var.termination_wait_seconds
      maximum_execution_timeout_in_seconds = var.maximum_execution_timeout_seconds
    }

    auto_rollback_configuration {
      dynamic "alarms" {
        for_each = toset(local.rollback_alarm_names)
        content {
          alarm_name = alarms.value
        }
      }
    }
  }

  tags = merge(var.tags, { environment = var.environment })

  lifecycle {
    precondition {
      condition     = !local.is_live || var.instance_count >= 2
      error_message = "LIVE endpoints require at least two instances."
    }
    precondition {
      condition     = length(local.rollback_alarm_names) > 0
      error_message = "A release without rollback alarms is refused."
    }
    precondition {
      condition     = !local.is_live || (var.live_canary_percent == 10 && var.live_canary_wait_seconds >= 900)
      error_message = "LIVE releases use a 10% canary with at least a 15-minute bake."
    }
  }
}

resource "aws_appautoscaling_target" "variant" {
  count              = var.enable_autoscaling ? 1 : 0
  service_namespace  = "sagemaker"
  resource_id        = "endpoint/${aws_sagemaker_endpoint.this.name}/variant/${local.variant_name}"
  scalable_dimension = "sagemaker:variant:DesiredInstanceCount"
  min_capacity       = var.instance_count
  max_capacity       = max(var.max_instance_count, var.instance_count)
}

resource "aws_appautoscaling_policy" "invocations" {
  count              = var.enable_autoscaling ? 1 : 0
  name               = "${var.endpoint_name}-invocations-per-instance"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.variant[0].service_namespace
  resource_id        = aws_appautoscaling_target.variant[0].resource_id
  scalable_dimension = aws_appautoscaling_target.variant[0].scalable_dimension

  target_tracking_scaling_policy_configuration {
    target_value       = var.target_invocations_per_instance
    scale_in_cooldown  = 300
    scale_out_cooldown = 60

    predefined_metric_specification {
      predefined_metric_type = "SageMakerVariantInvocationsPerInstance"
    }
  }
}
