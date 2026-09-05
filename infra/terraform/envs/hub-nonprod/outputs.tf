output "pipeline_role_arn" {
  value = module.iam.pipeline_role_arn
}

output "training_role_arn" {
  value = module.iam.training_role_arn
}

output "inference_role_arn" {
  value = module.iam.inference_role_arn
}

output "gha_pipeline_role_arn" {
  value = module.iam.gha_pipeline_role_arn
}

output "gha_deploy_role_arn" {
  value = module.iam.gha_deploy_role_arn
}

output "data_bucket_name" {
  value = module.storage.data_bucket_name
}

output "dev_artifacts_bucket_name" {
  value = module.storage.dev_artifacts_bucket_name
}

output "artifacts_bucket_name" {
  value = module.storage.artifacts_bucket_name
}

output "ecr_repository_url" {
  value = module.storage.ecr_repository_url
}

output "model_package_group_arn" {
  value = module.registry.model_package_group_arn
}

output "credit_risk_pipeline_config" {
  value = module.credit_risk_pipeline.pipeline_config
}

output "pipeline_trigger_arn" {
  value = module.pipeline_trigger.state_machine_arn
}

output "pipeline_secret_arn" {
  value = module.secrets.pipeline_secret_arn
}

output "cloudwatch_dashboard_name" {
  value = module.cloudwatch.dashboard_name
}

output "sagemaker_security_group_id" {
  value = module.network.sagemaker_security_group_id
}

output "kms_key_arn" {
  value = module.kms.key_arn
}

output "sns_alerts_topic_arn" {
  value = module.sns.alerts_topic_arn
}

output "github_dispatch_secret_arn" {
  value = module.secrets.github_dispatch_secret_arn
}

output "github_dispatch_lambda_arn" {
  value = module.governance.github_dispatch_lambda_arn
}

output "athena_workgroup_name" {
  value = module.stage_analytics.athena_workgroup_name
}

output "athena_jdbc_hint" {
  value = module.stage_analytics.athena_jdbc_hint
}

output "bu_endpoint_names" {
  value = try(module.bu_endpoints[0].endpoint_names, {})
}
