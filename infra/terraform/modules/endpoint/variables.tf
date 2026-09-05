variable "name_prefix" {
  type = string
}

variable "model_package_arn" {
  type        = string
  description = "Approved SageMaker Model Package ARN to deploy."
}

variable "endpoint_name" {
  type        = string
  description = "SageMaker endpoint name."
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

variable "instance_type" {
  type    = string
  default = "ml.m5.large"
}

variable "instance_count" {
  type    = number
  default = 1
}

variable "enable_multi_az" {
  type    = bool
  default = false
}

variable "enable_data_capture" {
  type        = bool
  default     = true
  description = "Enable SageMaker data capture for Model Monitor."
}

variable "data_capture_s3_uri" {
  type        = string
  default     = ""
  description = "s3://bucket/prefix for captured request/response payloads."
}

variable "data_capture_percentage" {
  type    = number
  default = 100
}

variable "kms_key_id" {
  type        = string
  default     = null
  description = "Optional KMS key id/arn for data capture."
}

variable "tags" {
  type    = map(string)
  default = {}
}
