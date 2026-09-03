variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "name_prefix" {
  type    = string
  default = "mlp-hub-nonprod"
}

variable "vpc_id" {
  type        = string
  description = "Existing hub VPC ID."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Private subnets for SageMaker."
}

variable "data_bucket_name" {
  type        = string
  description = "Globally unique S3 bucket name for training data."
}

variable "artifacts_bucket_name" {
  type        = string
  description = "Globally unique S3 bucket name for artifacts."
}

variable "ecr_repository_name" {
  type    = string
  default = "ml-platform-models"
}

variable "model_package_group_name" {
  type    = string
  default = "ModelCreditRisk"
}

variable "spoke_account_ids" {
  type        = list(string)
  default     = []
  description = "Dev/test spoke account IDs for RAM model package sharing."
}

variable "github_oidc_provider_arn" {
  type    = string
  default = null
}

variable "github_repo_subjects" {
  type    = list(string)
  default = []
}

variable "dev_artifacts_bucket_name" {
  type        = string
  description = "Dev artifacts bucket for pipeline build outputs."
}

variable "create_dev_test_endpoint" {
  type    = bool
  default = false
}

variable "dev_test_model_package_arn" {
  type    = string
  default = ""
}

variable "tags" {
  type    = map(string)
  default = { Environment = "hub-nonprod", ManagedBy = "terraform" }
}
