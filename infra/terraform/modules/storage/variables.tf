variable "name_prefix" {
  type = string
}

variable "data_bucket_name" {
  type        = string
  description = "Globally unique S3 bucket for training/evaluation input data."
}

variable "artifacts_bucket_name" {
  type        = string
  description = "Globally unique S3 bucket for model artifacts and pipeline outputs."
}

variable "ecr_repository_name" {
  type    = string
  default = "ml-platform-models"
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
