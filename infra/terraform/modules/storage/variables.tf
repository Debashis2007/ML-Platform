variable "name_prefix" {
  type = string
}

variable "data_bucket_name" {
  type        = string
  description = "Globally unique S3 bucket for training/evaluation input data."
}

variable "artifacts_bucket_name" {
  type        = string
  description = "Model artifact bucket for registered models and pipeline outputs."
}

variable "dev_artifacts_bucket_name" {
  type        = string
  description = "Dev Git/pipeline artifacts bucket."
}

variable "prod_data_bucket_name" {
  type        = string
  default     = null
  description = "Optional PROD data bucket."
}

variable "ecr_repository_name" {
  type    = string
  default = "ml-platform-models"
}

variable "platform_lambdas_ecr_repository_name" {
  type        = string
  default     = "mlp-platform-lambdas"
  description = "ECR repository for platform Lambda container images (CI build before CD apply)."
}

variable "kms_key_arn" {
  type        = string
  default     = null
  description = "Optional KMS key for bucket encryption."
}

variable "tags" {
  type    = map(string)
  default = {}
}
