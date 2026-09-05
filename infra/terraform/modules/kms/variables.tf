variable "name_prefix" {
  type = string
}

variable "description" {
  type    = string
  default = "ML Platform CMK for S3, SNS, Secrets, DynamoDB, and ECR"
}

variable "spoke_account_ids" {
  type        = list(string)
  default     = []
  description = "Spoke accounts allowed to use this key (Encrypt/Decrypt)."
}

variable "key_users" {
  type        = list(string)
  default     = []
  description = "Additional IAM principal ARNs allowed to use the key."
}

variable "deletion_window_in_days" {
  type    = number
  default = 30
}

variable "tags" {
  type    = map(string)
  default = {}
}
