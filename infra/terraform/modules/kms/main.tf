data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  key_users  = distinct(concat(var.key_users, []))
}

resource "aws_kms_key" "platform" {
  description             = var.description
  deletion_window_in_days = var.deletion_window_in_days
  enable_key_rotation     = true
  multi_region            = false

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Sid    = "EnableRootAccountAdmin"
          Effect = "Allow"
          Principal = {
            AWS = "arn:aws:iam::${local.account_id}:root"
          }
          Action   = "kms:*"
          Resource = "*"
        },
        {
          Sid    = "AllowPlatformServices"
          Effect = "Allow"
          Principal = {
            Service = [
              "s3.amazonaws.com",
              "sns.amazonaws.com",
              "secretsmanager.amazonaws.com",
              "dynamodb.amazonaws.com",
              "logs.${data.aws_region.current.name}.amazonaws.com",
              "sagemaker.amazonaws.com",
            ]
          }
          Action = [
            "kms:Encrypt",
            "kms:Decrypt",
            "kms:ReEncrypt*",
            "kms:GenerateDataKey*",
            "kms:DescribeKey",
            "kms:CreateGrant",
          ]
          Resource = "*"
          Condition = {
            StringEquals = {
              "kms:CallerAccount" = local.account_id
            }
          }
        }
      ],
      length(local.key_users) > 0 || length(var.spoke_account_ids) > 0 ? [
        {
          Sid    = "AllowKeyUsersAndSpokes"
          Effect = "Allow"
          Principal = {
            AWS = concat(
              local.key_users,
              [for a in var.spoke_account_ids : "arn:aws:iam::${a}:root"]
            )
          }
          Action = [
            "kms:Encrypt",
            "kms:Decrypt",
            "kms:ReEncrypt*",
            "kms:GenerateDataKey*",
            "kms:DescribeKey",
            "kms:CreateGrant",
          ]
          Resource = "*"
        }
      ] : []
    )
  })

  tags = merge(var.tags, { Name = "${var.name_prefix}-cmk" })
}

resource "aws_kms_alias" "platform" {
  name          = "alias/${var.name_prefix}-platform"
  target_key_id = aws_kms_key.platform.key_id
}
