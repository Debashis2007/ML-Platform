variable "name_prefix" {
  type = string
}

variable "model_package_arn" {
  type        = string
  description = "Approved SageMaker Model Package ARN to deploy (approved through the management API)."
}

variable "endpoint_name" {
  type        = string
  description = "SageMaker endpoint name (stable across releases)."
}

variable "environment" {
  type        = string
  description = "qa (ALL_AT_ONCE) or live (CANARY 10%, 15-minute bake)."

  validation {
    condition     = contains(["qa", "live"], var.environment)
    error_message = "environment must be qa or live."
  }
}

variable "release_id" {
  type        = string
  description = "Unique per release (e.g. package version + short hash); names the model and endpoint config."

  validation {
    condition     = can(regex("^[a-zA-Z0-9-]{1,24}$", var.release_id))
    error_message = "release_id must be 1-24 letters, digits or hyphens."
  }
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
  type        = number
  default     = 2
  description = "Initial and minimum instance count. LIVE requires at least 2."
}

variable "enable_network_isolation" {
  type    = bool
  default = false
}

variable "enable_autoscaling" {
  type    = bool
  default = true
}

variable "max_instance_count" {
  type    = number
  default = 4
}

variable "target_invocations_per_instance" {
  type    = number
  default = 100
}

variable "qa_wait_seconds" {
  type    = number
  default = 0
}

variable "live_canary_percent" {
  type    = number
  default = 10
}

variable "live_canary_wait_seconds" {
  type    = number
  default = 900
}

variable "termination_wait_seconds" {
  type    = number
  default = 300
}

variable "maximum_execution_timeout_seconds" {
  type    = number
  default = 3600
}

variable "rollback_5xx_threshold" {
  type    = number
  default = 5
}

variable "rollback_latency_p99_ms" {
  type    = number
  default = 1000
}

variable "extra_rollback_alarm_names" {
  type        = list(string)
  default     = []
  description = "Additional CloudWatch alarms that roll a release back."
}

variable "alarm_actions" {
  type    = list(string)
  default = []
}

variable "enable_data_capture" {
  type        = bool
  default     = true
  description = "Enable SageMaker data capture for monitoring."
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
  description = "Optional KMS key id/arn for data capture and endpoint storage."
}

variable "tags" {
  type    = map(string)
  default = {}
}
