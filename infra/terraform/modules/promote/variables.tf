variable "name_prefix" {
  type = string
}

variable "lambda_zip_path" {
  type = string
}

variable "lambda_source_hash" {
  type = string
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

variable "tags" {
  type    = map(string)
  default = {}
}
