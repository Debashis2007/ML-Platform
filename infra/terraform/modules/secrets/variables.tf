variable "name_prefix" {
  type = string
}

variable "description" {
  type    = string
  default = "ML Platform pipeline secrets"
}

variable "kms_key_arn" {
  type        = string
  default     = null
  description = "Optional CMK for Secrets Manager encryption."
}

variable "github_dispatch_token" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Optional GitHub PAT/App token for repository_dispatch auto-deploy. Leave empty to skip."
}

variable "tags" {
  type    = map(string)
  default = {}
}
