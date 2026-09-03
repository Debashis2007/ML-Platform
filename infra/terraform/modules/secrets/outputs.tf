output "pipeline_secret_arn" {
  value = aws_secretsmanager_secret.pipeline.arn
}

output "pipeline_secret_name" {
  value = aws_secretsmanager_secret.pipeline.name
}
