variable "name_prefix" {
  type = string
}

variable "endpoint_name" {
  type = string
}

variable "latency_threshold_ms" {
  type    = number
  default = 500
}

variable "error_rate_threshold" {
  type    = number
  default = 5
}

variable "alarm_actions" {
  type        = list(string)
  default     = []
  description = "SNS topic ARNs for alarm notifications."
}

variable "enable_model_monitor" {
  type        = bool
  default     = false
  description = "Create SageMaker Data Quality monitoring schedule."
}

variable "monitoring_role_arn" {
  type        = string
  default     = ""
  description = "IAM role for Model Monitor processing jobs."
}

variable "baseline_constraints_s3_uri" {
  type        = string
  default     = ""
  description = "s3://.../constraints.json from a baseline job."
}

variable "baseline_statistics_s3_uri" {
  type        = string
  default     = ""
  description = "s3://.../statistics.json from a baseline job."
}

variable "data_capture_s3_uri" {
  type        = string
  default     = ""
  description = "Endpoint data capture S3 prefix."
}

variable "monitoring_output_s3_uri" {
  type        = string
  default     = ""
  description = "S3 prefix for monitoring reports."
}

variable "monitoring_image_uri" {
  type        = string
  default     = ""
  description = "SageMaker Model Monitor analyzer image URI for the region."
}

variable "monitoring_instance_type" {
  type    = string
  default = "ml.m5.xlarge"
}

variable "schedule_expression" {
  type    = string
  default = "cron(0 * ? * * *)"
}

variable "tags" {
  type    = map(string)
  default = {}
}
