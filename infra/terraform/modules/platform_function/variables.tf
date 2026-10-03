variable "function_name" {
  type = string
}

variable "description" {
  type    = string
  default = ""
}

variable "role_arn" {
  type        = string
  description = "Client-managed Lambda execution role ARN."
}

variable "image_uri" {
  type        = string
  default     = ""
  description = "Container image URI from platform-infra CI. Empty = zip of source_dir."
}

variable "source_dir" {
  type        = string
  default     = ""
  description = "Lambda source directory for the zip fallback."
}

variable "require_image" {
  type        = bool
  default     = false
  description = "Refuse the zip fallback (functions with third-party dependencies)."
}

variable "environment" {
  type    = map(string)
  default = {}
}

variable "timeout" {
  type    = number
  default = 30
}

variable "memory_size" {
  type    = number
  default = 256
}

variable "subnet_ids" {
  type    = list(string)
  default = []
}

variable "security_group_ids" {
  type    = list(string)
  default = []
}

variable "log_retention_days" {
  type    = number
  default = 365
}

variable "kms_key_arn" {
  type    = string
  default = null
}

variable "alarm_actions" {
  type    = list(string)
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
