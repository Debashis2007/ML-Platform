variable "name_prefix" {
  type = string
}

variable "kms_key_arn" {
  type        = string
  default     = null
  description = "Optional CMK for SNS topic encryption."
}

variable "tags" {
  type    = map(string)
  default = {}
}
