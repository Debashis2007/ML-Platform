output "pipeline_role_arn" {
  value       = var.pipeline_role_arn
  description = "Client-managed SageMaker pipeline role ARN (passed through)."
}

output "training_role_arn" {
  value       = var.training_role_arn
  description = "Client-managed SageMaker training role ARN (passed through)."
}

output "inference_role_arn" {
  value       = var.inference_role_arn
  description = "Client-managed SageMaker inference role ARN (passed through)."
}

output "artifacts_bucket_name" {
  value = module.storage.artifacts_bucket_name
}

output "data_bucket_name" {
  value = module.storage.data_bucket_name
}

output "ecr_repository_url" {
  value = module.storage.ecr_repository_url
}

output "model_package_group_name" {
  value = module.registry.model_package_group_name
}

output "kms_key_arn" {
  value = module.kms.key_arn
}

output "governance_table_name" {
  value = module.governance.governance_table_name
}

output "decision_log_table_name" {
  value = module.governance.decision_log_table_name
}

output "lifecycle_table_name" {
  value = module.governance.lifecycle_table_name
}

output "artefact_store_bucket_name" {
  value = module.storage.artefact_store_bucket_name
}

output "evidence_bucket_name" {
  value = module.storage.evidence_bucket_name
}

output "model_ecr_repository_urls" {
  value = module.storage.model_ecr_repository_urls
}

output "management_api_url" {
  value = try(module.management_api[0].invoke_url, null)
}

output "hub_event_bus_arn" {
  value = module.governance.hub_event_bus_arn
}
