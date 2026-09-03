variable "name_prefix" {
  type = string
}

variable "data_bucket_arn" {
  type = string
}

variable "artifacts_bucket_arn" {
  type = string
}

variable "ecr_repository_arn" {
  type = string
}

variable "github_oidc_provider_arn" {
  type        = string
  default     = null
  description = "GitHub OIDC provider ARN for GHA roles."
}

variable "github_repo_subjects" {
  type        = list(string)
  default     = []
  description = "OIDC subject claims, e.g. repo:org/ML-Platform:ref:refs/heads/main"
}

variable "tags" {
  type    = map(string)
  default = {}
}
