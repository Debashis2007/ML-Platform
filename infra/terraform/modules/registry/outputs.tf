output "model_package_group_name" {
  value = aws_sagemaker_model_package_group.this.model_package_group_name
}

output "model_package_group_arn" {
  value = aws_sagemaker_model_package_group.this.arn
}

output "recommended_life_cycle_stages" {
  description = "Model Registry staging construct (applied via ModelLifeCycle on packages)."
  value = {
    nonprod_register = { Stage = "Development", StageStatus = "PendingApproval" }
    promote_prod     = { Stage = "Production", StageStatus = "Approved" }
  }
}
