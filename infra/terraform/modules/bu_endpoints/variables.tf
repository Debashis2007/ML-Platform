variable "name_prefix" {
  type = string
}

variable "business_units" {
  type = map(object({
    endpoint_name         = string
    model_package_arn     = string
    instance_type         = optional(string, "ml.m5.large")
    instance_count        = optional(number, 1)
    enable_data_capture   = optional(bool, true)
    enable_multi_az       = optional(bool, false)
  }))
  description = "Map of BU code (BU1, BU2, BU3, BU4) to endpoint settings. Empty model_package_arn skips that BU."
}

variable "inference_role_arn" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_group_ids" {
  type = list(string)
}

variable "artifacts_bucket_name" {
  type = string
}

variable "kms_key_arn" {
  type    = string
  default = null
}

variable "enable_api_gateway" {
  type        = bool
  description = "false = Non-Prod DEV (direct SageMaker). true = Prod (API Gateway front door)."
  default     = false
}

variable "enable_waf" {
  type    = bool
  default = true
}

variable "enable_iam_auth" {
  type    = bool
  default = true
}

variable "lambda_zip_path" {
  type    = string
  default = ""
}

variable "lambda_source_hash" {
  type    = string
  default = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}
