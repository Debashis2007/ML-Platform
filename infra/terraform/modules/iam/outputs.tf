output "pipeline_role_arn" {
  value = aws_iam_role.pipeline.arn
}

output "training_role_arn" {
  value = aws_iam_role.training.arn
}

output "inference_role_arn" {
  value = aws_iam_role.inference.arn
}

output "gha_pipeline_role_arn" {
  value = try(aws_iam_role.gha_pipeline[0].arn, null)
}

output "gha_deploy_role_arn" {
  value = try(aws_iam_role.gha_deploy[0].arn, null)
}
