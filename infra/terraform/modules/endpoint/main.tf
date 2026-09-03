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

  tags = var.tags
}

resource "aws_sagemaker_endpoint" "this" {
  name                 = var.endpoint_name
  endpoint_config_name = aws_sagemaker_endpoint_configuration.this.name
  tags                 = var.tags
}
