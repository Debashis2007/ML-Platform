output "pipeline_log_group_name" {
  value = aws_cloudwatch_log_group.pipeline.name
}

output "evaluation_output_prefix" {
  value = local.evaluation_output_prefix
}

output "pipeline_output_prefix" {
  value = local.pipeline_output_prefix
}

output "ssm_parameter_prefix" {
  value = "/${var.name_prefix}/pipelines/${var.model_name}"
}

output "pipeline_config" {
  description = "Values consumed by ml_platform/build_pipeline.py and GitHub Actions Workflow A."
  value = {
    model_name               = var.model_name
    metric_name              = var.metric_name
    metric_threshold         = var.metric_threshold
    train_instance_type      = var.train_instance_type
    evaluate_instance_type   = var.evaluate_instance_type
    features_enabled         = var.features_enabled
    pipeline_role_arn        = var.pipeline_role_arn
    training_role_arn        = var.training_role_arn
    evaluation_output_prefix = local.evaluation_output_prefix
    model_package_group_name = var.model_package_group_name
    data_bucket_name         = var.data_bucket_name
    artifacts_bucket_name    = var.artifacts_bucket_name
  }
}
