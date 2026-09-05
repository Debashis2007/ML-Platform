resource "aws_sagemaker_model" "this" {
  name               = "${var.name_prefix}-${var.endpoint_name}-model"
  execution_role_arn = var.inference_role_arn

  primary_container {
    model_package_name = var.model_package_arn
  }

  vpc_config {
    subnets            = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  tags = var.tags
}

resource "aws_sagemaker_endpoint_configuration" "this" {
  name = "${var.name_prefix}-${var.endpoint_name}-config"

  production_variants {
    variant_name           = "AllTraffic"
    model_name             = aws_sagemaker_model.this.name
    initial_instance_count = var.enable_multi_az ? max(var.instance_count, 2) : var.instance_count
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

  tags = var.tags
}

resource "aws_sagemaker_endpoint" "this" {
  name                 = var.endpoint_name
  endpoint_config_name = aws_sagemaker_endpoint_configuration.this.name
  tags                 = var.tags
}
