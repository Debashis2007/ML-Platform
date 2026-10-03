variable "name_prefix" {
  type = string
}

variable "model_package_group_name" {
  type        = string
  default     = ""
  description = "Restrict approval capture to one package group. Empty = all groups in the account."
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

variable "register_candidate_image_uri" {
  type        = string
  default     = ""
  description = "ECR image URI for the copy-in registration Lambda."
}

variable "github_dispatch_image_uri" {
  type        = string
  default     = ""
  description = "ECR image URI for github_dispatch Lambda (when enable_auto_deploy)."
}

variable "deploy_parameter_prefix" {
  type        = string
  default     = ""
  description = "SSM prefix for latest approved model package ARN (release workflow input)."
}

variable "kms_key_arn" {
  type        = string
  default     = null
  description = "Optional CMK for DynamoDB encryption."
}

variable "deletion_protection" {
  type        = bool
  default     = true
  description = "DynamoDB deletion protection on the four governance tables."
}

variable "retain_legacy_governance_table" {
  type        = bool
  default     = true
  description = "Keep the pre-v7 single governance table so its records are not destroyed."
}

variable "artefact_bucket_name" {
  type        = string
  description = "Object Lock artefact store the registration Lambda copies model.tar.gz into."
}

variable "evidence_bucket_name" {
  type        = string
  description = "Object Lock evidence bucket (candidate manifest, metrics)."
}

variable "training_account_ids" {
  type        = list(string)
  default     = []
  description = "Accounts allowed to submit candidates besides this control-plane account (BU training)."
}

variable "spoke_account_ids" {
  type        = list(string)
  default     = []
  description = "Accounts allowed to put events on the hub bus."
}

variable "source_read_role_name" {
  type        = string
  default     = ""
  description = "Role name in each BU training account the registration Lambda assumes to read pipeline parameters and candidate.json."
}

variable "lambda_subnet_ids" {
  type    = list(string)
  default = []
}

variable "lambda_security_group_ids" {
  type    = list(string)
  default = []
}

variable "alarm_actions" {
  type    = list(string)
  default = []
}

variable "violation_topic_arn" {
  type        = string
  default     = ""
  description = "SNS topic notified when a package is approved outside the management API."
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

variable "registration_lambda_role_arn" {
  type        = string
  description = "Client-managed role for the registration Lambda. Must be denied sagemaker:UpdateModelPackage."
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
