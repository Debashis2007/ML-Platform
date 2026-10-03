variable "name_prefix" {
  type = string
}

variable "lambda_zip_path" {
  type    = string
  default = ""
}

variable "lambda_source_hash" {
  type    = string
  default = ""
}

variable "promote_model_image_uri" {
  type        = string
  default     = ""
  description = "ECR image URI from platform-infra CI. When set, deploys container Lambda instead of zip."
}

variable "lambda_role_arn" {
  type        = string
  description = "Client-managed IAM role ARN for the promote Lambda."
}

variable "target_model_package_group" {
  type = string
}

variable "deploy_parameter_prefix" {
  type    = string
  default = ""
}

variable "kms_key_arn" {
  type    = string
  default = null
}

variable "enable_event_trigger" {
  type        = bool
  default     = false
  description = "Also accept promotion requests from EventBridge (the workflow invokes directly by default)."
}

variable "decision_log_table_name" {
  type        = string
  description = "Prod decision log table (PROMOTION_REQUESTED records)."
}

variable "source_registry_read_role_arn" {
  type        = string
  default     = ""
  description = "Read-only role in the NonProd control plane for DescribeModelPackage."
}

variable "source_account_ids" {
  type        = list(string)
  default     = []
  description = "Non-Prod account IDs (documentation / client IAM scoping). Not used to create roles."
}

variable "tags" {
  type    = map(string)
  default = {}
}
