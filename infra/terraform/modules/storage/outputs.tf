output "data_bucket_name" {
  value = aws_s3_bucket.data.id
}

output "data_bucket_arn" {
  value = aws_s3_bucket.data.arn
}

output "artifacts_bucket_name" {
  value = aws_s3_bucket.artifacts.id
}

output "artifacts_bucket_arn" {
  value = aws_s3_bucket.artifacts.arn
}

output "dev_artifacts_bucket_name" {
  value = aws_s3_bucket.dev_artifacts.id
}

output "dev_artifacts_bucket_arn" {
  value = aws_s3_bucket.dev_artifacts.arn
}

output "prod_data_bucket_name" {
  value = try(aws_s3_bucket.prod_data[0].id, null)
}

output "ecr_repository_name" {
  value = aws_ecr_repository.models.name
}

output "ecr_repository_url" {
  value = aws_ecr_repository.models.repository_url
}

output "ecr_repository_arn" {
  value = aws_ecr_repository.models.arn
}
