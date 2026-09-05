variable "name_prefix" {
  type = string
}

variable "model_package_group_name" {
  type = string
}

variable "lambda_source_dir" {
  type        = string
  description = "Directory containing capture_approval.zip (and optionally github_dispatch.zip)."
  default     = ""
}

variable "deploy_parameter_prefix" {
  type        = string
  default     = ""
  description = "SSM prefix for latest approved model package ARN (Workflow B input)."
}

variable "kms_key_arn" {
  type        = string
  default     = null
  description = "Optional CMK for DynamoDB encryption."
}

variable "enable_auto_deploy" {
  type        = bool
  default     = false
  description = "When true, Model Approved events trigger GitHub repository_dispatch."
}

variable "github_owner" {
  type    = string
  default = ""
}

variable "github_repo" {
  type    = string
  default = ""
}

variable "github_token_secret_arn" {
  type        = string
  default     = ""
  description = "Secrets Manager ARN holding the GitHub dispatch token."
}

variable "tags" {
  type    = map(string)
  default = {}
}
