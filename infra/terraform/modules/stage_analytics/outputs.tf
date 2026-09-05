output "spill_bucket_name" {
  value = aws_s3_bucket.spill.bucket
}

output "spill_bucket_arn" {
  value = aws_s3_bucket.spill.arn
}

output "athena_workgroup_name" {
  value = aws_athena_workgroup.governance.name
}

output "athena_database_name" {
  value = aws_glue_catalog_database.governance.name
}

output "glue_table_name" {
  value = aws_glue_catalog_table.stage_governance.name
}

output "export_lambda_arn" {
  value = aws_lambda_function.export.arn
}

output "quicksight_data_source_arn" {
  value = try(aws_quicksight_data_source.athena[0].arn, null)
}

output "athena_jdbc_hint" {
  value = "jdbc:awsathena://AwsRegion=${local.region};S3OutputLocation=s3://${aws_s3_bucket.spill.bucket}/athena-results/;Workgroup=${aws_athena_workgroup.governance.name}"
  description = "Connection hint for Power BI / JDBC clients (CRBG BI dependency)."
}
