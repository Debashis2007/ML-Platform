data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id   = var.aws_account_id != "" ? var.aws_account_id : data.aws_caller_identity.current.account_id
  region       = var.aws_region != "" ? var.aws_region : data.aws_region.current.name
  workgroup    = var.athena_workgroup_name != "" ? var.athena_workgroup_name : "${var.name_prefix}-governance"
  export_prefix = "governance-export"
}

resource "aws_s3_bucket" "spill" {
  bucket = var.spill_bucket_name
  tags   = merge(var.tags, { Name = var.spill_bucket_name, Purpose = "athena-spill-governance-export" })
}

resource "aws_s3_bucket_public_access_block" "spill" {
  bucket                  = aws_s3_bucket.spill.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "spill" {
  bucket = aws_s3_bucket.spill.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_arn != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_arn
    }
  }
}

resource "aws_s3_bucket_versioning" "spill" {
  bucket = aws_s3_bucket.spill.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_athena_workgroup" "governance" {
  name = local.workgroup

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    result_configuration {
      output_location = "s3://${aws_s3_bucket.spill.bucket}/athena-results/"

      dynamic "encryption_configuration" {
        for_each = var.kms_key_arn != null ? [1] : []
        content {
          encryption_option = "SSE_KMS"
          kms_key_arn       = var.kms_key_arn
        }
      }

      dynamic "encryption_configuration" {
        for_each = var.kms_key_arn == null ? [1] : []
        content {
          encryption_option = "SSE_S3"
        }
      }
    }
  }

  tags = var.tags
}

resource "aws_glue_catalog_database" "governance" {
  name = var.athena_database_name
}

resource "aws_glue_catalog_table" "stage_governance" {
  name          = "stage_governance"
  database_name = aws_glue_catalog_database.governance.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL              = "TRUE"
    "classification"      = "json"
    "projection.enabled"  = "false"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.spill.bucket}/${local.export_prefix}/"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      name                  = "json"
      serialization_library = "org.openx.data.jsonserde.JsonSerDe"
    }

    columns {
      name = "pk"
      type = "string"
    }
    columns {
      name = "sk"
      type = "string"
    }
    columns {
      name = "model_package_arn"
      type = "string"
    }
    columns {
      name = "approval_status"
      type = "string"
    }
    columns {
      name = "account"
      type = "string"
    }
    columns {
      name = "region"
      type = "string"
    }
    columns {
      name = "business_unit"
      type = "string"
    }
    columns {
      name = "captured_at"
      type = "string"
    }
  }
}

resource "aws_cloudwatch_log_group" "export" {
  name              = "/aws/lambda/${var.name_prefix}-governance-export"
  retention_in_days = 30
  tags              = var.tags
}

data "archive_file" "export" {
  type        = "zip"
  source_file = "${path.module}/lambda/export_governance.py"
  output_path = "${path.module}/build/export_governance.zip"
}

resource "aws_lambda_function" "export" {
  function_name    = "${var.name_prefix}-governance-export"
  role             = var.export_lambda_role_arn
  handler          = "export_governance.handler"
  runtime          = "python3.11"
  timeout          = 120
  memory_size      = 512
  filename         = data.archive_file.export.output_path
  source_code_hash = data.archive_file.export.output_base64sha256

  environment {
    variables = {
      GOVERNANCE_TABLE = var.governance_table_name
      EXPORT_BUCKET    = aws_s3_bucket.spill.bucket
      EXPORT_PREFIX    = local.export_prefix
    }
  }

  depends_on = [aws_cloudwatch_log_group.export]
  tags       = var.tags
}

resource "aws_cloudwatch_event_rule" "export_schedule" {
  name                = "${var.name_prefix}-governance-export"
  description         = "Export Stage Governance DynamoDB rows to S3 for Athena"
  schedule_expression = var.export_schedule_expression
  tags                = var.tags
}

resource "aws_cloudwatch_event_target" "export" {
  rule      = aws_cloudwatch_event_rule.export_schedule.name
  target_id = "GovernanceExport"
  arn       = aws_lambda_function.export.arn
}

resource "aws_lambda_permission" "export_events" {
  statement_id  = "AllowEventBridgeExport"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.export.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.export_schedule.arn
}

resource "aws_athena_named_query" "recent_approvals" {
  name      = "${var.name_prefix}-recent-approvals"
  workgroup = aws_athena_workgroup.governance.id
  database  = aws_glue_catalog_database.governance.name
  query     = <<-SQL
    SELECT pk AS model_package_group, sk AS version, model_package_arn, approval_status,
           business_unit, account, region, captured_at
    FROM ${aws_glue_catalog_database.governance.name}.stage_governance
    WHERE approval_status IS NOT NULL
    ORDER BY captured_at DESC
    LIMIT 100
  SQL
}

# Optional QuickSight Athena datasource (CRBG BI may prefer Power BI → Athena JDBC instead).
resource "aws_quicksight_data_source" "athena" {
  count         = var.quicksight_user_arn != "" ? 1 : 0
  data_source_id = "${var.name_prefix}-governance-athena"
  name           = "${var.name_prefix} Governance Athena"
  type           = "ATHENA"
  aws_account_id = local.account_id

  parameters {
    athena {
      work_group = aws_athena_workgroup.governance.name
    }
  }

  permission {
    actions = [
      "quicksight:DescribeDataSource",
      "quicksight:DescribeDataSourcePermissions",
      "quicksight:PassDataSource",
      "quicksight:UpdateDataSource",
      "quicksight:DeleteDataSource",
      "quicksight:UpdateDataSourcePermissions",
    ]
    principal = var.quicksight_user_arn
  }

  tags = var.tags
}
