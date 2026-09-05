variable "name_prefix" {
  type = string
}

variable "lambda_zip_path" {
  type = string
}

variable "lambda_source_hash" {
  type = string
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

variable "target_approval_status" {
  type    = string
  default = "Approved"
}

variable "business_unit" {
  type    = string
  default = ""
}

variable "kms_key_arn" {
  type    = string
  default = null
}

variable "enable_event_trigger" {
  type        = bool
  default     = true
  description = "Subscribe to ml.platform.governance Model Approved events."
}

variable "model_life_cycle_stage" {
  type        = string
  default     = "Production"
  description = "Model Registry staging construct stage set on promoted packages."
}

variable "model_life_cycle_status" {
  type        = string
  default     = "Approved"
  description = "Model Registry staging construct status set on promoted packages."
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
