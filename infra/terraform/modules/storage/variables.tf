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

variable "snapshot_bucket_name" {
  type        = string
  default     = null
  description = "Override for the Object Lock snapshot bucket (default <prefix>-<account>-snapshots)."
}

variable "artefact_store_bucket_name" {
  type        = string
  default     = null
  description = "Override for the Object Lock artefact store (default <prefix>-<account>-artefacts)."
}

variable "evidence_bucket_name" {
  type        = string
  default     = null
  description = "Override for the Object Lock evidence bucket (default <prefix>-<account>-evidence)."
}

variable "object_lock_retention_days" {
  type        = number
  default     = 730
  description = "Default Object Lock GOVERNANCE retention for snapshots, artefacts and evidence."
}

variable "break_glass_principal_arns" {
  type        = list(string)
  default     = []
  description = "Principals exempt from the delete/retention deny (break-glass only)."
}

variable "staging_prefix" {
  type        = string
  default     = "pipelines/"
  description = "Pipeline run output prefix on the artifacts bucket; expires after staging_expiration_days."
}

variable "staging_expiration_days" {
  type    = number
  default = 7
}

variable "model_ids" {
  type        = list(string)
  default     = []
  description = "Model IDs that get their own immutable ECR repository."
}

variable "model_repository_prefix" {
  type    = string
  default = "ml-models"
}

variable "ecr_keep_image_count" {
  type    = number
  default = 200
}

variable "ecr_pull_account_ids" {
  type        = list(string)
  default     = []
  description = "Deployment target accounts allowed to pull model images by digest."
}
