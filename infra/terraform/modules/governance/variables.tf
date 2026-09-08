variable "name_prefix" {
  type = string
}

variable "model_package_group_name" {
  type = string
}

variable "lambda_source_dir" {
  type        = string
  description = "Directory containing capture_approval.zip (zip fallback when image URI empty)."
  default     = ""
}

variable "capture_approval_image_uri" {
  type        = string
  default     = ""
  description = "ECR image URI from platform-infra CI. When set, deploys container Lambda instead of zip."
}

variable "github_dispatch_image_uri" {
  type        = string
  default     = ""
  description = "ECR image URI for github_dispatch Lambda (when enable_auto_deploy)."
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

variable "governance_lambda_role_arn" {
  type        = string
  description = "Client-managed IAM role ARN for capture_approval Lambda."
}

variable "github_dispatch_lambda_role_arn" {
  type        = string
  default     = ""
  description = "Client-managed IAM role ARN for github_dispatch Lambda (required when enable_auto_deploy)."
}

variable "tags" {
  type    = map(string)
  default = {}
}
