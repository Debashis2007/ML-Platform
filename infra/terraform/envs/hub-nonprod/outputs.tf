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

output "sagemaker_security_group_id" {
  value = module.network.sagemaker_security_group_id
}
