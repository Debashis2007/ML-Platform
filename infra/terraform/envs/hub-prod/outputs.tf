output "prod_data_bucket_name" {
  value = module.storage.prod_data_bucket_name
}

output "sns_alerts_topic_arn" {
  value = module.sns.alerts_topic_arn
}

output "prod_pipeline_config" {
  value = module.credit_risk_pipeline_prod.pipeline_config
}

output "kms_key_arn" {
  value = module.kms.key_arn
}

output "pipeline_secret_arn" {
  value = module.secrets.pipeline_secret_arn
}

output "ecr_repository_url" {
  value = module.storage.ecr_repository_url
}

output "pipeline_role_arn" {
  value       = var.pipeline_role_arn
  description = "Client-managed (passed through)."
}

output "training_role_arn" {
  value       = var.training_role_arn
  description = "Client-managed (passed through)."
}

output "github_dispatch_lambda_arn" {
  value = try(module.governance[0].github_dispatch_lambda_arn, null)
}

output "promote_lambda_arn" {
  value = try(module.promote[0].promote_lambda_arn, null)
}

output "athena_workgroup_name" {
  value = try(module.stage_analytics[0].athena_workgroup_name, null)
}

output "athena_jdbc_hint" {
  value = try(module.stage_analytics[0].athena_jdbc_hint, null)
}

output "management_api_url" {
  value = try(module.management_api[0].invoke_url, null)
}

output "artefact_store_bucket_name" {
  value = module.storage.artefact_store_bucket_name
}

output "model_ecr_repository_urls" {
  value = module.storage.model_ecr_repository_urls
}
