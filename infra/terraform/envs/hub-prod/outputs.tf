output "prod_data_bucket_name" {
  value = module.storage.prod_data_bucket_name
}

output "sns_alerts_topic_arn" {
  value = module.sns.alerts_topic_arn
}

output "deploy_trigger_arn" {
  value = module.deploy_trigger.state_machine_arn
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
  value = local.pipeline_role_arn
}

output "training_role_arn" {
  value = local.training_role_arn
}

output "gha_pipeline_role_arn" {
  value = try(module.iam[0].gha_pipeline_role_arn, null)
}

output "gha_deploy_role_arn" {
  value = try(module.iam[0].gha_deploy_role_arn, null)
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

output "bu_endpoint_names" {
  value = try(module.bu_endpoints[0].endpoint_names, {})
}

output "bu_api_invoke_urls" {
  value = try(module.bu_endpoints[0].api_invoke_urls, {})
}
