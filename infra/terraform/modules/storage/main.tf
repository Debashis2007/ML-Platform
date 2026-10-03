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
  block_public_policy     = true
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
  block_public_policy     = true
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

resource "aws_ecr_repository" "platform_lambdas" {
  name                 = var.platform_lambdas_ecr_repository_name
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }

  dynamic "encryption_configuration" {
    for_each = var.kms_key_arn != null ? [1] : []
    content {
      encryption_type = "KMS"
      kms_key         = var.kms_key_arn
    }
  }

  tags = merge(var.tags, { Name = var.platform_lambdas_ecr_repository_name, Layer = "platform-lambdas" })
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
  block_public_policy     = true
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
  block_public_policy     = true
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

# --- Design v7: control-plane Object Lock stores and per-model ECR ---
#
# snapshots   immutable training-data snapshots referenced by lineage
# artefacts   model.tar.gz copied in by the registration Lambda (checksum verified)
# evidence    candidate manifests and metrics bound to each registration
# All three use Object Lock GOVERNANCE mode. Deletes, retention changes and governance
# bypass are denied to everyone except the break-glass principals.

data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  locked_buckets = {
    snapshots = coalesce(var.snapshot_bucket_name, "${var.name_prefix}-${local.account_id}-snapshots")
    artefacts = coalesce(var.artefact_store_bucket_name, "${var.name_prefix}-${local.account_id}-artefacts")
    evidence  = coalesce(var.evidence_bucket_name, "${var.name_prefix}-${local.account_id}-evidence")
  }
}

resource "aws_s3_bucket" "locked" {
  for_each = local.locked_buckets

  bucket              = each.value
  object_lock_enabled = true
  tags                = merge(var.tags, { Name = each.value, Layer = each.key, ObjectLock = "GOVERNANCE" })
}

resource "aws_s3_bucket_versioning" "locked" {
  for_each = aws_s3_bucket.locked
  bucket   = each.value.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_object_lock_configuration" "locked" {
  for_each = aws_s3_bucket.locked
  bucket   = each.value.id

  rule {
    default_retention {
      mode = "GOVERNANCE"
      days = var.object_lock_retention_days
    }
  }

  depends_on = [aws_s3_bucket_versioning.locked]
}

resource "aws_s3_bucket_public_access_block" "locked" {
  for_each                = aws_s3_bucket.locked
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "locked" {
  for_each = aws_s3_bucket.locked
  bucket   = each.value.id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "locked" {
  for_each = aws_s3_bucket.locked
  bucket   = each.value.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_arn != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = var.kms_key_arn != null
  }
}

data "aws_iam_policy_document" "locked" {
  for_each = aws_s3_bucket.locked

  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [each.value.arn, "${each.value.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  statement {
    sid    = "DenyDeleteAndRetentionChangesExceptBreakGlass"
    effect = "Deny"
    actions = [
      "s3:DeleteObject",
      "s3:DeleteObjectVersion",
      "s3:BypassGovernanceRetention",
      "s3:PutObjectRetention",
      "s3:PutBucketObjectLockConfiguration",
      "s3:PutLifecycleConfiguration",
    ]
    resources = [each.value.arn, "${each.value.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    dynamic "condition" {
      for_each = length(var.break_glass_principal_arns) > 0 ? [1] : []
      content {
        test     = "ArnNotLike"
        variable = "aws:PrincipalArn"
        values   = var.break_glass_principal_arns
      }
    }
  }
}

resource "aws_s3_bucket_policy" "locked" {
  for_each = aws_s3_bucket.locked
  bucket   = each.value.id
  policy   = data.aws_iam_policy_document.locked[each.key].json

  # Later retention changes need a break-glass principal; the policy denies everyone else.
  depends_on = [aws_s3_bucket_public_access_block.locked, aws_s3_bucket_object_lock_configuration.locked]
}

# Pipeline run outputs are staging only; registered artefacts live in the artefact store.
resource "aws_s3_bucket_lifecycle_configuration" "artifacts_staging" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    id     = "expire-pipeline-staging"
    status = "Enabled"
    filter {
      prefix = var.staging_prefix
    }
    expiration {
      days = var.staging_expiration_days
    }
    noncurrent_version_expiration {
      noncurrent_days = var.staging_expiration_days
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# One immutable repository per model; images are referenced by digest only.
resource "aws_ecr_repository" "model" {
  for_each = toset(var.model_ids)

  name                 = "${var.model_repository_prefix}/${each.value}"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }

  dynamic "encryption_configuration" {
    for_each = var.kms_key_arn != null ? [1] : []
    content {
      encryption_type = "KMS"
      kms_key         = var.kms_key_arn
    }
  }

  tags = merge(var.tags, { Name = "${var.model_repository_prefix}/${each.value}", model_id = each.value })
}

# Count-based retention so digests still referenced by registered packages are not aged out.
resource "aws_ecr_lifecycle_policy" "model" {
  for_each   = aws_ecr_repository.model
  repository = each.value.name
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged layers left by failed pushes"
        selection    = { tagStatus = "untagged", countType = "sinceImagePushed", countUnit = "days", countNumber = 14 }
        action       = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Keep the most recent images; registry-referenced digests fall well inside this window"
        selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = var.ecr_keep_image_count }
        action       = { type = "expire" }
      },
    ]
  })
}

data "aws_iam_policy_document" "model_repo_pull" {
  count = length(var.ecr_pull_account_ids) > 0 ? 1 : 0

  statement {
    sid     = "AllowTargetAccountPullByDigest"
    actions = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability"]
    principals {
      type        = "AWS"
      identifiers = [for a in var.ecr_pull_account_ids : "arn:aws:iam::${a}:root"]
    }
  }
}

resource "aws_ecr_repository_policy" "model" {
  for_each   = length(var.ecr_pull_account_ids) > 0 ? aws_ecr_repository.model : {}
  repository = each.value.name
  policy     = data.aws_iam_policy_document.model_repo_pull[0].json
}
