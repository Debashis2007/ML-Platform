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

variable "tags" {
  type    = map(string)
  default = {}
}
