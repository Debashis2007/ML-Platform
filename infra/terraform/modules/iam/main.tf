data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name

  sagemaker_pipeline_actions = [
    "sagemaker:CreatePipeline",
    "sagemaker:UpdatePipeline",
    "sagemaker:DescribePipeline",
    "sagemaker:StartPipelineExecution",
    "sagemaker:DescribePipelineExecution",
    "sagemaker:ListPipelineExecutions",
    "sagemaker:AddTags",
    "sagemaker:ListTags",
  ]

  sagemaker_job_actions = [
    "sagemaker:CreateTrainingJob",
    "sagemaker:DescribeTrainingJob",
    "sagemaker:StopTrainingJob",
    "sagemaker:CreateProcessingJob",
    "sagemaker:DescribeProcessingJob",
    "sagemaker:StopProcessingJob",
    "sagemaker:CreateModel",
    "sagemaker:DescribeModel",
    "sagemaker:DeleteModel",
    "sagemaker:CreateModelPackage",
    "sagemaker:DescribeModelPackage",
    "sagemaker:UpdateModelPackage",
    "sagemaker:ListModelPackages",
    "sagemaker:CreateModelPackageGroup",
    "sagemaker:DescribeModelPackageGroup",
    "sagemaker:CreateEndpointConfig",
    "sagemaker:DescribeEndpointConfig",
    "sagemaker:CreateEndpoint",
    "sagemaker:DescribeEndpoint",
    "sagemaker:UpdateEndpoint",
    "sagemaker:InvokeEndpoint",
    "sagemaker:AddTags",
    "sagemaker:ListTags",
  ]
}

resource "aws_iam_role" "pipeline" {
  name = "${var.name_prefix}-sagemaker-pipeline"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "sagemaker.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = var.tags
}

resource "aws_iam_role" "training" {
  name = "${var.name_prefix}-sagemaker-training"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "sagemaker.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = var.tags
}

resource "aws_iam_role" "inference" {
  name = "${var.name_prefix}-sagemaker-inference"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "sagemaker.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy" "pipeline_s3" {
  name = "${var.name_prefix}-pipeline-s3"
  role = aws_iam_role.pipeline.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:DeleteObject"]
      Resource = [var.data_bucket_arn, "${var.data_bucket_arn}/*", var.artifacts_bucket_arn, "${var.artifacts_bucket_arn}/*"]
    }]
  })
}

resource "aws_iam_role_policy" "pipeline_sagemaker" {
  name = "${var.name_prefix}-pipeline-sagemaker"
  role = aws_iam_role.pipeline.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = concat(local.sagemaker_pipeline_actions, local.sagemaker_job_actions)
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [aws_iam_role.training.arn, aws_iam_role.pipeline.arn]
        Condition = {
          StringEquals = { "iam:PassedToService" = "sagemaker.amazonaws.com" }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "cloudwatch:PutMetricData",
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "pipeline_kms" {
  count = var.kms_key_arn != null ? 1 : 0
  name  = "${var.name_prefix}-pipeline-kms"
  role  = aws_iam_role.pipeline.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
      Resource = [var.kms_key_arn]
    }]
  })
}

resource "aws_iam_role_policy" "training_kms" {
  count = var.kms_key_arn != null ? 1 : 0
  name  = "${var.name_prefix}-training-kms"
  role  = aws_iam_role.training.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
      Resource = [var.kms_key_arn]
    }]
  })
}

resource "aws_iam_role_policy" "inference_kms" {
  count = var.kms_key_arn != null ? 1 : 0
  name  = "${var.name_prefix}-inference-kms"
  role  = aws_iam_role.inference.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
      Resource = [var.kms_key_arn]
    }]
  })
}

resource "aws_iam_role_policy" "training_s3_ecr" {
  name = "${var.name_prefix}-training-s3-ecr"
  role = aws_iam_role.training.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
        Resource = [var.data_bucket_arn, "${var.data_bucket_arn}/*", var.artifacts_bucket_arn, "${var.artifacts_bucket_arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"]
        Resource = var.ecr_repository_arn
      },
      {
        Effect   = "Allow"
        Action   = local.sagemaker_job_actions
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "inference_scoped" {
  name = "${var.name_prefix}-inference-scoped"
  role = aws_iam_role.inference.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sagemaker:InvokeEndpoint",
          "sagemaker:DescribeEndpoint",
          "sagemaker:DescribeModel",
          "sagemaker:DescribeModelPackage"
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:ListBucket"]
        Resource = [var.artifacts_bucket_arn, "${var.artifacts_bucket_arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"]
        Resource = var.ecr_repository_arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role" "gha_pipeline" {
  count = var.github_oidc_provider_arn != null ? 1 : 0
  name  = "${var.name_prefix}-gha-pipeline"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = var.github_oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" }
        StringLike   = { "token.actions.githubusercontent.com:sub" = var.github_repo_subjects }
      }
    }]
  })
  tags = var.tags
}

resource "aws_iam_role" "gha_deploy" {
  count = var.github_oidc_provider_arn != null ? 1 : 0
  name  = "${var.name_prefix}-gha-deploy"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = var.github_oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" }
        StringLike   = { "token.actions.githubusercontent.com:sub" = var.github_repo_subjects }
      }
    }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy" "gha_pipeline" {
  count = length(aws_iam_role.gha_pipeline) > 0 ? 1 : 0
  name  = "${var.name_prefix}-gha-pipeline"
  role  = aws_iam_role.gha_pipeline[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = concat(local.sagemaker_pipeline_actions, ["sagemaker:DescribeModelPackage", "sagemaker:ListModelPackages"])
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [aws_iam_role.pipeline.arn, aws_iam_role.training.arn]
        Condition = {
          StringEquals = { "iam:PassedToService" = "sagemaker.amazonaws.com" }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
        Resource = [var.data_bucket_arn, "${var.data_bucket_arn}/*", var.artifacts_bucket_arn, "${var.artifacts_bucket_arn}/*"]
      }
    ]
  })
}

resource "aws_iam_role_policy" "gha_deploy" {
  count = length(aws_iam_role.gha_deploy) > 0 ? 1 : 0
  name  = "${var.name_prefix}-gha-deploy"
  role  = aws_iam_role.gha_deploy[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sagemaker:CreateModel",
          "sagemaker:CreateEndpointConfig",
          "sagemaker:CreateEndpoint",
          "sagemaker:UpdateEndpoint",
          "sagemaker:Describe*",
          "sagemaker:AddTags",
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [aws_iam_role.inference.arn]
        Condition = {
          StringEquals = { "iam:PassedToService" = "sagemaker.amazonaws.com" }
        }
      }
    ]
  })
}
