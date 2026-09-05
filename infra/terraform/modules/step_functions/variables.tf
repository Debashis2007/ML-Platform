variable "name_prefix" {
  type = string
}

variable "pipeline_name" {
  type = string
}

variable "sfn_role_arn" {
  type        = string
  description = "Client-managed IAM role ARN for the Step Functions state machine."
}

variable "pipeline_role_arn" {
  type        = string
  default     = ""
  description = "Deprecated unused. Kept for call-site compatibility; prefer sfn_role_arn."
}

variable "tags" {
  type    = map(string)
  default = {}
}
