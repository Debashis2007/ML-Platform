resource "aws_s3_bucket" "data" {
  bucket = var.data_bucket_name
  tags   = merge(var.tags, { Name = var.data_bucket_name })
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy       = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_arn != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_arn
    }
  }
}

resource "aws_s3_bucket" "artifacts" {
  bucket = var.artifacts_bucket_name
  tags   = merge(var.tags, { Name = var.artifacts_bucket_name })
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy       = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_arn != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_arn
    }
  }
}

resource "aws_ecr_repository" "models" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }

  dynamic "encryption_configuration" {
    for_each = var.kms_key_arn != null ? [1] : []
    content {
      encryption_type = "KMS"
      kms_key         = var.kms_key_arn
    }
  }

  tags = merge(var.tags, { Name = var.ecr_repository_name })
}

resource "aws_s3_bucket" "dev_artifacts" {
  bucket = var.dev_artifacts_bucket_name
  tags   = merge(var.tags, { Name = var.dev_artifacts_bucket_name, Layer = "dev-artifacts" })
}

resource "aws_s3_bucket_versioning" "dev_artifacts" {
  bucket = aws_s3_bucket.dev_artifacts.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_public_access_block" "dev_artifacts" {
  bucket                  = aws_s3_bucket.dev_artifacts.id
  block_public_acls       = true
  block_public_policy       = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "dev_artifacts" {
  bucket = aws_s3_bucket.dev_artifacts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_arn != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_arn
    }
  }
}

resource "aws_s3_bucket" "prod_data" {
  count  = var.prod_data_bucket_name != null ? 1 : 0
  bucket = var.prod_data_bucket_name
  tags   = merge(var.tags, { Name = var.prod_data_bucket_name, Layer = "prod-data" })
}

resource "aws_s3_bucket_versioning" "prod_data" {
  count  = length(aws_s3_bucket.prod_data) > 0 ? 1 : 0
  bucket = aws_s3_bucket.prod_data[0].id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_public_access_block" "prod_data" {
  count                   = length(aws_s3_bucket.prod_data) > 0 ? 1 : 0
  bucket                  = aws_s3_bucket.prod_data[0].id
  block_public_acls       = true
  block_public_policy       = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "prod_data" {
  count  = length(aws_s3_bucket.prod_data) > 0 ? 1 : 0
  bucket = aws_s3_bucket.prod_data[0].id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_arn != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_arn
    }
  }
}
