output "pipeline_secret_arn" {
  value = aws_secretsmanager_secret.pipeline.arn
}

output "pipeline_secret_name" {
  value = aws_secretsmanager_secret.pipeline.name
}

output "github_dispatch_secret_arn" {
  value = try(aws_secretsmanager_secret.github_dispatch[0].arn, null)
}
